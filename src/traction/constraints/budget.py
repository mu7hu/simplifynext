"""Deterministic budget validation and mathematical constraint enforcement."""

from typing import Optional
from traction.schemas.experiment import ExperimentPlan, Allocation, Channel
from traction.schemas.founder import FounderBrief, ExclusionRule


def validate_budget_sum(plan: ExperimentPlan, total_budget: float, tolerance: float = 0.05) -> tuple[bool, str]:
    """Validate that proposed allocations sum exactly to the available budget within tolerance."""
    actual_sum = sum(a.proposed_budget for a in plan.allocations)
    diff = abs(actual_sum - total_budget)
    if diff > tolerance:
        return False, f"Allocations sum to ${actual_sum:.2f}, which does not match total budget ${total_budget:.2f} (diff: ${diff:.2f})"
    return True, "Budget sum valid."


def rebalance_micro_cents(plan: ExperimentPlan, total_budget: float) -> ExperimentPlan:
    """Deterministically adjust micro-cent floating point discrepancies so allocations sum exactly to total_budget."""
    if not plan.allocations:
        return plan

    current_sum = sum(a.proposed_budget for a in plan.allocations)
    delta = round(total_budget - current_sum, 2)

    if abs(delta) > 0.0 and abs(delta) <= 0.05:
        # Adjust the largest allocation by the rounding delta
        largest_alloc = max(plan.allocations, key=lambda a: a.proposed_budget)
        largest_alloc.proposed_budget = round(largest_alloc.proposed_budget + delta, 2)
        largest_alloc.proposed_share = round(largest_alloc.proposed_budget / total_budget, 4)

    # Ensure all proposed_share fields correctly reflect proposed_budget / total_budget.
    # A zero-budget plan is valid for simulator/test scenarios, so avoid a
    # division-by-zero while preserving zero shares.
    for a in plan.allocations:
        a.proposed_share = round(a.proposed_budget / total_budget, 4) if total_budget else 0.0

    plan.total_budget = total_budget

    return plan


def validate_hard_constraints(plan: ExperimentPlan, exclusions: list[ExclusionRule]) -> tuple[bool, str]:
    """Ensure hard-excluded channels receive zero spend."""
    excluded_channels = {e.channel.upper() for e in exclusions}
    for a in plan.allocations:
        if a.channel.value.upper() in excluded_channels and a.proposed_budget > 0:
            return False, f"Violation: Channel {a.channel.value} is hard-excluded but was allocated ${a.proposed_budget:.2f}"
    return True, "Hard constraints satisfied."


def validate_no_negative_spending(plan: ExperimentPlan) -> tuple[bool, str]:
    """Ensure no allocation contains negative spend or share."""
    for a in plan.allocations:
        if a.proposed_budget < 0 or a.proposed_share < 0:
            return False, f"Violation: Channel {a.channel.value} has negative budget ${a.proposed_budget:.2f}"
    return True, "No negative spending."


def validate_min_max_allocations(
    plan: ExperimentPlan, 
    min_spend_per_active_channel: float = 50.0,
    max_single_channel_share: float = 0.85
) -> tuple[bool, str]:
    """Ensure active channels receive sufficient test budget and no single channel monopolizes budget."""
    total = plan.total_budget
    for a in plan.allocations:
        if 0 < a.proposed_budget < min_spend_per_active_channel:
            return False, f"Channel {a.channel.value} allocated ${a.proposed_budget:.2f}, below minimum test floor ${min_spend_per_active_channel:.2f}"
        if (a.proposed_budget / total) > max_single_channel_share:
            return False, f"Channel {a.channel.value} allocated {a.proposed_share:.1%}, exceeding max risk cap {max_single_channel_share:.1%}"
    return True, "Min/max allocation rules satisfied."


def validate_plan_constraints(plan: ExperimentPlan, brief: FounderBrief) -> tuple[bool, list[str]]:
    """Comprehensive deterministic validation of an ExperimentPlan against all hard rules."""
    errors: list[str] = []

    # 1. Negative check
    ok_neg, msg_neg = validate_no_negative_spending(plan)
    if not ok_neg:
        errors.append(msg_neg)

    # 2. Budget sum check
    ok_sum, msg_sum = validate_budget_sum(plan, brief.total_budget)
    if not ok_sum:
        errors.append(msg_sum)

    # 3. Hard exclusions check
    ok_excl, msg_excl = validate_hard_constraints(plan, brief.hard_exclusions)
    if not ok_excl:
        errors.append(msg_excl)

    # 4. Risk / Concentration check
    ok_bounds, msg_bounds = validate_min_max_allocations(plan)
    if not ok_bounds:
        errors.append(msg_bounds)

    return len(errors) == 0, errors
