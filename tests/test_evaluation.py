"""Unit tests for the scientific evaluation harness and 6 agent metrics."""

from augury.evaluation.harness import EvaluationHarness
from augury.baselines.allocators import EqualSplitAllocator, OracleAllocator


def test_evaluation_metrics_generation(tmp_path):
    harness = EvaluationHarness(num_startups=2, num_cycles=3, seed=99)
    csv_file = str(tmp_path / "test_eval.csv")
    json_file = str(tmp_path / "test_eval.json")

    summary = harness.run_all(csv_path=csv_file, json_path=json_file)

    assert "Oracle" in summary
    assert "Equal Split" in summary
    assert "Augury (Agentic)" in summary

    augury_m = summary["Augury (Agentic)"]
    # Verify the official SimplifyNext 6 Digital Agent Metrics are present
    assert augury_m["schema_validation_pass_rate"] == 1.0
    assert augury_m["tool_call_success_rate"] == 1.0
    assert augury_m["task_completion_rate"] == 1.0
    assert augury_m["loop_discipline_rate"] == 1.0
    assert augury_m["answer_fidelity_score"] > 0.90
