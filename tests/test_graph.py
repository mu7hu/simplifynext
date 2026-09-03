"""Unit tests for end-to-end LangGraph supervisor workflow."""

from traction.services.intake import MockIntakeProvider
from traction.services.profiler import MockProfilerService
from traction.services.execution import SimulatedExecutionService
from traction.services.measurement import DefaultMeasurementService
from traction.services.digest import MarkdownDigestService
from traction.simulator.market import MarketSimulator
from traction.ledger.sqlite import SQLiteExperimentLedger
from traction.agents.strategist import StrategistAgent
from traction.agents.analyst import StubAnalystAgent
from traction.approval.cli import AutoApprovalGate
from traction.graph.build import compile_traction_graph


def test_graph_end_to_end_cycle(tmp_path):
    db_path = str(tmp_path / "graph_test.db")
    ledger = SQLiteExperimentLedger(db_path)
    profiler = MockProfilerService()
    intake = MockIntakeProvider()
    market_sim = MarketSimulator(seed=42)
    execution_svc = SimulatedExecutionService(market_sim)
    measurement_svc = DefaultMeasurementService()
    digest_svc = MarkdownDigestService()
    strategist = StrategistAgent()
    analyst = StubAnalystAgent()
    approval_gate = AutoApprovalGate()

    graph = compile_traction_graph(
        ledger=ledger,
        profiler=profiler,
        intake=intake,
        strategist_agent=strategist,
        analyst_agent=analyst,
        approval_gate=approval_gate,
        execution_service=execution_svc,
        measurement_service=measurement_svc,
        digest_service=digest_svc
    )

    state_input = {
        "startup_id": "test_startup",
        "thread_id": "test_thread",
        "cycle_id": 1,
        "iteration_count": 0,
        "retry_count": 0,
        "max_iterations": 5,
        "max_retries": 2,
        "next_cycle_requested": False
    }

    final_state = graph.invoke(state_input)

    assert final_state["approval_status"] == "APPROVED"
    assert final_state["approved_plan"] is not None
    assert len(final_state["normalized_results"]) > 0
    assert final_state["analysis_report"] is not None
    assert len(final_state["digest_markdown"]) > 0

    # Verify ledger was persisted
    history = ledger.get_startup_history("test_startup")
    assert len(history) > 0
