"""Experiment plan and channel allocation schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class Channel(str, Enum):
    """Supported marketing experimentation channels."""
    GOOGLE_SEARCH = "GOOGLE_SEARCH"
    LINKEDIN = "LINKEDIN"
    META = "META"
    COLD_EMAIL = "COLD_EMAIL"
    FOUNDER_CONTENT = "FOUNDER_CONTENT"


class Allocation(BaseModel):
    """Specific budget allocation and experiment design for a channel."""
    channel: Channel = Field(description="Channel assigned")
    experiment_id: str = Field(description="Unique experiment identifier e.g. EXP-01-GOOGLE")
    current_budget: float = Field(ge=0, description="Budget in the preceding cycle")
    proposed_budget: float = Field(ge=0, description="Proposed spend in currency units")
    proposed_share: float = Field(ge=0.0, le=1.0, description="Proposed share of total budget")
    hypothesis: str = Field(description="Falsifiable proposition being tested")
    audience: str = Field(description="Target persona or audience segment")
    message_angle: str = Field(description="Core value prop or creative hook")
    expected_outcome_range: Optional[tuple[int, int]] = Field(default=None, description="(min, max) expected outcomes")
    confidence: float = Field(ge=0.0, le=1.0, default=0.5, description="Strategist confidence in hypothesis")
    evaluation_window_days: int = Field(default=14, description="Days needed before concluding experiment")
    success_threshold: float = Field(gt=0, description="Max acceptable CAC to consider experiment successful")
    reason: str = Field(description="Explanation for proposed dollar/share change")
    evidence_used: str = Field(description="Prior data, benchmark, or historical verdict cited")
    is_exploration: bool = Field(default=False, description="True if exploratory experiment, False if exploiting proven channel")


class ExperimentPlan(BaseModel):
    """Structured portfolio proposal produced by Strategist Agent."""
    cycle_id: int = Field(ge=1, description="Cycle sequence number")
    total_budget: float = Field(ge=0, description="Total budget allocated across channels")
    primary_goal: str = Field(description="Target business goal")
    allocations: list[Allocation] = Field(description="Per-channel budget allocations")
    exploration_budget_pct: float = Field(ge=0.0, le=1.0, description="Share allocated to exploration")
    exploitation_budget_pct: float = Field(ge=0.0, le=1.0, description="Share allocated to exploitation")
    strategy_summary: str = Field(description="High-level narrative explaining portfolio movement")
    major_uncertainties: list[str] = Field(default_factory=list, description="Key assumptions under test")
