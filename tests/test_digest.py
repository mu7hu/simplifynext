"""Component tests for the founder DigestService."""

from __future__ import annotations

from augury.agents.analyst import BedrockAnalystAgent
from augury.schemas.analysis import AnalysisReport, ExperimentVerdict, Verdict
from augury.schemas.experiment import Channel
from augury.services.digest import (
    MarkdownDigestService,
    PlainTextDigestService,
    get_digest_service,
)

from tests._analyst_fixtures import sample_plan, sample_priors, sample_results_mixed

LEARNINGS = [
    "Google Search converts qualified demos below target CAC.",
    "Founder Content needs the full 30-day window before judging.",
    "Google Search converts qualified demos below target CAC.",  # dupe -> collapsed
]


def _report() -> AnalysisReport:
    return BedrockAnalystAgent(force_deterministic=True).analyze_cycle(
        2, sample_plan(), sample_results_mixed(), sample_priors()
    )


def test_markdown_digest_explains_outcomes_verdicts_and_movement():
    md = MarkdownDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    assert isinstance(md, str) and len(md) > 0

    # Structure
    for header in (
        "# Augury Weekly Portfolio Digest — Cycle 2",
        "## Executive summary",
        "## What happened this cycle",
        "## Verdicts & why",
        "## Proposed movement for the next cycle",
        "## Learnings to carry forward",
    ):
        assert header in md

    # Outcomes explained
    assert "TL;DR:" in md
    assert "qualified" in md.lower()

    # Every planned channel appears with its verdict
    report = _report()
    for v in report.verdicts:
        assert v.channel.value in md
    assert "SCALE" in md and "CUT" in md and "INSUFFICIENT DATA" in md

    # Proposed movement uses the analyst's directions
    assert "increase budget" in md  # GOOGLE_SEARCH SCALE -> INCREASE
    assert "Recommended explore ratio next cycle" in md


def test_digest_is_not_the_source_of_allocation_truth():
    md = MarkdownDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    assert "deterministic budget engine" in md
    assert "approve" in md.lower()


def test_digest_surfaces_attribution_and_open_windows():
    md = MarkdownDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    assert "Attribution caveats" in md            # GOOGLE_SEARCH / COLD_EMAIL overlap
    assert "still running" in md                  # FOUNDER_CONTENT window 12/30


def test_learnings_are_deduped_and_listed():
    md = MarkdownDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    assert md.count("Google Search converts qualified demos below target CAC.") == 1
    assert "1. " in md


def test_empty_results_do_not_crash():
    plan = sample_plan()
    empty_report = AnalysisReport(
        cycle_id=2,
        executive_summary="No data yet.",
        recommended_explore_ratio=0.3,
        verdicts=[
            ExperimentVerdict(
                channel=a.channel, experiment_id=a.experiment_id, verdict=Verdict.INSUFFICIENT_DATA,
                confidence=0.1, observed_cost_per_outcome=0.0, target_cost_per_outcome=a.success_threshold,
                evidence_count=0, evaluation_window_complete=False, reasoning_summary="No results.",
                recommended_budget_direction="MAINTAIN", learning="",
            )
            for a in plan.allocations
        ],
    )
    md = MarkdownDigestService().generate_digest(plan, [], empty_report, [])
    assert "no qualified outcomes recorded yet" in md
    assert "No new learnings recorded this cycle." in md


def test_plain_text_digest_has_no_markup_but_same_substance():
    txt = PlainTextDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    assert "|" not in txt and "##" not in txt and "# " not in txt
    assert "AUGURY WEEKLY DIGEST - CYCLE 2" in txt
    assert "deterministic budget engine" in txt
    for v in _report().verdicts:
        assert v.channel.value in txt


def test_digest_is_deterministic():
    a = MarkdownDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    b = MarkdownDigestService().generate_digest(sample_plan(), sample_results_mixed(), _report(), LEARNINGS)
    assert a == b


def test_get_digest_service_factory():
    assert isinstance(get_digest_service(), MarkdownDigestService)
    assert isinstance(get_digest_service("markdown"), MarkdownDigestService)
    assert isinstance(get_digest_service("text"), PlainTextDigestService)
    assert isinstance(get_digest_service("plain"), PlainTextDigestService)
