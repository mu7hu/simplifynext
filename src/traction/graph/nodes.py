"""LangGraph node implementations for Traction."""

from datetime import datetime
from typing import Any
from traction.logging import logger
from traction.graph.state import TractionGraphState
from traction.schemas.experiment import Channel
from traction.constraints.budget import validate_plan_constraints, rebalance_micro_cents
from traction.approval.base import ApprovalAction


def node_load_context(state: TractionGraphState, ledger, profiler, intake) -> dict[str, Any]:
    """Load startup profile, benchmark priors, and concise historical ledger summary."""
    startup_id = state.get("startup_id", "default_startup")
    cycle_id = state.get("cycle_id", 1)

    brief = state.get("founder_brief") or intake.get_founder_brief(startup_id)
    profile = state.get("startup_profile") or profiler.get_startup_profile(startup_id)
    priors = state.get("benchmark_priors") or profiler.get_benchmark_priors(startup_id)

    history_summary = ledger.get_historical_summary(startup_id)
    recent_learnings = ledger.get_recent_learnings(startup_id, limit=4)

    # Fetch last cycle verdicts if available
    history = ledger.get_startup_history(startup_id)
    last_cycle_entries = [e for e in history if e.cycle_id == cycle_id - 1]
    recent_verdicts = [
        {
            "channel": e.channel.value,
            "verdict": e.verdict.value,
            "observed_cost_per_outcome": e.observed_cac,
            "reasoning_summary": e.learning
        }
        for e in last_cycle_entries
    ]

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "load_context",
        "cycle_id": cycle_id,
        "message": f"Context loaded for {brief.startup_name}. Prior cycles in ledger: {history_summary.total_cycles_completed}"
    }

    return {
        "founder_brief": brief,
        "startup_profile": profile,
        "benchmark_priors": priors,
        "recent_learnings": recent_learnings,
        "recent_verdicts": recent_verdicts,
        "events": (state.get("events", []) + [event]),
        "retry_count": 0,
        "iteration_count": state.get("iteration_count", 0) + 1
    }


def node_strategist(state: TractionGraphState, strategist_agent, ledger) -> dict[str, Any]:
    """Invoke Strategist Agent to formulate the proposed ExperimentPlan."""
    cycle_id = state.get("cycle_id", 1)
    brief = state["founder_brief"]
    profile = state["startup_profile"]
    priors = state["benchmark_priors"]
    history_summary = ledger.get_historical_summary(state["startup_id"])
    recent_verdicts = state.get("recent_verdicts", [])
    feedback = state.get("founder_feedback")

    proposed_plan = strategist_agent.plan_cycle(
        cycle_id=cycle_id,
        brief=brief,
        profile=profile,
        priors=priors,
        history_summary=history_summary,
        recent_verdicts=recent_verdicts,
        founder_feedback=feedback
    )

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "strategist",
        "cycle_id": cycle_id,
        "message": f"Strategist formulated plan with {len(proposed_plan.allocations)} allocations."
    }

    return {
        "proposed_plan": proposed_plan,
        "events": (state.get("events", []) + [event]),
        "founder_feedback": None  # clear consumed feedback
    }


def node_validate_plan(state: TractionGraphState) -> dict[str, Any]:
    """Deterministically validate the proposed plan against all constraints."""
    plan = state["proposed_plan"]
    brief = state["founder_brief"]

    is_valid, errors = validate_plan_constraints(plan, brief)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "validate_plan",
        "is_valid": is_valid,
        "errors": errors
    }

    return {
        "plan_valid": is_valid,
        "constraint_errors": errors,
        "events": (state.get("events", []) + [event])
    }


def node_strategist_repair(state: TractionGraphState, strategist_agent) -> dict[str, Any]:
    """Repair invalid plan using bounded self-repair loop."""
    invalid_plan = state["proposed_plan"]
    brief = state["founder_brief"]
    errors = state.get("constraint_errors", [])
    retry_count = state.get("retry_count", 0) + 1

    repaired_plan = strategist_agent.repair_plan(invalid_plan, brief, errors)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "strategist_repair",
        "retry_count": retry_count,
        "message": f"Attempted repair on plan (retry {retry_count}/{state.get('max_retries', 2)})"
    }

    return {
        "proposed_plan": repaired_plan,
        "retry_count": retry_count,
        "events": (state.get("events", []) + [event])
    }


def node_approval_gate(state: TractionGraphState, approval_gate) -> dict[str, Any]:
    """Pause at human approval gate before executing any spend."""
    proposed_plan = state["proposed_plan"]
    current_plan = state.get("approved_plan")

    if state.get("approval_only"):
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "node": "approval_gate",
            "action": "PENDING",
            "message": "Plan is ready and waiting for founder approval.",
        }
        return {
            "approval_status": "PENDING",
            "events": (state.get("events", []) + [event]),
        }

    decision = approval_gate.evaluate(current_plan, proposed_plan)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "approval_gate",
        "action": decision.action.value,
        "feedback": decision.feedback
    }

    if decision.action == ApprovalAction.APPROVE:
        return {
            "approved_plan": proposed_plan,
            "approval_status": "APPROVED",
            "events": (state.get("events", []) + [event])
        }
    elif decision.action == ApprovalAction.EDIT and decision.revised_allocations:
        # Apply founder manual edits
        for a in proposed_plan.allocations:
            if a.channel.value in decision.revised_allocations:
                a.proposed_budget = decision.revised_allocations[a.channel.value]
        # Deterministic micro-cent rebalance
        rebalanced = rebalance_micro_cents(proposed_plan, state["founder_brief"].total_budget)
        is_valid, errors = validate_plan_constraints(rebalanced, state["founder_brief"])
        if not is_valid:
            return {
                "approval_status": "REJECTED",
                "founder_feedback": "Edited allocation failed deterministic validation: " + "; ".join(errors),
                "constraint_errors": errors,
                "events": (state.get("events", []) + [event])
            }
        return {
            "approved_plan": rebalanced,
            "approval_status": "APPROVED",
            "events": (state.get("events", []) + [event])
        }
    else:
        return {
            "approval_status": "REJECTED",
            "founder_feedback": decision.feedback,
            "events": (state.get("events", []) + [event])
        }


def node_founder_revision(state: TractionGraphState) -> dict[str, Any]:
    """Handle founder rejection feedback and prepare state for replanning."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "founder_revision",
        "message": "Routing back to Strategist with founder rejection feedback."
    }
    return {
        "events": (state.get("events", []) + [event])
    }


def node_execute(state: TractionGraphState, execution_service) -> dict[str, Any]:
    """Deploy approved budget to execution service or simulator."""
    plan = state["approved_plan"]
    raw_results = execution_service.execute_plan(plan)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "execute",
        "cycle_id": plan.cycle_id,
        "total_spend": sum(r.spend for r in raw_results),
        "total_outcomes": sum(r.primary_outcomes for r in raw_results)
    }

    return {
        "raw_results": raw_results,
        "events": (state.get("events", []) + [event])
    }


def node_measure(state: TractionGraphState, measurement_service) -> dict[str, Any]:
    """Normalize raw telemetry into comparable ExperimentResults."""
    raw_results = state["raw_results"]
    plan = state["approved_plan"]
    priors = state["benchmark_priors"]

    normalized = measurement_service.normalize_results(raw_results, plan, priors)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "measure",
        "channel_count": len(normalized)
    }

    return {
        "normalized_results": normalized,
        "events": (state.get("events", []) + [event])
    }


def node_analyst(state: TractionGraphState, analyst_agent) -> dict[str, Any]:
    """Invoke Analyst Agent to evaluate results and produce verdicts."""
    cycle_id = state.get("cycle_id", 1)
    plan = state["approved_plan"]
    normalized_results = state["normalized_results"]
    priors = state["benchmark_priors"]

    report = analyst_agent.analyze_cycle(
        cycle_id=cycle_id,
        plan=plan,
        results=normalized_results,
        benchmark_priors=priors
    )

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "analyst",
        "verdict_summary": [f"{v.channel.value}: {v.verdict.value}" for v in report.verdicts]
    }

    return {
        "analysis_report": report,
        "events": (state.get("events", []) + [event])
    }


def node_validate_analysis(state: TractionGraphState) -> dict[str, Any]:
    """Deterministically check that Analyst returned valid verdicts and respected window constraints."""
    report = state["analysis_report"]
    normalized = {r.channel: r for r in state["normalized_results"]}

    for v in report.verdicts:
        r = normalized.get(v.channel)
        if r and not r.is_window_complete and v.verdict.value == "CUT":
            # Guard against premature cuts during incomplete evaluation windows
            v.verdict = type(v.verdict).HOLD
            v.reasoning_summary += " [GUARD: Overridden to HOLD due to incomplete evaluation window]"

    return {
        "analysis_report": report
    }


def node_persist_ledger(state: TractionGraphState, ledger) -> dict[str, Any]:
    """Persist plan, normalized results, verdicts, and learnings to SQLite."""
    startup_id = state["startup_id"]
    cycle_id = state.get("cycle_id", 1)
    plan = state["approved_plan"]
    results = state["normalized_results"]
    report = state["analysis_report"]

    ledger.append_plan(startup_id, plan)
    ledger.append_results(startup_id, cycle_id, results)
    ledger.append_analysis(startup_id, report)

    recent_learnings = ledger.get_recent_learnings(startup_id, limit=5)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "persist_ledger",
        "message": f"Persisted cycle {cycle_id} to Experiment Ledger database."
    }

    return {
        "recent_learnings": recent_learnings,
        "events": (state.get("events", []) + [event])
    }


def node_generate_digest(state: TractionGraphState, digest_service) -> dict[str, Any]:
    """Generate weekly markdown digest for founder."""
    plan = state["approved_plan"]
    results = state["normalized_results"]
    report = state["analysis_report"]
    learnings = state.get("recent_learnings", [])

    digest_md = digest_service.generate_digest(plan, results, report, learnings)

    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "node": "generate_digest",
        "message": "Weekly founder digest generated."
    }

    return {
        "digest_markdown": digest_md,
        "events": (state.get("events", []) + [event])
    }
