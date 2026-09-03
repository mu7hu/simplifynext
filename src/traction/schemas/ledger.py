"""Ledger records and historical query models."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field
from traction.schemas.experiment import Channel
from traction.schemas.analysis import Verdict


class LedgerEntry(BaseModel):
    """Immutable persistent record of an experiment cycle in the ledger."""
    id: Optional[int] = None
    startup_id: str
    cycle_id: int
    channel: Channel
    experiment_id: str
    hypothesis: str
    audience: str
    message_angle: str
    planned_budget: float
    actual_spend: float
    primary_outcomes: int
    observed_cac: float
    verdict: Verdict
    confidence: float
    learning: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class FailedHypothesis(BaseModel):
    """Record of a failed test to prevent repeating past mistakes."""
    channel: Channel
    cycle_id: int
    hypothesis: str
    reason_failed: str
    learning: str


class HistoricalSummary(BaseModel):
    """Aggregated historical context loaded into Strategist."""
    startup_id: str
    total_cycles_completed: int
    total_spend: float
    total_outcomes: int
    lifetime_cac: float
    channel_lifetime_stats: dict[str, dict[str, Any]] = Field(default_factory=dict)
    recent_learnings: list[str] = Field(default_factory=list)
    prior_failed_hypotheses: list[FailedHypothesis] = Field(default_factory=list)
