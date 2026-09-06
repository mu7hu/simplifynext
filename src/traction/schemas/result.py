"""Execution results and normalized measurement schemas."""

from typing import Any, Optional
from pydantic import BaseModel, Field
from traction.schemas.experiment import Channel


class RawExecutionResult(BaseModel):
    """Raw telemetry returned by channel adapter or simulator."""
    channel: Channel
    experiment_id: str
    spend: float = Field(ge=0.0)
    impressions: int = Field(ge=0, default=0)
    clicks: int = Field(ge=0, default=0)
    leads: int = Field(ge=0, default=0)
    primary_outcomes: int = Field(ge=0, default=0, description="Qualified outcomes achieved (e.g. demos)")
    days_active: int = Field(ge=1, default=14)
    raw_telemetry: dict[str, Any] = Field(default_factory=dict)


class ExperimentResult(BaseModel):
    """Normalized, comparable metrics across all marketing channels."""
    channel: Channel
    experiment_id: str
    spend: float = Field(ge=0.0)
    primary_outcomes: int = Field(ge=0)
    observed_cac: float = Field(ge=0.0, description="Cost per primary outcome; infinite/spend if 0 outcomes")
    conversion_rate: float = Field(ge=0.0, le=1.0, description="Outcome rate from traffic/leads")
    click_through_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    days_observed: int = Field(ge=1)
    evaluation_window_days: int = Field(ge=1)
    is_window_complete: bool = Field(description="Whether the full evaluation window has elapsed")
    cost_efficiency_ratio: float = Field(
        default=1.0, 
        description="Target CAC / Observed CAC (values > 1.0 are outperforming target)"
    )
    raw_metrics: dict[str, Any] = Field(default_factory=dict)
