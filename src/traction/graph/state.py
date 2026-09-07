"""Strongly typed LangGraph state definition for Traction."""

from typing import Any, Optional, TypedDict
from traction.schemas.founder import FounderBrief
from traction.schemas.profile import StartupProfile, BenchmarkPrior
from traction.schemas.experiment import ExperimentPlan
from traction.schemas.result import RawExecutionResult, ExperimentResult
from traction.schemas.analysis import AnalysisReport


class TractionGraphState(TypedDict, total=False):
    """Execution state passed through the LangGraph supervisor workflow."""

    startup_id: str
    thread_id: str
    cycle_id: int

    # Domain Context
    founder_brief: Optional[FounderBrief]
    startup_profile: Optional[StartupProfile]
    benchmark_priors: list[BenchmarkPrior]

    # Current & Historical State
    current_allocation: dict[str, float]
    recent_learnings: list[str]
    recent_verdicts: list[dict[str, Any]]

    # Plan Lifecycle
    proposed_plan: Optional[ExperimentPlan]
    approved_plan: Optional[ExperimentPlan]
    plan_valid: bool
    constraint_errors: list[str]

    # Approval Gate
    approval_status: str           # "PENDING", "APPROVED", "REJECTED", "EDITED"
    founder_feedback: Optional[str]

    # Execution & Telemetry
    raw_results: list[RawExecutionResult]
    normalized_results: list[ExperimentResult]

    # Analysis & Reporting
    analysis_report: Optional[AnalysisReport]
    digest_markdown: Optional[str]

    # Loop Discipline & Guardrails
    iteration_count: int
    retry_count: int
    max_iterations: int
    max_retries: int
    next_cycle_requested: bool
    should_stop: bool

    # Event Telemetry Stream
    events: list[dict[str, Any]]
    errors: list[str]
    approval_only: bool
    content_package: dict[str, Any]
