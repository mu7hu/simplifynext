"""Unit tests for Strategist Agent portfolio generation and bounded repair."""

from augury.agents.strategist import StrategistAgent
from augury.services.intake import MockIntakeProvider
from augury.services.profiler import MockProfilerService
from augury.schemas.ledger import HistoricalSummary
from augury.constraints.budget import validate_budget_sum


def test_strategist_plan_cycle_1():
    agent = StrategistAgent()
    intake = MockIntakeProvider()
    profiler = MockProfilerService()

    brief = intake.get_founder_brief("ledger_ai")
    profile = profiler.get_startup_profile("ledger_ai")
    priors = profiler.get_benchmark_priors("ledger_ai")
    history_summary = HistoricalSummary(
        startup_id="ledger_ai",
        total_cycles_completed=0,
        total_spend=0.0,
        total_outcomes=0,
        lifetime_cac=0.0
    )

    plan = agent.plan_cycle(
        cycle_id=1,
        brief=brief,
        profile=profile,
        priors=priors,
        history_summary=history_summary,
        recent_verdicts=[]
    )

    # Validate exact budget match
    ok, msg = validate_budget_sum(plan, brief.total_budget)
    assert ok, msg
    assert plan.cycle_id == 1

    # Check that founder content received budget in cycle 1
    founder_alloc = next(a for a in plan.allocations if a.channel.value == "FOUNDER_CONTENT")
    assert founder_alloc.proposed_budget > 0


def test_strategist_challenges_founder_in_cycle_4():
    agent = StrategistAgent()
    intake = MockIntakeProvider()
    profiler = MockProfilerService()

    brief = intake.get_founder_brief("ledger_ai")
    profile = profiler.get_startup_profile("ledger_ai")
    priors = profiler.get_benchmark_priors("ledger_ai")
    history_summary = HistoricalSummary(
        startup_id="ledger_ai",
        total_cycles_completed=3,
        total_spend=6000.0,
        total_outcomes=12,
        lifetime_cac=500.0
    )

    plan = agent.plan_cycle(
        cycle_id=4,
        brief=brief,
        profile=profile,
        priors=priors,
        history_summary=history_summary,
        recent_verdicts=[{"channel": "FOUNDER_CONTENT", "verdict": "CUT", "observed_cost_per_outcome": 1850.0}]
    )

    founder_alloc = next(a for a in plan.allocations if a.channel.value == "FOUNDER_CONTENT")
    # Reduced to 10%
    assert founder_alloc.proposed_share == 0.10
    # Explicitly mentions 3x cost in reason
    assert "3x" in founder_alloc.reason
