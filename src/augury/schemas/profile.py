"""Startup profile and industry benchmark priors."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class StartupStage(str, Enum):
    PRE_SEED = "PRE_SEED"
    SEED = "SEED"
    SERIES_A = "SERIES_A"


class IndustrySector(str, Enum):
    B2B_SAAS = "B2B_SAAS"
    B2C_SUBSCRIPTION = "B2C_SUBSCRIPTION"
    MARKETPLACE = "MARKETPLACE"
    DEVTOOLS = "DEVTOOLS"


class StartupProfile(BaseModel):
    """Synthesized startup characteristics for targeting and expectations."""
    startup_id: str = Field(description="Unique identifier for the startup")
    startup_name: str = Field(description="Company name")
    stage: StartupStage = Field(default=StartupStage.SEED)
    sector: IndustrySector = Field(default=IndustrySector.B2B_SAAS)
    target_acv: float = Field(gt=0, description="Annual Contract Value / customer lifetime value")
    sales_cycle_days: int = Field(default=30, description="Average sales or conversion latency")
    primary_outcome_metric: str = Field(default="qualified_demo_bookings")


class BenchmarkPrior(BaseModel):
    """Industry reference benchmarks per marketing channel."""
    channel: str = Field(description="Channel name")
    median_cac: float = Field(gt=0, description="Typical benchmark cost per outcome")
    min_cac: float = Field(gt=0, description="Top decile cost per outcome")
    max_cac: float = Field(gt=0, description="High boundary cost per outcome")
    avg_cpc: float = Field(gt=0, description="Average cost per click or outreach unit")
    avg_conversion_rate: float = Field(gt=0, le=1.0, description="Lead-to-outcome conversion rate")
    min_evaluation_days: int = Field(default=14, description="Minimum days required for statistical validity")
    rationale: str = Field(description="Contextual note on channel dynamics")
