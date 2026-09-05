"""Component tests for the execution adapter layer."""

from __future__ import annotations

import pytest

from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import RawExecutionResult
from traction.simulator.market import MarketSimulator
from traction.simulator.channel import ChannelSimulator
from traction.simulator.presets import LEDGER_AI_MARKET_PRESET
from traction.services.execution import (
    SimulatedExecutionService,
    MultiChannelExecutionService,
    DryRunExecutionService,
    ApprovalGuardedExecutionService,
    ChannelExecutionAdapter,
    NullChannelAdapter,
    ExecutionError,
    ExecutionNotApprovedError,
    get_execution_service,
)

ALL_CHANNELS = list(Channel)


def _alloc(channel, budget, share):
    return Allocation(
        channel=channel, experiment_id=f"EXP-{channel.value}", current_budget=0.0,
        proposed_budget=budget, proposed_share=share, hypothesis="h", audience="a",
        message_angle="m", success_threshold=350.0, reason="r", evidence_used="e",
        evaluation_window_days=14,
    )


def _plan(channels=ALL_CHANNELS, total=2000.0, cycle_id=1):
    per = round(total / len(channels), 2)
    return ExperimentPlan(
        cycle_id=cycle_id, total_budget=total, primary_goal="Qualified Demo Bookings",
        allocations=[_alloc(c, per, round(per / total, 4)) for c in channels],
        exploration_budget_pct=0.4, exploitation_budget_pct=0.6, strategy_summary="s",
    )


def test_simulated_execution_one_row_per_allocation_and_deterministic():
    plan = _plan()
    a = SimulatedExecutionService(MarketSimulator(seed=42)).execute_plan(plan)
    b = SimulatedExecutionService(MarketSimulator(seed=42)).execute_plan(plan)
    assert [r.channel for r in a] == [al.channel for al in plan.allocations]
    assert all(isinstance(r, RawExecutionResult) for r in a)
    assert [r.model_dump() for r in a] == [r.model_dump() for r in b]
    assert sum(r.spend for r in a) > 0


def test_multichannel_from_simulator_matches_simulated_service():
    plan = _plan()
    baseline = SimulatedExecutionService(MarketSimulator(seed=7)).execute_plan(plan)
    multi = MultiChannelExecutionService.from_market_simulator(
        MarketSimulator(seed=7)
    ).execute_plan(plan)
    assert [r.model_dump() for r in multi] == [r.model_dump() for r in baseline]


def test_channel_without_simulator_gets_null_row():
    sim = MarketSimulator(
        ground_truths={Channel.GOOGLE_SEARCH: LEDGER_AI_MARKET_PRESET[Channel.GOOGLE_SEARCH]},
        seed=42,
    )
    plan = _plan([Channel.GOOGLE_SEARCH, Channel.META])
    out = {r.channel: r for r in SimulatedExecutionService(sim).execute_plan(plan)}
    assert set(out) == {Channel.GOOGLE_SEARCH, Channel.META}
    assert out[Channel.META].spend == 0.0
    assert out[Channel.META].primary_outcomes == 0
    assert out[Channel.META].raw_telemetry["adapter"] == "null"
    assert out[Channel.GOOGLE_SEARCH].spend > 0


def test_dry_run_execution_zero_spend_all_channels():
    plan = _plan()
    out = DryRunExecutionService().execute_plan(plan)
    assert len(out) == len(plan.allocations)
    assert all(r.spend == 0.0 and r.primary_outcomes == 0 for r in out)


class _FixedAdapter(ChannelExecutionAdapter):
    def execute(self, allocation, cycle_id):
        return RawExecutionResult(
            channel=allocation.channel, experiment_id=allocation.experiment_id,
            spend=allocation.proposed_budget, impressions=1000, clicks=50, leads=5,
            primary_outcomes=2, days_active=14, raw_telemetry={"adapter": "fixed", "cycle": cycle_id},
        )


def test_multichannel_routes_per_channel_with_default():
    plan = _plan([Channel.GOOGLE_SEARCH, Channel.META, Channel.LINKEDIN], cycle_id=3)
    svc = MultiChannelExecutionService(
        {Channel.GOOGLE_SEARCH: _FixedAdapter()},
        default_adapter=NullChannelAdapter(),
    )
    out = {r.channel: r for r in svc.execute_plan(plan)}
    assert out[Channel.GOOGLE_SEARCH].primary_outcomes == 2
    assert out[Channel.GOOGLE_SEARCH].raw_telemetry == {"adapter": "fixed", "cycle": 3}
    assert out[Channel.META].spend == 0.0
    assert out[Channel.LINKEDIN].raw_telemetry["adapter"] == "null"


def test_approval_guard_blocks_until_armed():
    plan = _plan(cycle_id=5)
    guarded = ApprovalGuardedExecutionService(DryRunExecutionService())

    with pytest.raises(ExecutionNotApprovedError):
        guarded.execute_plan(plan)

    guarded.approve(cycle_id=5)
    out = guarded.execute_plan(plan)
    assert len(out) == len(plan.allocations)

    # one-shot: the per-cycle arm is consumed
    with pytest.raises(ExecutionNotApprovedError):
        guarded.execute_plan(plan)


def test_approval_guard_callback_and_global_arm():
    plan = _plan(cycle_id=2)

    by_callback = ApprovalGuardedExecutionService(
        DryRunExecutionService(), approval_check=lambda p: p.cycle_id == 2
    )
    assert by_callback.execute_plan(plan)  # no explicit arm needed

    always = ApprovalGuardedExecutionService(DryRunExecutionService())
    always.approve()  # global
    assert always.execute_plan(plan)
    assert always.execute_plan(_plan(cycle_id=9))  # still armed


def test_validate_plan_rejects_non_plan():
    with pytest.raises(ExecutionError):
        SimulatedExecutionService(MarketSimulator(seed=1)).execute_plan({"not": "a plan"})


def test_get_execution_service_default():
    assert isinstance(get_execution_service(), SimulatedExecutionService)
    assert isinstance(get_execution_service(MarketSimulator(seed=3)), SimulatedExecutionService)
