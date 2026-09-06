"""Unit tests verifying bounded loop discipline and termination guarantees."""

from traction.graph.state import TractionGraphState
from traction.graph.routing import route_after_validation, route_after_digest


def test_retry_cap_stops_infinite_repair():
    # If retry count reaches max_retries, must terminate to END
    state: TractionGraphState = {
        "plan_valid": False,
        "retry_count": 2,
        "max_retries": 2
    }
    next_node = route_after_validation(state)
    assert next_node == "__end__"


def test_iteration_cap_stops_runaway_graph():
    # If iteration_count reaches max_iterations, must terminate to END
    state: TractionGraphState = {
        "iteration_count": 20,
        "max_iterations": 20,
        "next_cycle_requested": True
    }
    next_node = route_after_digest(state)
    assert next_node == "__end__"
