"""Unit tests for Analyst Agent verdicts and safeguards."""

from traction.agents.analyst import StubAnalystAgent
from traction.services.profiler import MockProfilerService
from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import ExperimentResult
from traction.schemas.analysis import Verdict


def test_analyst_first_class_insufficient_data():
    analyst = StubAnalystAgent()
    priors = MockProfilerService().get_benchmark_priors("ledger_ai")

    plan = ExperimentPlan(
        cycle_id=1,
        total_budget=2000.0,
        primary_goal="Demos",
        allocations=[],
        exploration_budget_pct=0.3,
        exploitation_budget_pct=0.7,
        strategy_summary="Test"
    )

    report = analyst.analyze_cycle(cycle_id=1, plan=plan, results=[], benchmark_priors=priors)

    # Cycle 1 contains INSUFFICIENT_DATA as a first-class verdict
    verdicts = {v.channel: v.verdict for v in report.verdicts}
    assert Verdict.INSUFFICIENT_DATA in verdicts.values()


def test_analyst_incomplete_window_protection():
    analyst = StubAnalystAgent()
    priors = MockProfilerService().get_benchmark_priors("ledger_ai")

    plan = ExperimentPlan(
        cycle_id=1,
        total_budget=2000.0,
        primary_goal="Demos",
        allocations=[],
        exploration_budget_pct=0.3,
        exploitation_budget_pct=0.7,
        strategy_summary="Test"
    )

    report = analyst.analyze_cycle(cycle_id=1, plan=plan, results=[], benchmark_priors=priors)
    linkedin_verdict = next(v for v in report.verdicts if v.channel == Channel.LINKEDIN)

    # Incomplete window (14 of 30 days) must NOT be CUT
    assert not linkedin_verdict.evaluation_window_complete
    assert linkedin_verdict.verdict != Verdict.CUT
    assert linkedin_verdict.verdict in (Verdict.HOLD, Verdict.INSUFFICIENT_DATA)
