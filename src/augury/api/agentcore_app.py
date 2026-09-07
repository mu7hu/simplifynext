"""AWS Bedrock AgentCore and local-first serving entrypoint."""

import os
from typing import Any, Optional
from pydantic import BaseModel, Field

from augury.config import settings
from augury.schemas.founder import FounderBrief
from augury.services.intake import get_intake_provider
from augury.services.profiler import get_profiler_service
from augury.services.execution import get_execution_service
from augury.services.measurement import DefaultMeasurementService
from augury.services.digest import get_digest_service
from augury.simulator.market import MarketSimulator
from augury.ledger.sqlite import SQLiteExperimentLedger
from augury.agents.strategist import StrategistAgent
from augury.agents.analyst import get_analyst_agent
from augury.approval.cli import AutoApprovalGate
from augury.graph.build import compile_augury_graph


class RunCycleRequest(BaseModel):
    startup_id: str = "ledger_ai"
    cycle_id: int = 1
    total_budget: float = 2000.0
    auto_approve: bool = True
    founder_feedback: Optional[str] = None


class RunCycleResponse(BaseModel):
    startup_id: str
    cycle_id: int
    approval_status: str
    strategy_summary: str
    verdicts: list[dict[str, Any]]
    digest_markdown: str
    events_count: int


# Global singletons
ledger = SQLiteExperimentLedger(settings.ledger_db_path)
profiler = get_profiler_service()
intake = get_intake_provider()
execution_svc = get_execution_service()
measurement_svc = DefaultMeasurementService()
digest_svc = get_digest_service()
strategist = StrategistAgent()
analyst = get_analyst_agent()
auto_gate = AutoApprovalGate()

graph = compile_augury_graph(
    ledger=ledger,
    profiler=profiler,
    intake=intake,
    strategist_agent=strategist,
    analyst_agent=analyst,
    approval_gate=auto_gate,
    execution_service=execution_svc,
    measurement_service=measurement_svc,
    digest_service=digest_svc
)


def entrypoint(request_data: dict[str, Any]) -> dict[str, Any]:
    """Bedrock AgentCore @app.entrypoint handler."""
    req = RunCycleRequest(**request_data)

    initial_state = {
        "startup_id": req.startup_id,
        "thread_id": f"thread_{req.startup_id}",
        "cycle_id": req.cycle_id,
        "iteration_count": 0,
        "retry_count": 0,
        "max_iterations": settings.max_graph_iterations,
        "max_retries": settings.max_agent_retries,
        "next_cycle_requested": False,
        "founder_feedback": req.founder_feedback
    }

    final_state = graph.invoke(initial_state)

    plan = final_state.get("approved_plan") or final_state.get("proposed_plan")
    report = final_state.get("analysis_report")
    digest = final_state.get("digest_markdown", "")

    verdicts_data = []
    if report:
        verdicts_data = [
            {
                "channel": v.channel.value,
                "verdict": v.verdict.value,
                "cost_per_outcome": v.observed_cost_per_outcome,
                "reason": v.reasoning_summary
            }
            for v in report.verdicts
        ]

    response = RunCycleResponse(
        startup_id=req.startup_id,
        cycle_id=req.cycle_id,
        approval_status=final_state.get("approval_status", "UNKNOWN"),
        strategy_summary=plan.strategy_summary if plan else "No plan generated",
        verdicts=verdicts_data,
        digest_markdown=digest,
        events_count=len(final_state.get("events", []))
    )

    return response.model_dump()
