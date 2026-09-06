"""Intake interface and mocked provider for founder onboarding."""

from abc import ABC, abstractmethod
from typing import Optional
from traction.schemas.founder import FounderBrief, PrimaryGoal, GoalType, ChannelPreference, ExclusionRule
from traction.schemas.experiment import Channel


class IntakeProvider(ABC):
    """Abstract interface for founder intake providers."""

    @abstractmethod
    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        """Retrieve the founder intake brief."""
        pass


class MockIntakeProvider(IntakeProvider):
    """Functional stub returning the seeded LedgerAI demo brief."""

    def __init__(self, brief: Optional[FounderBrief] = None):
        if brief:
            self._brief = brief
        else:
            self._brief = FounderBrief(
                startup_name="LedgerAI",
                stage="Seed",
                one_line_pitch="Autonomous financial reconciliations and AI ledger software for mid-market CFOs",
                total_budget=2000.0,
                primary_goal=PrimaryGoal(
                    goal_type=GoalType.DEMO_BOOKINGS,
                    target_cac=350.0,
                    minimum_acceptable_volume=5,
                    metric_name="Qualified Demo Bookings"
                ),
                initial_allocations={
                    Channel.GOOGLE_SEARCH.value: 0.20,
                    Channel.LINKEDIN.value: 0.25,
                    Channel.META.value: 0.15,
                    Channel.COLD_EMAIL.value: 0.15,
                    Channel.FOUNDER_CONTENT.value: 0.25
                },
                soft_preferences=[
                    ChannelPreference(
                        channel=Channel.FOUNDER_CONTENT.value,
                        prior_belief_strength=0.8,
                        founder_note="I strongly believe founder-led content is strategically important for building trust in B2B finance."
                    )
                ],
                hard_exclusions=[]
            )

    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        return self._brief
