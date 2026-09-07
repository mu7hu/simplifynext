"""Founder brief and intake domain models."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class GoalType(str, Enum):
    """Primary outcome metric target."""
    DEMO_BOOKINGS = "DEMO_BOOKINGS"
    PAID_CONVERSIONS = "PAID_CONVERSIONS"
    LEAD_SIGNUPS = "LEAD_SIGNUPS"
    WAITLIST_SIGNUPS = "WAITLIST_SIGNUPS"


class PrimaryGoal(BaseModel):
    """Specific measurable target for the startup."""
    goal_type: GoalType = Field(default=GoalType.DEMO_BOOKINGS, description="Target metric type")
    target_cac: float = Field(gt=0, description="Target acquisition cost per primary outcome")
    minimum_acceptable_volume: int = Field(ge=1, default=5, description="Min outcomes needed per cycle")
    metric_name: str = Field(default="Qualified Demo Bookings", description="Human-readable outcome name")


class ChannelPreference(BaseModel):
    """Founder soft prior / belief on a marketing channel."""
    channel: str = Field(description="Channel name e.g. FOUNDER_CONTENT, GOOGLE_SEARCH")
    prior_belief_strength: float = Field(ge=0.0, le=1.0, default=0.5, description="0.0 weak to 1.0 strong belief")
    founder_note: str = Field(description="Explanation of why the founder believes in this channel")


class ExclusionRule(BaseModel):
    """Hard boundary: channels that must never receive budget."""
    channel: str = Field(description="Excluded channel name")
    reason: str = Field(description="Rationale for hard exclusion")
    is_permanent: bool = Field(default=True, description="Whether exclusion is permanent or temporary")


class FounderBrief(BaseModel):
    """Intake state provided by the founder."""
    startup_name: str = Field(description="Name of the startup")
    stage: str = Field(default="Seed", description="Funding / operational stage")
    one_line_pitch: str = Field(description="One line value proposition")
    total_budget: float = Field(gt=0, description="Total marketing budget available for the cycle")
    primary_goal: PrimaryGoal = Field(description="Primary business outcome to optimize")
    initial_allocations: dict[str, float] = Field(
        default_factory=dict, 
        description="Starting allocation percentage (0.0 to 1.0) per channel"
    )
    soft_preferences: list[ChannelPreference] = Field(
        default_factory=list, 
        description="Founder beliefs acting as priors"
    )
    hard_exclusions: list[ExclusionRule] = Field(
        default_factory=list, 
        description="Channels barred from receiving any spend"
    )
