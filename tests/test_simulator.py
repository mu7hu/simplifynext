"""Unit tests for market simulator and ground-truth encapsulation."""

from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.simulator.market import MarketSimulator


def test_simulator_determinism():
    sim1 = MarketSimulator(seed=123)
    sim2 = MarketSimulator(seed=123)

    plan = ExperimentPlan(
        cycle_id=1,
        total_budget=1000.0,
        primary_goal="Demos",
        allocations=[
            Allocation(
                channel=Channel.GOOGLE_SEARCH,
                experiment_id="EXP-1",
                current_budget=0.0,
                proposed_budget=1000.0,
                proposed_share=1.0,
                hypothesis="Test",
                audience="CFO",
                message_angle="Test",
                evaluation_window_days=14,
                success_threshold=350.0,
                reason="Test",
                evidence_used="Test"
            )
        ],
        exploration_budget_pct=0.0,
        exploitation_budget_pct=1.0,
        strategy_summary="Test"
    )

    res1 = sim1.simulate_plan(plan)
    res2 = sim2.simulate_plan(plan)

    assert res1[0].primary_outcomes == res2[0].primary_outcomes
    assert res1[0].clicks == res2[0].clicks
    assert res1[0].spend == res2[0].spend


def test_simulator_zero_spend():
    sim = MarketSimulator(seed=42)
    plan = ExperimentPlan(
        cycle_id=1,
        total_budget=0.0,
        primary_goal="Demos",
        allocations=[
            Allocation(
                channel=Channel.META,
                experiment_id="EXP-META-0",
                current_budget=0.0,
                proposed_budget=0.0,
                proposed_share=0.0,
                hypothesis="Zero test",
                audience="All",
                message_angle="Zero",
                evaluation_window_days=14,
                success_threshold=350.0,
                reason="No spend",
                evidence_used="None"
            )
        ],
        exploration_budget_pct=0.0,
        exploitation_budget_pct=0.0,
        strategy_summary="Zero spend test"
    )
    res = sim.simulate_plan(plan)
    assert res[0].primary_outcomes == 0
    assert res[0].spend == 0.0
