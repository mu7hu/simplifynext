"""Unit tests for SQLite Experiment Ledger persistence."""

import os
from traction.ledger.sqlite import SQLiteExperimentLedger
from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import ExperimentResult
from traction.schemas.analysis import AnalysisReport, ExperimentVerdict, Verdict


def test_ledger_cycle_persistence(tmp_path):
    db_path = str(tmp_path / "test_ledger.db")
    ledger = SQLiteExperimentLedger(db_path)

    plan = ExperimentPlan(
        cycle_id=1,
        total_budget=2000.0,
        primary_goal="Qualified Demos",
        allocations=[
            Allocation(
                channel=Channel.GOOGLE_SEARCH,
                experiment_id="EXP-01-GOOG",
                current_budget=0.0,
                proposed_budget=800.0,
                proposed_share=0.40,
                hypothesis="Search intent converts",
                audience="CFOs",
                message_angle="Close faster",
                evaluation_window_days=14,
                success_threshold=350.0,
                reason="Initial test",
                evidence_used="Benchmark",
                is_exploration=False
            )
        ],
        exploration_budget_pct=0.0,
        exploitation_budget_pct=1.0,
        strategy_summary="Cycle 1 Plan"
    )

    ledger.append_plan("test_startup", plan)
    history = ledger.get_startup_history("test_startup")
    assert len(history) == 1
    assert history[0].planned_budget == 800.0

    # Append Results
    results = [
        ExperimentResult(
            channel=Channel.GOOGLE_SEARCH,
            experiment_id="EXP-01-GOOG",
            spend=800.0,
            primary_outcomes=3,
            observed_cac=266.67,
            conversion_rate=0.045,
            click_through_rate=0.02,
            days_observed=14,
            evaluation_window_days=14,
            is_window_complete=True
        )
    ]
    ledger.append_results("test_startup", 1, results)

    # Append Analysis
    report = AnalysisReport(
        cycle_id=1,
        verdicts=[
            ExperimentVerdict(
                channel=Channel.GOOGLE_SEARCH,
                experiment_id="EXP-01-GOOG",
                verdict=Verdict.SCALE,
                confidence=0.85,
                observed_cost_per_outcome=266.67,
                target_cost_per_outcome=350.0,
                evidence_count=3,
                evaluation_window_complete=True,
                reasoning_summary="Beat CAC target significantly",
                recommended_budget_direction="INCREASE",
                learning="Search intent is high quality for B2B financial reconciliations."
            )
        ],
        executive_summary="Cycle 1 success"
    )
    ledger.append_analysis("test_startup", report)

    summary = ledger.get_historical_summary("test_startup")
    assert summary.total_cycles_completed == 1
    assert summary.total_spend == 800.0
    assert summary.total_outcomes == 3
    assert len(summary.recent_learnings) == 1
    assert "Search intent" in summary.recent_learnings[0]
