"""Execution service interface and simulated market adapter."""

from abc import ABC, abstractmethod
from traction.schemas.experiment import ExperimentPlan
from traction.schemas.result import RawExecutionResult
from traction.simulator.market import MarketSimulator


class ExecutionService(ABC):
    """Abstract interface for marketing execution adapters (APIs or simulator)."""

    @abstractmethod
    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        """Deploy budget and return raw execution telemetry."""
        pass


class SimulatedExecutionService(ExecutionService):
    """Functional execution stub backed by the MarketSimulator."""

    def __init__(self, simulator: MarketSimulator):
        self.simulator = simulator

    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        return self.simulator.simulate_plan(plan)
