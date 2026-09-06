"""AWS Lambda entrypoint for one complete Traction cycle.

The handler keeps the existing LangGraph workflow intact while selecting
serverless persistence and storage through environment-aware factories.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ValidationError

from traction.agents.analyst import get_analyst_agent
from traction.agents.strategist import StrategistAgent
from traction.approval.cli import AutoApprovalGate
from traction.graph.build import compile_traction_graph
from traction.runtime import get_runtime_intake, get_runtime_ledger, get_runtime_profiler
from traction.services.digest import get_digest_service
from traction.services.execution import get_execution_service
from traction.services.measurement import DefaultMeasurementService
from traction.config import settings
from traction.schemas.founder import FounderBrief

try:
    import boto3
except ImportError:  # local tests can run without AWS SDK wiring
    boto3 = None


class RunCycleRequest(BaseModel):
    startup_id: str = "ledger_ai"
    cycle_id: int = 1
    total_budget: float = 2000.0
    auto_approve: bool = True
    founder_feedback: Optional[str] = None
    run_id: Optional[str] = None
    founder_brief: Optional[dict[str, Any]] = None


def _parse_event(event: Any) -> dict[str, Any]:
    if isinstance(event, dict) and "body" in event:
        body = event.get("body")
        if body is None or body == "":
            raise ValueError("request body is empty")
        return json.loads(body) if isinstance(body, str) else body
    if isinstance(event, str):
        return json.loads(event)
    if not isinstance(event, dict):
        raise ValueError("event must be a JSON object")
    return event


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "content-type": "application/json",
            "access-control-allow-origin": "*",
        },
        "body": json.dumps(payload, default=str),
    }


def _build_graph():
    ledger = get_runtime_ledger()
    return compile_traction_graph(
        ledger=ledger,
        profiler=get_runtime_profiler(),
        intake=get_runtime_intake(),
        strategist_agent=StrategistAgent(),
        analyst_agent=get_analyst_agent(),
        approval_gate=AutoApprovalGate(),
        execution_service=get_execution_service(),
        measurement_service=DefaultMeasurementService(),
        digest_service=get_digest_service(),
    )


def _record_run(run_id: str | None, *, status: str, event: dict[str, Any] | None = None, result: dict[str, Any] | None = None) -> None:
    table_name = os.environ.get("RUN_TABLE_NAME")
    if not run_id or not table_name or boto3 is None:
        return
    table = boto3.resource("dynamodb").Table(table_name)
    values: dict[str, Any] = {"#status": status, "updated_at": datetime.now(timezone.utc).isoformat()}
    names = {"#status": "status"}
    expression = "SET #status = :status, updated_at = :updated"
    expression_values = {":status": status, ":updated": values["updated_at"]}
    if event:
        expression += ", events = list_append(if_not_exists(events, :empty), :events)"
        expression_values[":empty"] = []
        # DynamoDB does not accept Python floats in nested maps.  Convert
        # streamed agent events recursively while preserving their shape.
        expression_values[":events"] = [json.loads(json.dumps(event, default=str), parse_float=Decimal)]
    if result:
        expression += ", #result = :result"
        names["#result"] = "result"
        expression_values[":result"] = json.loads(json.dumps(result, default=str), parse_float=Decimal)
    table.update_item(Key={"record_id": run_id}, UpdateExpression=expression, ExpressionAttributeNames=names, ExpressionAttributeValues=expression_values)


def handler(event: Any, context: Any = None) -> dict[str, Any]:  # noqa: ARG001
    try:
        request = RunCycleRequest.model_validate(_parse_event(event))
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        return _response(400, {"error": "invalid_request", "detail": str(exc)})

    try:
        _record_run(request.run_id, status="RUNNING", event={"node": "workflow", "status": "started", "timestamp": datetime.now(timezone.utc).isoformat(), "message": "Supervisor started the LangGraph workflow."})
        graph = _build_graph()
        initial_state = {
            "startup_id": request.startup_id,
            "thread_id": f"thread_{request.startup_id}",
            "cycle_id": request.cycle_id,
            "iteration_count": 0,
            "retry_count": 0,
            "max_iterations": settings.max_graph_iterations,
            "max_retries": settings.max_agent_retries,
            "next_cycle_requested": False,
            "founder_feedback": request.founder_feedback,
            "approval_only": not request.auto_approve,
        }
        if request.founder_brief:
            initial_state["founder_brief"] = FounderBrief.model_validate(request.founder_brief)
        state: dict[str, Any] = {}
        for update in graph.stream(initial_state):
            for node_name, node_update in update.items():
                if isinstance(node_update, dict):
                    state.update(node_update)
                node_events = node_update.get("events", []) if isinstance(node_update, dict) else []
                event = node_events[-1] if node_events else {"node": node_name, "timestamp": datetime.now(timezone.utc).isoformat(), "message": f"{node_name} completed."}
                _record_run(request.run_id, status="WAITING_APPROVAL" if node_name == "approval_gate" and state.get("approval_status") == "PENDING" else "RUNNING", event=event)
        plan = state.get("approved_plan") or state.get("proposed_plan")
        report = state.get("analysis_report")
        verdicts = []
        if report:
            verdicts = [
                {
                    "channel": verdict.channel.value,
                    "verdict": verdict.verdict.value,
                    "cost_per_outcome": verdict.observed_cost_per_outcome,
                    "reason": verdict.reasoning_summary,
                }
                for verdict in report.verdicts
            ]
        response = {
            "startup_id": request.startup_id,
            "cycle_id": request.cycle_id,
            "approval_status": state.get("approval_status", "UNKNOWN"),
            "strategy_summary": plan.strategy_summary if plan else "No plan generated",
            "verdicts": verdicts,
            "digest_markdown": state.get("digest_markdown", ""),
            "events_count": len(state.get("events", [])),
            "events": state.get("events", []),
            "plan": plan.model_dump(mode="json") if plan else None,
        }
        status = "WAITING_APPROVAL" if state.get("approval_status") == "PENDING" else "COMPLETE"
        _record_run(request.run_id, status=status, result=response)
        return _response(200, response)
    except Exception as exc:  # pragma: no cover - exercised in AWS runtime
        _record_run(request.run_id, status="FAILED", event={"node": "workflow", "status": "failed", "timestamp": datetime.now(timezone.utc).isoformat(), "message": str(exc)})
        return _response(500, {"error": "cycle_failure", "detail": str(exc)})


lambda_handler = handler
