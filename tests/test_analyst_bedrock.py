"""Component tests for the real (Bedrock-backed) AnalystAgent.

Covers the deterministic rule engine (used as the offline fallback) and the
mandatory safety post-processing that also wraps live Bedrock output.
"""

from __future__ import annotations

import pytest

from augury.agents.analyst import BedrockAnalystAgent
from augury.schemas.analysis import AnalysisReport, ExperimentVerdict, Verdict
from augury.schemas.experiment import Channel

from tests._analyst_fixtures import (
    sample_plan,
    sample_priors,
    sample_results_mixed,
    result,
)


def _deterministic_agent() -> BedrockAnalystAgent:
    return BedrockAnalystAgent(force_deterministic=True)


def test_returns_validated_analysis_report():
    report = _deterministic_agent().analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())
    assert isinstance(report, AnalysisReport)
    # Exactly one verdict per planned channel, each a real ExperimentVerdict.
    assert {v.channel for v in report.verdicts} == {a.channel for a in sample_plan().allocations}
    assert all(isinstance(v, ExperimentVerdict) for v in report.verdicts)
    assert len(report.verdicts) == 3


def test_incomplete_window_is_never_cut():
    """The Founder Content window is 12/30 days with 0 outcomes: must NOT be CUT."""
    report = _deterministic_agent().analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())
    fc = next(v for v in report.verdicts if v.channel == Channel.FOUNDER_CONTENT)
    assert fc.evaluation_window_complete is False
    assert fc.verdict == Verdict.INSUFFICIENT_DATA
    assert fc.verdict != Verdict.CUT
    assert fc.recommended_budget_direction in {"MAINTAIN", "DECREASE"}


def test_strong_complete_window_scales():
    report = _deterministic_agent().analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())
    g = next(v for v in report.verdicts if v.channel == Channel.GOOGLE_SEARCH)
    assert g.verdict == Verdict.SCALE
    assert g.recommended_budget_direction == "INCREASE"
    assert g.observed_cost_per_outcome < g.target_cost_per_outcome
    assert g.evaluation_window_complete is True


def test_complete_window_zero_outcomes_with_real_spend_is_cut():
    report = _deterministic_agent().analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())
    ce = next(v for v in report.verdicts if v.channel == Channel.COLD_EMAIL)
    assert ce.verdict == Verdict.CUT
    assert ce.recommended_budget_direction in {"DECREASE", "PAUSE"}
    assert ce.evidence_count == 0


def test_overlapping_audiences_get_attribution_warning():
    report = _deterministic_agent().analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())
    by_ch = {v.channel: v for v in report.verdicts}
    assert by_ch[Channel.GOOGLE_SEARCH].attribution_warning
    assert by_ch[Channel.COLD_EMAIL].attribution_warning
    # Founder Content targets a distinct audience -> no warning.
    assert by_ch[Channel.FOUNDER_CONTENT].attribution_warning is None


def test_benchmark_prior_backstops_sparse_evidence():
    """Single outcome, no allocation threshold help: prior median keeps CAC comparison sane."""
    plan = sample_plan()
    # One outcome slightly under the blended (threshold+prior)/2 target -> HOLD, not SCALE.
    res = [
        result(Channel.GOOGLE_SEARCH, "EXP-02-GOOG", spend=300.0, outcomes=1, cac=300.0,
               days=14, window=14, complete=True),
        result(Channel.COLD_EMAIL, "EXP-02-COLD", spend=380.0, outcomes=1, cac=380.0,
               days=14, window=14, complete=True),
        result(Channel.FOUNDER_CONTENT, "EXP-02-FNDR", spend=200.0, outcomes=0, cac=200.0,
               days=30, window=30, complete=True),
    ]
    report = _deterministic_agent().analyze_cycle(2, plan, res, sample_priors())
    g = next(v for v in report.verdicts if v.channel == Channel.GOOGLE_SEARCH)
    assert g.verdict == Verdict.HOLD  # thin evidence -> not scaled despite good CAC
    assert g.target_cost_per_outcome > 0


def test_missing_results_yield_insufficient_data():
    report = _deterministic_agent().analyze_cycle(2, sample_plan(), [], sample_priors())
    assert len(report.verdicts) == 3
    assert all(v.verdict == Verdict.INSUFFICIENT_DATA for v in report.verdicts)
    assert all(v.target_cost_per_outcome > 0 for v in report.verdicts)


# --------------------------------------------------------------------------- #
# Mocked Bedrock response: the LLM returns a premature CUT on an incomplete    #
# window; post-processing must downgrade it to INSUFFICIENT_DATA.             #
# --------------------------------------------------------------------------- #

class _FakeStructuredModel:
    def __init__(self, report: AnalysisReport):
        self._report = report
        self.calls = 0

    def invoke(self, messages, **kwargs):
        self.calls += 1
        return self._report


def _llm_report_with_premature_cut() -> AnalysisReport:
    """A deliberately sloppy LLM payload: premature CUT, out-of-range confidence,
    a direction synonym, and a missing channel. Built with model_construct so the
    invalid values reach post-processing the way an unvalidated LLM dict would."""
    return AnalysisReport.model_construct(
        cycle_id=2,
        executive_summary="LLM says cut everything early.",
        primary_bottleneck=None,
        recommended_explore_ratio=0.3,
        verdicts=[
            ExperimentVerdict.model_construct(
                channel=Channel.FOUNDER_CONTENT, experiment_id="EXP-02-FNDR", verdict=Verdict.CUT,
                confidence=0.9, observed_cost_per_outcome=450.0, target_cost_per_outcome=650.0,
                evidence_count=0, evaluation_window_complete=True,  # LLM wrongly claims complete
                reasoning_summary="Looks bad already.", recommended_budget_direction="PAUSE",
                learning="kill it", attribution_warning=None,
            ),
            ExperimentVerdict.model_construct(
                channel=Channel.GOOGLE_SEARCH, experiment_id="EXP-02-GOOG", verdict=Verdict.SCALE,
                confidence=1.4, observed_cost_per_outcome=266.67, target_cost_per_outcome=350.0,
                evidence_count=3, evaluation_window_complete=True,
                reasoning_summary="Great.", recommended_budget_direction="scale up",  # synonym
                learning="scale", attribution_warning=None,
            ),
        ],
    )


def test_postprocess_overrides_llm_premature_cut():
    fake = _FakeStructuredModel(_llm_report_with_premature_cut())
    agent = BedrockAnalystAgent(structured_model=fake)

    report = agent.analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())

    assert fake.calls == 1  # the LLM path was actually used
    assert isinstance(report, AnalysisReport)

    fc = next(v for v in report.verdicts if v.channel == Channel.FOUNDER_CONTENT)
    assert fc.verdict == Verdict.INSUFFICIENT_DATA  # downgraded from CUT
    assert fc.evaluation_window_complete is False   # corrected from measurement truth
    assert "WINDOW GUARD" in fc.reasoning_summary

    g = next(v for v in report.verdicts if v.channel == Channel.GOOGLE_SEARCH)
    assert 0.0 <= g.confidence <= 1.0               # clamped from 1.4
    assert g.recommended_budget_direction == "INCREASE"  # normalized from "scale up"

    # LLM omitted COLD_EMAIL entirely -> coverage fills it in.
    assert any(v.channel == Channel.COLD_EMAIL for v in report.verdicts)
    assert len(report.verdicts) == 3


def test_llm_failure_falls_back_to_deterministic():
    class _Boom:
        def invoke(self, *a, **k):
            raise RuntimeError("bedrock unavailable")

    agent = BedrockAnalystAgent(structured_model=_Boom())
    report = agent.analyze_cycle(2, sample_plan(), sample_results_mixed(), sample_priors())
    assert isinstance(report, AnalysisReport)
    # Same protective outcome as the pure deterministic path.
    fc = next(v for v in report.verdicts if v.channel == Channel.FOUNDER_CONTENT)
    assert fc.verdict == Verdict.INSUFFICIENT_DATA
