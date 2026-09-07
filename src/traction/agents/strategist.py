"""Strategist Agent: Proposes portfolio allocations and manages bounded self-repair."""

from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from traction.config import settings
from traction.logging import logger
from traction.models import get_strategist_model
from traction.schemas.founder import FounderBrief
from traction.schemas.profile import StartupProfile, BenchmarkPrior
from traction.schemas.experiment import ExperimentPlan, Channel
from traction.schemas.ledger import HistoricalSummary
from traction.constraints.budget import validate_plan_constraints, rebalance_micro_cents
from traction.constraints.policies import ExploreExploitPolicy
from traction.agents.prompts import STRATEGIST_SYSTEM_PROMPT


class StrategistAgent:
    """Strategist reasoning agent implementing portfolio allocation and bounded self-repair."""

    def __init__(self, model=None, policy: Optional[ExploreExploitPolicy] = None):
        self.model = model or get_strategist_model()
        self.structured_model = self.model.with_structured_output(ExperimentPlan)
        self.policy = policy or ExploreExploitPolicy()

    def plan_cycle(
        self,
        cycle_id: int,
        brief: FounderBrief,
        profile: StartupProfile,
        priors: list[BenchmarkPrior],
        history_summary: HistoricalSummary,
        recent_verdicts: list[dict],
        founder_feedback: Optional[str] = None
    ) -> ExperimentPlan:
        """Generate a proposed ExperimentPlan."""
        prompt_content = self._build_prompt(
            cycle_id=cycle_id,
            brief=brief,
            profile=profile,
            priors=priors,
            history_summary=history_summary,
            recent_verdicts=recent_verdicts,
            founder_feedback=founder_feedback
        )

        messages = [
            SystemMessage(content=STRATEGIST_SYSTEM_PROMPT),
            HumanMessage(content=prompt_content)
        ]

        logger.info(f"Strategist invoking model for cycle {cycle_id}", extra={"cycle_id": cycle_id, "agent": "strategist"})
        raw_plan = self.structured_model.invoke(messages)

        # The offline stub uses the seeded LedgerAI budget. Scale it when a
        # caller supplies a different validated founder budget; live models
        # are also normalized through this same deterministic boundary.
        adjusted_plan = self._normalize_budget(raw_plan, brief.total_budget)
        return adjusted_plan

    def repair_plan(
        self,
        invalid_plan: ExperimentPlan,
        brief: FounderBrief,
        constraint_errors: list[str]
    ) -> ExperimentPlan:
        """Attempt bounded self-repair on an invalid plan using explicit error diagnostics."""
        repair_prompt = f"""Your previous ExperimentPlan failed deterministic validation with these errors:
{chr(10).join(f'- {e}' for e in constraint_errors)}

Please correct the allocations so that:
1. Total budget equals ${brief.total_budget:.2f} exactly.
2. Hard excluded channels receive $0.00.
3. No negative allocations exist.

Preserve the cycle ID, business context and intended experiments. Correct this complete plan:
{invalid_plan.model_dump_json()}

Founder brief, including hard exclusions:
{brief.model_dump_json()}
"""
        messages = [
            SystemMessage(content=STRATEGIST_SYSTEM_PROMPT),
            HumanMessage(content=repair_prompt)
        ]

        logger.warning("Strategist repairing invalid plan", extra={"agent": "strategist"})
        repaired_plan = self.structured_model.invoke(messages)
        return self._normalize_budget(repaired_plan, brief.total_budget)

    @staticmethod
    def _normalize_budget(plan: ExperimentPlan, total_budget: float) -> ExperimentPlan:
        """Scale model output to the founder budget before final validation."""
        proposed_sum = sum(a.proposed_budget for a in plan.allocations)
        if proposed_sum and abs(proposed_sum - total_budget) > 0.005:
            scale = total_budget / proposed_sum
            for allocation in plan.allocations:
                allocation.proposed_budget = round(allocation.proposed_budget * scale, 2)
        return rebalance_micro_cents(plan, total_budget)

    def _build_prompt(
        self,
        cycle_id: int,
        brief: FounderBrief,
        profile: StartupProfile,
        priors: list[BenchmarkPrior],
        history_summary: HistoricalSummary,
        recent_verdicts: list[dict],
        founder_feedback: Optional[str]
    ) -> str:
        rec_explore = self.policy.get_exploration_target(cycle_id)
        rec_exploit = self.policy.get_exploitation_target(cycle_id)

        sections = [
            f"# Planning Context for Cycle {cycle_id}",
            f"Startup: {brief.startup_name} ({profile.stage.value}, {profile.sector.value})",
            f"Pitch: {brief.one_line_pitch}",
            f"Total Available Budget: ${brief.total_budget:,.2f}",
            f"Primary Goal: {brief.primary_goal.metric_name} (Target CAC: ${brief.primary_goal.target_cac:.2f})",
            f"Recommended Policy: {rec_exploit*100:.0f}% Exploit / {rec_explore*100:.0f}% Explore",
            "\n## Soft Founder Preferences (Priors):",
            *(f"- {p.channel}: belief strength {p.prior_belief_strength} ('{p.founder_note}')" for p in brief.soft_preferences),
            "\n## Hard Channel Exclusions:",
        ]

        if brief.hard_exclusions:
            sections.extend(f"- {e.channel} (Reason: {e.reason})" for e in brief.hard_exclusions)
        else:
            sections.append("- None")

        sections.extend([
            "\n## Industry Benchmark Priors:",
            *(f"- {p.channel}: median CAC ${p.median_cac:.2f}, min eval {p.min_evaluation_days} days ({p.rationale})" for p in priors),
            f"\n## Historical Memory Summary (Cycles completed: {history_summary.total_cycles_completed}):",
            f"- Total Lifetime Spend: ${history_summary.total_spend:,.2f}",
            f"- Total Outcomes: {history_summary.total_outcomes} (Blended CAC: ${history_summary.lifetime_cac:.2f})",
            "Recent Learnings:",
        ])

        if history_summary.recent_learnings:
            sections.extend(f"- {l}" for l in history_summary.recent_learnings)
        else:
            sections.append("- No prior learnings recorded yet.")

        if recent_verdicts:
            sections.append("\n## Latest Analyst Verdicts:")
            for v in recent_verdicts:
                sections.append(f"- {v.get('channel')}: `{v.get('verdict')}` (CAC: ${v.get('observed_cost_per_outcome', 0):.2f}, Reason: {v.get('reasoning_summary', '')})")

        if founder_feedback:
            sections.append(f"\n## Founder Feedback from Previous Cycle / Rejection:\n{founder_feedback}")

        sections.append("\nPropose the complete ExperimentPlan for Cycle " + str(cycle_id))
        return "\n".join(sections)
