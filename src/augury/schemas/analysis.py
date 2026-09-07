"""Analyst verdicts and structured report schemas."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from augury.schemas.experiment import Channel


class Verdict(str, Enum):
    """Official Analyst verdict per experiment."""
    SCALE = "SCALE"
    HOLD = "HOLD"
    CUT = "CUT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class ExperimentVerdict(BaseModel):
    """Analyst evaluation for one channel experiment."""
    channel: Channel
    experiment_id: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in verdict given evidence volume")
    observed_cost_per_outcome: float = Field(ge=0.0)
    target_cost_per_outcome: float = Field(gt=0.0)
    evidence_count: int = Field(ge=0, description="Number of primary outcomes / data points observed")
    evaluation_window_complete: bool = Field(description="True if window elapsed; False protects against premature cut")
    reasoning_summary: str = Field(description="Concise diagnostic explanation of why this verdict was issued")
    recommended_budget_direction: str = Field(description="'INCREASE', 'MAINTAIN', 'DECREASE', or 'PAUSE'")
    learning: str = Field(description="Persistent insight to retain in the Experiment Ledger")
    attribution_warning: Optional[str] = Field(default=None, description="Note on overlapping signals or multi-touch noise")


class AnalysisReport(BaseModel):
    """Complete multi-channel evaluation produced by Analyst Agent."""
    cycle_id: int = Field(ge=1)
    verdicts: list[ExperimentVerdict]
    executive_summary: str = Field(description="High-level performance summary of the cycle")
    primary_bottleneck: Optional[str] = Field(default=None, description="Identified bottleneck (e.g. creative vs landing page)")
    recommended_explore_ratio: float = Field(ge=0.0, le=1.0, default=0.30)
