"""Conditional routing functions for LangGraph execution."""

from langgraph.graph import END
from traction.graph.state import TractionGraphState


def route_after_validation(state: TractionGraphState) -> str:
    """Route after plan validation: proceed to approval gate, repair, or end on failure."""
    if state.get("plan_valid", False):
        return "approval_gate"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count < max_retries:
        return "strategist_repair"
    else:
        return END  # Bounded failure exit


def route_after_approval(state: TractionGraphState) -> str:
    """Route after founder gate: proceed to execution or founder revision."""
    status = state.get("approval_status", "REJECTED")
    if status == "PENDING":
        return "end"
    if status == "APPROVED":
        return "execute"
    else:
        return "founder_revision"


def route_after_digest(state: TractionGraphState) -> str:
    """Check loop discipline: route to next cycle or cleanly terminate at iteration limit."""
    if state.get("should_stop", False):
        return END

    iter_count = state.get("iteration_count", 0)
    max_iters = state.get("max_iterations", 20)

    # Check loop cap (Guardrail)
    if iter_count >= max_iters:
        return END

    if state.get("next_cycle_requested", False):
        return "load_context"
    else:
        return END
