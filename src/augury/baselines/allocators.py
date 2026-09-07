"""Deterministic baseline budget allocators for scientific benchmarking."""

from abc import ABC, abstractmethod
from typing import Optional
from augury.schemas.experiment import Channel
from augury.simulator.presets import LEDGER_AI_MARKET_PRESET


class BaseAllocator(ABC):
    """Abstract baseline allocator interface."""

    @abstractmethod
    def allocate(
        self,
        cycle_id: int,
        total_budget: float,
        history: list[dict]
    ) -> dict[Channel, float]:
        """Return dollar allocation per channel summing to total_budget."""
        pass


class EqualSplitAllocator(BaseAllocator):
    """Evenly divides total budget across all channels."""

    def allocate(self, cycle_id: int, total_budget: float, history: list[dict]) -> dict[Channel, float]:
        channels = list(Channel)
        per_channel = round(total_budget / len(channels), 2)
        allocations = {c: per_channel for c in channels}
        # Balance rounding discrepancy
        diff = round(total_budget - sum(allocations.values()), 2)
        if diff != 0:
            allocations[channels[0]] += diff
        return allocations


class FounderSplitAllocator(BaseAllocator):
    """Preserves the founder's initial naive allocation permanently without adapting."""

    def __init__(self, initial_shares: Optional[dict[Channel, float]] = None):
        self.shares = initial_shares or {
            Channel.GOOGLE_SEARCH: 0.20,
            Channel.LINKEDIN: 0.25,
            Channel.META: 0.15,
            Channel.COLD_EMAIL: 0.15,
            Channel.FOUNDER_CONTENT: 0.25,
        }

    def allocate(self, cycle_id: int, total_budget: float, history: list[dict]) -> dict[Channel, float]:
        allocations = {c: round(total_budget * share, 2) for c, share in self.shares.items()}
        diff = round(total_budget - sum(allocations.values()), 2)
        if diff != 0:
            allocations[Channel.GOOGLE_SEARCH] += diff
        return allocations


class GreedyLastWinnerAllocator(BaseAllocator):
    """Greedily shifts 60% of budget to the lowest CAC channel in the previous cycle."""

    def allocate(self, cycle_id: int, total_budget: float, history: list[dict]) -> dict[Channel, float]:
        channels = list(Channel)
        if cycle_id <= 1 or not history:
            # Fallback to equal split for cycle 1
            return EqualSplitAllocator().allocate(cycle_id, total_budget, history)

        # Find channel with lowest CAC > 0 in prior cycle
        last_cycle = [h for h in history if h.get("cycle_id") == cycle_id - 1]
        valid_performers = [h for h in last_cycle if h.get("observed_cac", 0) > 0 and h.get("primary_outcomes", 0) > 0]

        if valid_performers:
            winner = min(valid_performers, key=lambda x: x["observed_cac"])["channel"]
        else:
            winner = Channel.GOOGLE_SEARCH.value

        winner_channel = Channel(winner)
        other_channels = [c for c in channels if c != winner_channel]

        allocations = {winner_channel: round(total_budget * 0.60, 2)}
        remainder = round(total_budget * 0.40 / len(other_channels), 2)
        for c in other_channels:
            allocations[c] = remainder

        diff = round(total_budget - sum(allocations.values()), 2)
        if diff != 0:
            allocations[winner_channel] += diff
        return allocations


class OracleAllocator(BaseAllocator):
    """Theoretically optimal allocator inspecting hidden ground truth. 
    WARNING: Permitted ONLY in evaluation benchmarks. The real Augury agent never receives oracle data."""

    def __init__(self, ground_truths=None):
        self.ground_truths = ground_truths or LEDGER_AI_MARKET_PRESET

    def allocate(self, cycle_id: int, total_budget: float, history: list[dict]) -> dict[Channel, float]:
        # Oracle knows Google Search is best up to saturation, Cold Email is 2nd, and remaining channels are suboptimal
        # Allocates optimal portfolio: 65% Google Search, 20% Cold Email, 5% LinkedIn, 5% Meta, 5% Founder Content
        allocations = {
            Channel.GOOGLE_SEARCH: round(total_budget * 0.65, 2),
            Channel.COLD_EMAIL: round(total_budget * 0.20, 2),
            Channel.LINKEDIN: round(total_budget * 0.05, 2),
            Channel.META: round(total_budget * 0.05, 2),
            Channel.FOUNDER_CONTENT: round(total_budget * 0.05, 2),
        }
        diff = round(total_budget - sum(allocations.values()), 2)
        if diff != 0:
            allocations[Channel.GOOGLE_SEARCH] += diff
        return allocations
