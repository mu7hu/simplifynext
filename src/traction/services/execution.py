"""Execution adapters: deploy an approved plan and return raw channel telemetry.

The boundary is fixed: ``ExecutionService.execute_plan(plan) -> list[RawExecutionResult]``,
one row per allocation. Implementations may be the seeded ``MarketSimulator``,
per-channel adapters (real ad-network APIs), or a mix - none of them see or emit
oracle / ground-truth parameters, and none of them decide approval.

* ``SimulatedExecutionService``   - unchanged constructor; MarketSimulator-backed,
  now guarantees one row per allocation (channels with no simulator get a null row).
* ``MultiChannelExecutionService`` - routes each allocation to a
  ``ChannelExecutionAdapter`` (real channel or simulator), same raw-result boundary.
* ``DryRunExecutionService``      - zero-spend rows, for rehearsing the pipeline.
* ``ApprovalGuardedExecutionService`` - refuses to run unless explicitly armed /
  an approval check passes (defense-in-depth outside the graph, which already
  gates execution behind the human approval gate).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, Optional

from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import RawExecutionResult
from traction.simulator.market import MarketSimulator

_DEFAULT_DAYS_ACTIVE = 14


class ExecutionError(RuntimeError):
    """Raised when a plan cannot be executed (malformed, or adapter failure)."""


class ExecutionNotApprovedError(ExecutionError):
    """Raised when execution is attempted without a recorded approval."""


class ExecutionService(ABC):
    """Abstract interface for marketing execution adapters (APIs or simulator)."""

    @abstractmethod
    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        """Deploy budget and return raw execution telemetry."""
        pass


def _validate_plan(plan: ExperimentPlan) -> None:
    if plan is None or not isinstance(plan, ExperimentPlan):
        raise ExecutionError("execute_plan requires a validated ExperimentPlan")
    for a in plan.allocations:
        if a.proposed_budget < 0:
            raise ExecutionError(f"negative proposed_budget for {a.channel.value}")


# --------------------------------------------------------------------------- #
# Per-channel adapters                                                         #
# --------------------------------------------------------------------------- #

class ChannelExecutionAdapter(ABC):
    """Executes the spend for a single channel allocation and returns raw telemetry.

    Implement this to plug a real ad network (Google Ads, LinkedIn, Meta, an ESP)
    into Traction without touching the graph or the result schema.
    """

    @abstractmethod
    def execute(self, allocation: Allocation, cycle_id: int) -> RawExecutionResult:
        ...


class NullChannelAdapter(ChannelExecutionAdapter):
    """No-op adapter: reports zero spend / zero activity for a channel."""

    def execute(self, allocation: Allocation, cycle_id: int) -> RawExecutionResult:
        return RawExecutionResult(
            channel=allocation.channel,
            experiment_id=allocation.experiment_id,
            spend=0.0,
            impressions=0,
            clicks=0,
            leads=0,
            primary_outcomes=0,
            days_active=_DEFAULT_DAYS_ACTIVE,
            raw_telemetry={"adapter": "null", "note": "no execution adapter configured for channel"},
        )


class SimulatorChannelAdapter(ChannelExecutionAdapter):
    """Routes one channel's spend through a shared :class:`MarketSimulator`.

    Uses the simulator's seeded RNG so a set of these adapters, invoked in
    allocation order, reproduces ``MarketSimulator.simulate_plan`` exactly.
    """

    def __init__(self, simulator: MarketSimulator, channel: Channel):
        self._simulator = simulator
        self._channel = channel

    def execute(self, allocation: Allocation, cycle_id: int) -> RawExecutionResult:
        channel_sim = self._simulator.simulators.get(self._channel)
        if channel_sim is None:
            return NullChannelAdapter().execute(allocation, cycle_id)
        return channel_sim.simulate(
            spend=allocation.proposed_budget,
            cycle_id=cycle_id,
            rng=self._simulator._rng,  # noqa: SLF001 - deliberate shared seeded RNG
            experiment_id=allocation.experiment_id,
        )


# --------------------------------------------------------------------------- #
# Execution services                                                           #
# --------------------------------------------------------------------------- #

class SimulatedExecutionService(ExecutionService):
    """Execution backed by the :class:`MarketSimulator` ground-truth testbed.

    Guarantees exactly one :class:`RawExecutionResult` per allocation, in plan
    order; a channel the simulator does not model yields a null row rather than
    silently disappearing.
    """

    def __init__(self, simulator: MarketSimulator):
        self.simulator = simulator

    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        _validate_plan(plan)
        simulated = {r.channel: r for r in self.simulator.simulate_plan(plan)}
        out: list[RawExecutionResult] = []
        for a in plan.allocations:
            out.append(simulated.get(a.channel) or NullChannelAdapter().execute(a, plan.cycle_id))
        return out


class MultiChannelExecutionService(ExecutionService):
    """Routes each allocation to a per-channel :class:`ChannelExecutionAdapter`.

    Mix real channel adapters with simulator-backed ones freely; the raw-result
    boundary is unchanged.
    """

    def __init__(
        self,
        adapters: dict[Channel, ChannelExecutionAdapter],
        *,
        default_adapter: Optional[ChannelExecutionAdapter] = None,
    ):
        self.adapters = dict(adapters)
        self.default_adapter = default_adapter or NullChannelAdapter()

    @classmethod
    def from_market_simulator(
        cls,
        simulator: MarketSimulator,
        real_adapters: Optional[dict[Channel, ChannelExecutionAdapter]] = None,
    ) -> "MultiChannelExecutionService":
        """Build simulator adapters for every modelled channel, overlaid with any real ones."""
        adapters: dict[Channel, ChannelExecutionAdapter] = {
            ch: SimulatorChannelAdapter(simulator, ch) for ch in simulator.simulators
        }
        adapters.update(real_adapters or {})
        return cls(adapters)

    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        _validate_plan(plan)
        out: list[RawExecutionResult] = []
        for a in plan.allocations:
            adapter = self.adapters.get(a.channel, self.default_adapter)
            out.append(adapter.execute(a, plan.cycle_id))
        return out


class DryRunExecutionService(ExecutionService):
    """Returns zero-spend rows for every allocation - rehearse the pipeline safely."""

    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        _validate_plan(plan)
        null = NullChannelAdapter()
        return [null.execute(a, plan.cycle_id) for a in plan.allocations]


class ApprovalGuardedExecutionService(ExecutionService):
    """Wraps another ExecutionService and refuses to run unapproved plans.

    The LangGraph supervisor already routes to ``node_execute`` only after the
    approval gate returns APPROVE / revalidated EDIT; this wrapper is the same
    guarantee for any caller invoking an execution service directly.

    Arm it per cycle with :meth:`approve` (optionally scoped to a cycle_id), or
    pass an ``approval_check`` callback that returns True when the given plan is
    approved.
    """

    def __init__(
        self,
        inner: ExecutionService,
        *,
        approval_check: Optional[Callable[[ExperimentPlan], bool]] = None,
    ):
        self._inner = inner
        self._approval_check = approval_check
        self._armed_cycle: Optional[int] = None
        self._armed_any = False

    def approve(self, cycle_id: Optional[int] = None) -> None:
        if cycle_id is None:
            self._armed_any = True
        else:
            self._armed_cycle = cycle_id

    def revoke(self) -> None:
        self._armed_any = False
        self._armed_cycle = None

    def _is_approved(self, plan: ExperimentPlan) -> bool:
        if self._approval_check is not None and self._approval_check(plan):
            return True
        if self._armed_any:
            return True
        return self._armed_cycle is not None and self._armed_cycle == plan.cycle_id

    def execute_plan(self, plan: ExperimentPlan) -> list[RawExecutionResult]:
        _validate_plan(plan)
        if not self._is_approved(plan):
            raise ExecutionNotApprovedError(
                f"cycle {plan.cycle_id} plan has not been approved for execution"
            )
        results = self._inner.execute_plan(plan)
        self._armed_cycle = None  # one-shot per cycle
        return results


def get_execution_service(
    simulator: Optional[MarketSimulator] = None,
    *,
    seed: int = 42,
) -> ExecutionService:
    """Default execution service: the seeded MarketSimulator testbed."""
    return SimulatedExecutionService(simulator or MarketSimulator(seed=seed))
