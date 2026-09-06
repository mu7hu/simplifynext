"""Component tests for the real MeasurementService (DefaultMeasurementService)."""

from __future__ import annotations

from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import RawExecutionResult, ExperimentResult
from traction.schemas.profile import BenchmarkPrior
from traction.services.measurement import DefaultMeasurementService


def _alloc(channel, exp_id, audience, threshold, window, exploration=False):
    return Allocation(
        channel=channel, experiment_id=exp_id, current_budget=0.0, proposed_budget=800.0,
        proposed_share=0.4, hypothesis="h", audience=audience, message_angle="m",
        success_threshold=threshold, reason="r", evidence_used="e",
        evaluation_window_days=window, is_exploration=exploration,
    )


def _plan(allocs):
    return ExperimentPlan(
        cycle_id=2, total_budget=1600.0, primary_goal="Qualified Demo Bookings",
        allocations=allocs, exploration_budget_pct=0.4, exploitation_budget_pct=0.6,
        strategy_summary="s",
    )


def _priors():
    return [
        BenchmarkPrior(channel="GOOGLE_SEARCH", median_cac=320.0, min_cac=220.0, max_cac=550.0,
                       avg_cpc=11.5, avg_conversion_rate=0.04, min_evaluation_days=14, rationale="x"),
        BenchmarkPrior(channel="FOUNDER_CONTENT", median_cac=650.0, min_cac=300.0, max_cac=1800.0,
                       avg_cpc=7.5, avg_conversion_rate=0.003, min_evaluation_days=30, rationale="x"),
    ]


SVC = DefaultMeasurementService()


def test_observed_cac_matches_handoff_example():
    plan = _plan([_alloc(Channel.GOOGLE_SEARCH, "EXP-2-GOOG", "CFOs searching software", 350.0, 14)])
    raw = [RawExecutionResult(channel=Channel.GOOGLE_SEARCH, experiment_id="EXP-2-GOOG", spend=800.0,
                              impressions=10000, clicks=400, leads=8, primary_outcomes=3, days_active=14)]
    out = SVC.normalize_results(raw, plan, _priors())
    assert len(out) == 1 and isinstance(out[0], ExperimentResult)
    assert out[0].observed_cac == 266.67
    assert out[0].is_window_complete is True
    assert out[0].cost_efficiency_ratio == round(350.0 / 266.67, 2)
    assert out[0].click_through_rate == 0.04
    assert out[0].conversion_rate == round(3 / 400, 4)


def test_incomplete_window_when_days_below_evaluation_window():
    plan = _plan([_alloc(Channel.FOUNDER_CONTENT, "EXP-2-FNDR", "Founder brand followers", 650.0, 30)])
    raw = [RawExecutionResult(channel=Channel.FOUNDER_CONTENT, experiment_id="EXP-2-FNDR", spend=500.0,
                              impressions=9000, clicks=300, leads=5, primary_outcomes=0, days_active=14)]
    out = SVC.normalize_results(raw, plan, _priors())[0]
    assert out.is_window_complete is False
    assert out.raw_metrics["days_remaining"] == 16
    assert out.raw_metrics["window_progress"] == round(14 / 30, 3)
    assert out.raw_metrics["data_quality"] == "low"


def test_zero_spend_is_safe():
    plan = _plan([_alloc(Channel.META, "EXP-2-META", "All", 750.0, 14)])
    raw = [RawExecutionResult(channel=Channel.META, experiment_id="EXP-2-META", spend=0.0,
                              impressions=0, clicks=0, leads=0, primary_outcomes=0, days_active=14,
                              raw_telemetry={"note": "Zero spend allocated"})]
    out = SVC.normalize_results(raw, plan, _priors())[0]
    assert out.spend == 0.0
    assert out.observed_cac == 0.0
    assert out.conversion_rate == 0.0
    assert out.click_through_rate == 0.0
    assert out.cost_efficiency_ratio == 0.0
    assert out.raw_metrics["telemetry_note"] == "Zero spend allocated"


def test_zero_outcomes_observed_cac_is_spend():
    plan = _plan([_alloc(Channel.GOOGLE_SEARCH, "EXP-2-GOOG", "CFOs", 350.0, 14)])
    raw = [RawExecutionResult(channel=Channel.GOOGLE_SEARCH, experiment_id="EXP-2-GOOG", spend=600.0,
                              impressions=8000, clicks=250, leads=4, primary_outcomes=0, days_active=14)]
    out = SVC.normalize_results(raw, plan, _priors())[0]
    assert out.observed_cac == 600.0
    assert out.raw_metrics["vs_target"] == "no_outcomes"


def test_attribution_warning_on_overlapping_audiences():
    plan = _plan([
        _alloc(Channel.GOOGLE_SEARCH, "EXP-2-GOOG", "Mid-market CFOs and Controllers evaluating finance software", 350.0, 14),
        _alloc(Channel.COLD_EMAIL, "EXP-2-COLD", "Controllers and CFOs at mid-market finance teams", 400.0, 14),
        _alloc(Channel.FOUNDER_CONTENT, "EXP-2-FNDR", "Founder personal brand followers on social", 650.0, 30),
    ])
    raw = [
        RawExecutionResult(channel=Channel.GOOGLE_SEARCH, experiment_id="EXP-2-GOOG", spend=800.0,
                           impressions=10000, clicks=400, leads=8, primary_outcomes=3, days_active=14),
        RawExecutionResult(channel=Channel.COLD_EMAIL, experiment_id="EXP-2-COLD", spend=400.0,
                           impressions=0, clicks=120, leads=6, primary_outcomes=1, days_active=14),
        RawExecutionResult(channel=Channel.FOUNDER_CONTENT, experiment_id="EXP-2-FNDR", spend=400.0,
                           impressions=9000, clicks=300, leads=5, primary_outcomes=0, days_active=14),
    ]
    out = {r.channel: r for r in SVC.normalize_results(raw, plan, _priors())}
    assert out[Channel.GOOGLE_SEARCH].raw_metrics["attribution_risk"] is True
    assert out[Channel.COLD_EMAIL].raw_metrics["attribution_risk"] is True
    assert "COLD_EMAIL" in out[Channel.GOOGLE_SEARCH].raw_metrics["attribution_warning"]
    assert out[Channel.FOUNDER_CONTENT].raw_metrics["attribution_risk"] is False
    assert out[Channel.FOUNDER_CONTENT].raw_metrics["attribution_warning"] is None


def test_response_delay_suspected_from_leads_without_outcomes():
    plan = _plan([_alloc(Channel.FOUNDER_CONTENT, "EXP-2-FNDR", "Founder brand followers", 650.0, 30)])
    raw = [RawExecutionResult(channel=Channel.FOUNDER_CONTENT, experiment_id="EXP-2-FNDR", spend=500.0,
                              impressions=9000, clicks=300, leads=7, primary_outcomes=0, days_active=14,
                              raw_telemetry={"delay_damping": 0.35})]
    out = SVC.normalize_results(raw, plan, _priors())[0]
    assert out.raw_metrics["response_delay_suspected"] is True


def test_benchmark_ratio_uses_priors():
    plan = _plan([_alloc(Channel.GOOGLE_SEARCH, "EXP-2-GOOG", "CFOs", 350.0, 14)])
    raw = [RawExecutionResult(channel=Channel.GOOGLE_SEARCH, experiment_id="EXP-2-GOOG", spend=640.0,
                              impressions=8000, clicks=300, leads=4, primary_outcomes=2, days_active=14)]
    out = SVC.normalize_results(raw, plan, _priors())[0]
    assert out.observed_cac == 320.0
    assert out.raw_metrics["benchmark_cac_median"] == 320.0
    assert out.raw_metrics["benchmark_cac_ratio"] == 1.0


def test_deterministic_and_one_result_per_raw():
    plan = _plan([
        _alloc(Channel.GOOGLE_SEARCH, "EXP-2-GOOG", "CFOs searching", 350.0, 14),
        _alloc(Channel.FOUNDER_CONTENT, "EXP-2-FNDR", "Founder followers", 650.0, 30),
    ])
    raw = [
        RawExecutionResult(channel=Channel.GOOGLE_SEARCH, experiment_id="EXP-2-GOOG", spend=800.0,
                           impressions=10000, clicks=400, leads=8, primary_outcomes=3, days_active=14),
        RawExecutionResult(channel=Channel.FOUNDER_CONTENT, experiment_id="EXP-2-FNDR", spend=500.0,
                           impressions=9000, clicks=300, leads=5, primary_outcomes=1, days_active=14),
    ]
    a = SVC.normalize_results(raw, plan, _priors())
    b = SVC.normalize_results(raw, plan, _priors())
    assert len(a) == 2
    assert [x.model_dump() for x in a] == [x.model_dump() for x in b]
