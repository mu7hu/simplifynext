"""Market simulator aggregating multiple marketing channels with seeded random noise."""

from random import Random
from typing import Optional
from traction.schemas.experiment import Channel, ExperimentPlan
from traction.schemas.result import RawExecutionResult
from traction.simulator.channel import ChannelGroundTruth, ChannelSimulator
from traction.simulator.presets import LEDGER_AI_MARKET_PRESET


class MarketSimulator:
    """Simulates market environment across all channels."""

    def __init__(
        self,
        ground_truths: Optional[dict[Channel, ChannelGroundTruth]] = None,
        seed: Optional[int] = 42
    ):
        self.ground_truths = ground_truths or LEDGER_AI_MARKET_PRESET
        self.simulators = {c: ChannelSimulator(gt) for c, gt in self.ground_truths.items()}
        self.seed = seed
        self._rng = Random(seed)

    def set_seed(self, seed: int) -> None:
        self.seed = seed
        self._rng = Random(seed)

    def simulate_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        """Execute a full cycle plan across all channel simulators."""
        results: list[RawExecutionResult] = []
        for a in plan.allocations:
            sim = self.simulators.get(a.channel)
            if sim:
                res = sim.simulate(
                    spend=a.proposed_budget,
                    cycle_id=plan.cycle_id,
                    rng=self._rng,
                    experiment_id=a.experiment_id
                )
                results.append(res)
        return results
