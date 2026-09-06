"""Unit tests for deterministic budget constraints and policies."""

from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.founder import FounderBrief, PrimaryGoal, ExclusionRule
from traction.constraints.budget import (
    validate_budget_sum,
    rebalance_micro_cents,
    validate_hard_constraints,
    validate_no_negative_spending,
    validate_plan_constraints,
)
from traction.constraints.policies import ExploreExploitPolicy


def _make_sample_plan(b1: float, b2: float) -> ExperimentPlan:
    allocs = [
        Allocation(
            channel=Channel.GOOGLE_SEARCH,
            experiment_id="EXP-1",
            current_budget=0.0,
            proposed_budget=b1,
            proposed_share=b1 / (b1 + b2),
            hypothesis="H1",
            audience="A1",
            message_angle="M1",
            evaluation_window_days=14,
            success_threshold=350.0,
            reason="R1",
            evidence_used="E1",
            is_exploration=False
        ),
        Allocation(
            channel=Channel.FOUNDER_CONTENT,
            experiment_id="EXP-2",
            current_budget=0.0,
            proposed_budget=b2,
            proposed_share=b2 / (b1 + b2),
            hypothesis="H2",
            audience="A2",
            message_angle="M2",
            evaluation_window_days=14,
            success_threshold=650.0,
            reason="R2",
            evidence_used="E2",
            is_exploration=True
        ),
    ]
    return ExperimentPlan(
        cycle_id=1,
        total_budget=b1 + b2,
        primary_goal="Demos",
        allocations=allocs,
        exploration_budget_pct=b2 / (b1 + b2),
        exploitation_budget_pct=b1 / (b1 + b2),
        strategy_summary="Test"
    )


def test_validate_budget_sum():
    plan = _make_sample_plan(1000.0, 1000.0)
    ok, msg = validate_budget_sum(plan, 2000.0)
    assert ok

    # Off by $10
    ok, msg = validate_budget_sum(plan, 1990.0)
    assert not ok


def test_rebalance_micro_cents():
    plan = _make_sample_plan(1200.00, 799.98)  # Sums to 1999.98
    plan.total_budget = 2000.0
    adjusted = rebalance_micro_cents(plan, 2000.0)
    total_adjusted = sum(a.proposed_budget for a in adjusted.allocations)
    assert round(total_adjusted, 2) == 2000.0


def test_validate_hard_constraints():
    plan = _make_sample_plan(1500.0, 500.0)
    exclusions = [ExclusionRule(channel="FOUNDER_CONTENT", reason="Brand restriction")]
    ok, msg = validate_hard_constraints(plan, exclusions)
    assert not ok
    assert "FOUNDER_CONTENT" in msg


def test_explore_exploit_policy():
    policy = ExploreExploitPolicy()
    assert policy.get_exploration_target(1) == 0.40
    assert policy.get_exploration_target(3) == 0.30
    assert policy.get_exploration_target(6) == 0.15
    # Never drops below minimum floor
    assert policy.get_exploration_target(10, highest_confidence=0.99) >= 0.10
