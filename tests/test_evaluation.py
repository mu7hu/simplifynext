"""Unit tests for the scientific evaluation harness and 6 agent metrics."""

from traction.evaluation.harness import EvaluationHarness
from traction.baselines.allocators import EqualSplitAllocator, OracleAllocator


def test_evaluation_metrics_generation(tmp_path):
    harness = EvaluationHarness(num_startups=2, num_cycles=3, seed=99)
    csv_file = str(tmp_path / "test_eval.csv")
    json_file = str(tmp_path / "test_eval.json")

    summary = harness.run_all(csv_path=csv_file, json_path=json_file)

    assert "Oracle" in summary
    assert "Equal Split" in summary
    assert "Traction (Agentic)" in summary

    traction_m = summary["Traction (Agentic)"]
    # Verify the official SimplifyNext 6 Digital Agent Metrics are present
    assert traction_m["schema_validation_pass_rate"] == 1.0
    assert traction_m["tool_call_success_rate"] == 1.0
    assert traction_m["task_completion_rate"] == 1.0
    assert traction_m["loop_discipline_rate"] == 1.0
    assert traction_m["answer_fidelity_score"] > 0.90
