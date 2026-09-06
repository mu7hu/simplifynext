"""AWS Lambda entrypoint for one complete Traction cycle.

The handler keeps the existing LangGraph workflow intact while selecting
serverless persistence and storage through environment-aware factories.
"""

from __future__ import annotations

import json
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


class RunCycleRequest(BaseModel):
    startup_id: str = "ledger_ai"
    cycle_id: int = 1
    total_budget: float = 2000.0
    auto_approve: bool = True
    founder_feedback: Optional[str] = None


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


def handler(event: Any, context: Any = None) -> dict[str, Any]:  # noqa: ARG001
    try:
        request = RunCycleRequest.model_validate(_parse_event(event))
    except (ValueError, json.JSONDecodeError, ValidationError) as exc:
        return _response(400, {"error": "invalid_request", "detail": str(exc)})

    if not request.auto_approve:
        return _response(422, {
            "error": "approval_required",
            "detail": "The first serverless deployment supports auto_approve=true only. Add a durable approval state before enabling manual approval.",
        })

    try:
        graph = _build_graph()
        state = graph.invoke({
            "startup_id": request.startup_id,
            "thread_id": f"thread_{request.startup_id}",
            "cycle_id": request.cycle_id,
            "iteration_count": 0,
            "retry_count": 0,
            "max_iterations": settings.max_graph_iterations,
            "max_retries": settings.max_agent_retries,
            "next_cycle_requested": False,
            "founder_feedback": request.founder_feedback,
        })
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
        return _response(200, {
            "startup_id": request.startup_id,
            "cycle_id": request.cycle_id,
            "approval_status": state.get("approval_status", "UNKNOWN"),
            "strategy_summary": plan.strategy_summary if plan else "No plan generated",
            "verdicts": verdicts,
            "digest_markdown": state.get("digest_markdown", ""),
            "events_count": len(state.get("events", [])),
        })
    except Exception as exc:  # pragma: no cover - exercised in AWS runtime
        return _response(500, {"error": "cycle_failure", "detail": str(exc)})


lambda_handler = handler
