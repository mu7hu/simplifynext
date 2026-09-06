"""Founder digest service interface and markdown summary generator."""

from abc import ABC, abstractmethod
from typing import Optional
from traction.schemas.experiment import ExperimentPlan
from traction.schemas.analysis import AnalysisReport
from traction.schemas.result import ExperimentResult


class DigestService(ABC):
    """Abstract interface for publishing executive summaries for founders."""

    @abstractmethod
    def generate_digest(
        self,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        report: AnalysisReport,
        learnings: list[str]
    ) -> str:
        pass


class MarkdownDigestService(DigestService):
    """Generates a structured weekly executive digest for the founder."""

    def generate_digest(
        self,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        report: AnalysisReport,
        learnings: list[str]
    ) -> str:
        total_spend = sum(r.spend for r in results)
        total_outcomes = sum(r.primary_outcomes for r in results)
        blended_cac = round(total_spend / max(1, total_outcomes), 2)

        md = [
            f"# Traction Weekly Portfolio Digest — Cycle {plan.cycle_id}",
            f"**Total Spend:** ${total_spend:,.2f} | **Total Outcomes:** {total_outcomes} | **Blended CAC:** ${blended_cac:.2f}\n",
            "## Executive Summary",
            f"{report.executive_summary}\n",
            "## Channel Verdicts & Performance",
            "| Channel | Spend | Outcomes | Observed CAC | Verdict | Direction |",
            "| :--- | :--- | :--- | :--- | :--- | :--- |"
        ]

        verdict_map = {v.channel: v for v in report.verdicts}
        for r in results:
            v = verdict_map.get(r.channel)
            v_str = v.verdict.value if v else "N/A"
            dir_str = v.recommended_budget_direction if v else "MAINTAIN"
            md.append(f"| **{r.channel.value}** | ${r.spend:,.2f} | {r.primary_outcomes} | ${r.observed_cac:,.2f} | `{v_str}` | {dir_str} |")

        md.append("\n## Key Retained Learnings")
        for idx, l in enumerate(learnings[:4], 1):
            md.append(f"{idx}. {l}")

        return "\n".join(md)
