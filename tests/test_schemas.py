"""Unit tests for domain schemas and serialization."""

import pytest
from pydantic import ValidationError
from augury.schemas.founder import FounderBrief, PrimaryGoal, GoalType, ExclusionRule, ChannelPreference
from augury.schemas.experiment import Channel, Allocation, ExperimentPlan
from augury.schemas.result import RawExecutionResult, ExperimentResult
from augury.schemas.analysis import Verdict, ExperimentVerdict, AnalysisReport
from augury.schemas.ledger import LedgerEntry


def test_channel_enum():
    assert Channel.GOOGLE_SEARCH.value == "GOOGLE_SEARCH"
    assert Channel.FOUNDER_CONTENT.value == "FOUNDER_CONTENT"
    assert len(Channel) == 5


def test_allocation_schema():
    alloc = Allocation(
        channel=Channel.GOOGLE_SEARCH,
        experiment_id="EXP-01",
        current_budget=200.0,
        proposed_budget=500.0,
        proposed_share=0.25,
        hypothesis="Testing search intent",
        audience="CFOs",
        message_angle="Automate close",
        evaluation_window_days=14,
        success_threshold=350.0,
        reason="Scale winner",
        evidence_used="Benchmark",
        is_exploration=False
    )
    assert alloc.proposed_budget == 500.0
    assert not alloc.is_exploration

    # Check negative budget validation
    with pytest.raises(ValidationError):
        Allocation(
            channel=Channel.GOOGLE_SEARCH,
            experiment_id="EXP-01",
            current_budget=0.0,
            proposed_budget=-50.0,  # invalid
            proposed_share=-0.05,
            hypothesis="Fail",
            audience="CFOs",
            message_angle="Test",
            evaluation_window_days=14,
            success_threshold=350.0,
            reason="Fail",
            evidence_used="Fail"
        )


def test_experiment_plan_schema():
    alloc = Allocation(
        channel=Channel.GOOGLE_SEARCH,
        experiment_id="EXP-01",
        current_budget=0.0,
        proposed_budget=2000.0,
        proposed_share=1.0,
        hypothesis="Search dominates",
        audience="CFOs",
        message_angle="Automation",
        evaluation_window_days=14,
        success_threshold=350.0,
        reason="Test",
        evidence_used="Test",
        is_exploration=False
    )
    plan = ExperimentPlan(
        cycle_id=1,
        total_budget=2000.0,
        primary_goal="Qualified Demo Bookings",
        allocations=[alloc],
        exploration_budget_pct=0.0,
        exploitation_budget_pct=1.0,
        strategy_summary="Full allocation test"
    )
    assert plan.cycle_id == 1
    assert len(plan.allocations) == 1
    dump = plan.model_dump()
    assert dump["total_budget"] == 2000.0


def test_verdict_enum():
    assert Verdict.SCALE.value == "SCALE"
    assert Verdict.HOLD.value == "HOLD"
    assert Verdict.CUT.value == "CUT"
    assert Verdict.INSUFFICIENT_DATA.value == "INSUFFICIENT_DATA"
