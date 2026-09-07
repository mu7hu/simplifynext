"""Channel physics and ground truth simulation models."""

import math
from random import Random
from typing import Optional
from pydantic import BaseModel, Field
from augury.schemas.experiment import Channel
from augury.schemas.result import RawExecutionResult


class ChannelGroundTruth(BaseModel):
    """Hidden ground truth parameters. AGENTS MUST NEVER RECEIVE OR INSPECT THIS OBJECT."""
    channel: Channel
    base_unit_cost: float = Field(gt=0, description="Cost per click or unit outreach")
    base_conversion_rate: float = Field(gt=0, le=1.0, description="Base conversion rate to qualified demo")
    saturation_spend: float = Field(gt=0, description="Spend level where diminishing returns begin")
    diminishing_returns_gamma: float = Field(default=0.75, description="Power law exponent for returns above saturation")
    noise_std: float = Field(default=0.15, description="Relative Gaussian variance on conversions")
    response_delay_days: int = Field(default=0, description="Lag days before full conversions manifest")
    min_evaluation_days: int = Field(default=14, description="True evaluation window needed for statistical validity")
    audience_fit_score: float = Field(default=1.0, ge=0.1, le=2.0, description="Market-channel fit multiplier")


class ChannelSimulator:
    """Simulates realistic, noisy market response to budget spend on a channel."""

    def __init__(self, ground_truth: ChannelGroundTruth):
        self.truth = ground_truth

    def simulate(self, spend: float, cycle_id: int, rng: Random, experiment_id: str) -> RawExecutionResult:
        if spend <= 0:
            return RawExecutionResult(
                channel=self.truth.channel,
                experiment_id=experiment_id,
                spend=0.0,
                impressions=0,
                clicks=0,
                leads=0,
                primary_outcomes=0,
                days_active=14,
                raw_telemetry={"note": "Zero spend allocated"}
            )

        # 1. Traffic / Volume with minor noise
        cpc_noise = rng.gauss(1.0, 0.08)
        effective_cpc = max(0.5, self.truth.base_unit_cost * cpc_noise)
        clicks = int(spend / effective_cpc)
        impressions = int(clicks * rng.uniform(20.0, 45.0))

        # 2. Diminishing returns curve: effective spend
        if spend <= self.truth.saturation_spend:
            effective_spend_factor = 1.0
        else:
            excess = spend - self.truth.saturation_spend
            diminished = excess ** self.truth.diminishing_returns_gamma
            effective_spend_factor = (self.truth.saturation_spend + diminished) / spend

        # 3. Conversion calculation
        conversion_noise = rng.gauss(1.0, self.truth.noise_std)
        effective_cvr = max(
            0.001,
            self.truth.base_conversion_rate * self.truth.audience_fit_score * effective_spend_factor * conversion_noise
        )

        # Account for response delay: in early cycles, delayed channels report fraction of conversions
        delay_damping = 1.0
        if self.truth.response_delay_days > 14 and cycle_id <= 2:
            delay_damping = 0.35  # most conversions haven't materialized yet

        expected_conversions = clicks * effective_cvr * delay_damping
        # Poisson or binomial draw approximation
        outcomes = int(max(0, round(rng.gauss(expected_conversions, max(0.5, math.sqrt(max(0.1, expected_conversions)))))))

        leads = int(outcomes * rng.uniform(1.8, 3.5))

        return RawExecutionResult(
            channel=self.truth.channel,
            experiment_id=experiment_id,
            spend=round(spend, 2),
            impressions=impressions,
            clicks=clicks,
            leads=leads,
            primary_outcomes=outcomes,
            days_active=14,
            raw_telemetry={
                "effective_cpc": round(effective_cpc, 2),
                "delay_damping": delay_damping,
                "effective_cvr": round(effective_cvr, 4)
            }
        )
