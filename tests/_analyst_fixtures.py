"""Shared fixtures for the real (Bedrock) Analyst Agent tests."""

from __future__ import annotations

from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import ExperimentResult
from traction.schemas.profile import BenchmarkPrior


def sample_priors() -> list[BenchmarkPrior]:
    return [
        BenchmarkPrior(channel="GOOGLE_SEARCH", median_cac=320.0, min_cac=220.0, max_cac=550.0,
                       avg_cpc=11.5, avg_conversion_rate=0.04, min_evaluation_days=14,
                       rationale="High buyer intent"),
        BenchmarkPrior(channel="COLD_EMAIL", median_cac=400.0, min_cac=250.0, max_cac=700.0,
                       avg_cpc=2.0, avg_conversion_rate=0.015, min_evaluation_days=14,
                       rationale="Niche CFO list"),
        BenchmarkPrior(channel="FOUNDER_CONTENT", median_cac=650.0, min_cac=300.0, max_cac=1800.0,
                       avg_cpc=7.5, avg_conversion_rate=0.003, min_evaluation_days=30,
                       rationale="Slow, expensive for direct demo capture"),
    ]


def _alloc(channel: Channel, exp_id: str, audience: str, threshold: float, window: int,
           exploration: bool = False) -> Allocation:
    return Allocation(
        channel=channel, experiment_id=exp_id, current_budget=0.0, proposed_budget=500.0,
        proposed_share=0.25, hypothesis="hypothesis", audience=audience, message_angle="angle",
        success_threshold=threshold, reason="reason", evidence_used="evidence",
        evaluation_window_days=window, is_exploration=exploration,
    )


def sample_plan(cycle_id: int = 2) -> ExperimentPlan:
    """3 channels; GOOGLE_SEARCH and COLD_EMAIL deliberately share an audience."""
    return ExperimentPlan(
        cycle_id=cycle_id,
        total_budget=1500.0,
        primary_goal="Qualified Demo Bookings",
        allocations=[
            _alloc(Channel.GOOGLE_SEARCH, "EXP-02-GOOG",
                   "Mid-market CFOs and Controllers evaluating finance software", 350.0, 14),
            _alloc(Channel.COLD_EMAIL, "EXP-02-COLD",
                   "Controllers and CFOs at mid-market finance teams", 400.0, 14),
            _alloc(Channel.FOUNDER_CONTENT, "EXP-02-FNDR",
                   "Founder personal LinkedIn brand followers", 650.0, 30, exploration=True),
        ],
        exploration_budget_pct=0.25,
        exploitation_budget_pct=0.5,
        strategy_summary="summary",
    )


def result(channel: Channel, exp_id: str, spend: float, outcomes: int, cac: float,
           days: int, window: int, complete: bool, ctr: float = 0.03, conv: float = 0.02) -> ExperimentResult:
    return ExperimentResult(
        channel=channel, experiment_id=exp_id, spend=spend, primary_outcomes=outcomes,
        observed_cac=cac, conversion_rate=conv, click_through_rate=ctr, days_observed=days,
        evaluation_window_days=window, is_window_complete=complete,
    )


def sample_results_mixed() -> list[ExperimentResult]:
    """Google = clear SCALE; Cold Email = expensive CUT; Founder Content = incomplete window, weak early data."""
    return [
        result(Channel.GOOGLE_SEARCH, "EXP-02-GOOG", spend=800.0, outcomes=3, cac=266.67,
               days=14, window=14, complete=True, ctr=0.07, conv=0.05),
        result(Channel.COLD_EMAIL, "EXP-02-COLD", spend=600.0, outcomes=0, cac=600.0,
               days=14, window=14, complete=True, ctr=0.005, conv=0.0),
        result(Channel.FOUNDER_CONTENT, "EXP-02-FNDR", spend=450.0, outcomes=0, cac=450.0,
               days=12, window=30, complete=False, ctr=0.02, conv=0.0),
    ]


def payload_dict(cycle_id: int = 2) -> dict:
    return {
        "cycle_id": cycle_id,
        "plan": sample_plan(cycle_id).model_dump(mode="json"),
        "results": [r.model_dump(mode="json") for r in sample_results_mixed()],
        "benchmark_priors": [p.model_dump(mode="json") for p in sample_priors()],
    }
