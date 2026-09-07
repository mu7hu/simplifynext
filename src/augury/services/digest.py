"""Founder-facing weekly digest.

``generate_digest(plan, results, report, learnings) -> str`` produces a readable
recap: what happened, the Analyst's verdict and reasoning per channel, the
learnings to carry forward, and the *proposed* next-cycle movement. It is a
communication artifact only - it never sets allocations. The deterministic budget
engine and the human approval gate remain the source of allocation truth, and the
digest says so explicitly.

* ``MarkdownDigestService`` - default, GitHub-flavoured Markdown.
* ``PlainTextDigestService`` - same content, no markup (email / SMS / logs).
* ``get_digest_service(fmt=...)`` - pick one.

Deterministic: no timestamps, stable channel ordering (plan order).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from augury.schemas.experiment import ExperimentPlan
from augury.schemas.analysis import AnalysisReport, ExperimentVerdict, Verdict
from augury.schemas.result import ExperimentResult

_VERDICT_LABEL = {
    Verdict.SCALE: "SCALE ✅",
    Verdict.HOLD: "HOLD ⏸️",
    Verdict.CUT: "CUT ❌",
    Verdict.INSUFFICIENT_DATA: "INSUFFICIENT DATA 🔍",
}
_DIRECTION_PHRASE = {
    "INCREASE": "increase budget",
    "MAINTAIN": "keep budget flat",
    "DECREASE": "reduce budget",
    "PAUSE": "pause the channel",
}
_DISCLAIMER = (
    "These are the Analyst's recommendations for the next planning cycle. Actual "
    "budgets are computed by the deterministic budget engine and only take effect "
    "after you approve them at the human gate."
)


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _cac_marker(observed: float, target: float, outcomes: int) -> str:
    if outcomes <= 0:
        return "no outcomes yet"
    if target <= 0:
        return _money(observed)
    if observed <= target * 0.98:
        return f"{_money(observed)} vs {_money(target)} target  ▼ under"
    if observed >= target * 1.02:
        return f"{_money(observed)} vs {_money(target)} target  ▲ over"
    return f"{_money(observed)} vs {_money(target)} target  ≈ on target"


def _window_note(v: Optional[ExperimentVerdict], r: Optional[ExperimentResult]) -> str:
    if r is not None:
        state = "complete" if r.is_window_complete else "still running"
        return f"{r.days_observed}/{r.evaluation_window_days} days ({state})"
    if v is not None:
        return "complete" if v.evaluation_window_complete else "still running"
    return "n/a"


def _dedupe(seq: list[str], limit: int) -> list[str]:
    out: list[str] = []
    for item in seq:
        text = (item or "").strip()
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


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


class _BaseDigestService(DigestService):
    """Shared digest assembly; subclasses only choose the rendering style."""

    def generate_digest(
        self,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        report: AnalysisReport,
        learnings: list[str],
    ) -> str:
        res_by_ch = {r.channel: r for r in results}
        verdict_by_ch = {v.channel: v for v in report.verdicts}
        alloc_by_ch = {a.channel: a for a in plan.allocations}

        total_spend = sum(r.spend for r in results)
        total_outcomes = sum(r.primary_outcomes for r in results)
        blended_cac = round(total_spend / total_outcomes, 2) if total_outcomes else 0.0
        goal_target = plan.allocations[0].success_threshold if plan.allocations else 0.0

        # ---- headline -----------------------------------------------------
        if total_outcomes:
            cac_line = f"blended CAC {_money(blended_cac)}"
            if goal_target:
                cac_line += f" (target {_money(goal_target)})"
        else:
            cac_line = "no qualified outcomes recorded yet"
        headline = (
            f"Cycle {plan.cycle_id}: spent {_money(total_spend)} for {total_outcomes} "
            f"{plan.primary_goal.lower()} — {cac_line}."
        )

        scaled = [c.value for c, v in verdict_by_ch.items() if v.verdict == Verdict.SCALE]
        cut = [c.value for c, v in verdict_by_ch.items() if v.verdict == Verdict.CUT]

        # ---- per-channel performance rows -------------------------------
        perf_rows = []
        for a in plan.allocations:
            r = res_by_ch.get(a.channel)
            v = verdict_by_ch.get(a.channel)
            target = (v.target_cost_per_outcome if v and v.target_cost_per_outcome > 0 else a.success_threshold)
            spend = r.spend if r else 0.0
            outcomes = r.primary_outcomes if r else 0
            observed = r.observed_cac if r else 0.0
            perf_rows.append({
                "channel": a.channel.value,
                "share": f"{a.proposed_share * 100:.0f}%",
                "spend": _money(spend),
                "outcomes": outcomes,
                "cac": _cac_marker(observed, target, outcomes),
                "window": _window_note(v, r),
                "attribution": (v.attribution_warning if v and v.attribution_warning else None),
            })

        # ---- verdict / reasoning rows ---------------------------------
        verdict_rows = []
        for a in plan.allocations:
            v = verdict_by_ch.get(a.channel)
            if v is None:
                verdict_rows.append({
                    "channel": a.channel.value, "verdict": "N/A", "confidence": "",
                    "why": "No verdict returned for this channel.", "learning": "",
                })
                continue
            verdict_rows.append({
                "channel": a.channel.value,
                "verdict": _VERDICT_LABEL.get(v.verdict, v.verdict.value),
                "confidence": f"{v.confidence * 100:.0f}% confidence",
                "why": v.reasoning_summary,
                "learning": v.learning,
            })

        # ---- proposed next-cycle movement ---------------------------
        move_rows = []
        for a in plan.allocations:
            v = verdict_by_ch.get(a.channel)
            direction = v.recommended_budget_direction if v else "MAINTAIN"
            move_rows.append({
                "channel": a.channel.value,
                "current_share": f"{a.proposed_share * 100:.0f}%",
                "direction": direction,
                "phrase": _DIRECTION_PHRASE.get(direction, direction.lower()),
            })

        carried = _dedupe(list(learnings or []) + [v.learning for v in report.verdicts], limit=6)

        return self._render(
            plan=plan,
            report=report,
            headline=headline,
            scaled=scaled,
            cut=cut,
            total_spend=total_spend,
            total_outcomes=total_outcomes,
            blended_cac=blended_cac,
            perf_rows=perf_rows,
            verdict_rows=verdict_rows,
            move_rows=move_rows,
            carried=carried,
        )

    # subclasses implement rendering
    def _render(self, **_: object) -> str:  # pragma: no cover - abstract-ish
        raise NotImplementedError


class MarkdownDigestService(_BaseDigestService):
    """Generates a structured weekly executive digest for the founder (Markdown)."""

    def _render(self, *, plan, report, headline, scaled, cut, total_spend, total_outcomes,
                blended_cac, perf_rows, verdict_rows, move_rows, carried) -> str:
        md: list[str] = []
        md.append(f"# Augury Weekly Portfolio Digest — Cycle {plan.cycle_id}")
        md.append("")
        md.append(f"**TL;DR:** {headline}")
        if scaled:
            md.append(f"- Scaling: {', '.join(scaled)}")
        if cut:
            md.append(f"- Cutting: {', '.join(cut)}")
        md.append("")

        md.append("## Executive summary")
        md.append(report.executive_summary or "_No summary provided._")
        if report.primary_bottleneck:
            md.append("")
            md.append(f"**Primary bottleneck:** {report.primary_bottleneck}")
        md.append("")

        md.append("## What happened this cycle")
        md.append("| Channel | Share | Spend | Outcomes | Cost per outcome | Evaluation window |")
        md.append("| :--- | ---: | ---: | ---: | :--- | :--- |")
        for row in perf_rows:
            md.append(
                f"| **{row['channel']}** | {row['share']} | {row['spend']} | {row['outcomes']} "
                f"| {row['cac']} | {row['window']} |"
            )
        attn = [f"- **{r['channel']}**: {r['attribution']}" for r in perf_rows if r["attribution"]]
        if attn:
            md.append("")
            md.append("_Attribution caveats:_")
            md.extend(attn)
        md.append("")

        md.append("## Verdicts & why")
        for row in verdict_rows:
            conf = f" ({row['confidence']})" if row["confidence"] else ""
            md.append(f"### {row['channel']} — {row['verdict']}{conf}")
            md.append(row["why"])
            if row["learning"]:
                md.append(f"> Learning: {row['learning']}")
            md.append("")

        md.append("## Proposed movement for the next cycle")
        md.append("| Channel | Current share | Analyst suggests |")
        md.append("| :--- | ---: | :--- |")
        for row in move_rows:
            md.append(f"| **{row['channel']}** | {row['current_share']} | {row['direction']} — {row['phrase']} |")
        md.append("")
        md.append(f"_Recommended explore ratio next cycle: {report.recommended_explore_ratio * 100:.0f}%._")
        md.append("")
        md.append(f"> {_DISCLAIMER}")
        md.append("")

        md.append("## Learnings to carry forward")
        if carried:
            md.extend(f"{i}. {line}" for i, line in enumerate(carried, 1))
        else:
            md.append("_No new learnings recorded this cycle._")

        return "\n".join(md)


class PlainTextDigestService(_BaseDigestService):
    """Same digest content with no markup - for email, SMS, or log output."""

    def _render(self, *, plan, report, headline, scaled, cut, total_spend, total_outcomes,
                blended_cac, perf_rows, verdict_rows, move_rows, carried) -> str:
        lines: list[str] = []
        title = f"AUGURY WEEKLY DIGEST - CYCLE {plan.cycle_id}"
        lines.append(title)
        lines.append("=" * len(title))
        lines.append(headline)
        if scaled:
            lines.append(f"Scaling: {', '.join(scaled)}")
        if cut:
            lines.append(f"Cutting: {', '.join(cut)}")
        lines.append("")

        lines.append("EXECUTIVE SUMMARY")
        lines.append(report.executive_summary or "No summary provided.")
        if report.primary_bottleneck:
            lines.append(f"Primary bottleneck: {report.primary_bottleneck}")
        lines.append("")

        lines.append("WHAT HAPPENED THIS CYCLE")
        for row in perf_rows:
            lines.append(f"- {row['channel']}  (share {row['share']})")
            lines.append(
                f"    spend {row['spend']} · {row['outcomes']} outcomes · "
                f"{row['cac']} · window {row['window']}"
            )
            if row["attribution"]:
                lines.append(f"    attribution: {row['attribution']}")
        lines.append("")

        lines.append("VERDICTS & WHY")
        for row in verdict_rows:
            conf = f" ({row['confidence']})" if row["confidence"] else ""
            lines.append(f"- {row['channel']}: {row['verdict']}{conf}")
            lines.append(f"    {row['why']}")
            if row["learning"]:
                lines.append(f"    learning: {row['learning']}")
        lines.append("")

        lines.append("PROPOSED MOVEMENT FOR THE NEXT CYCLE")
        for row in move_rows:
            lines.append(f"- {row['channel']} (now {row['current_share']}): {row['direction']} - {row['phrase']}")
        lines.append(f"Recommended explore ratio next cycle: {report.recommended_explore_ratio * 100:.0f}%")
        lines.append(_DISCLAIMER)
        lines.append("")

        lines.append("LEARNINGS TO CARRY FORWARD")
        if carried:
            lines.extend(f"{i}. {line}" for i, line in enumerate(carried, 1))
        else:
            lines.append("No new learnings recorded this cycle.")

        return "\n".join(lines)


def get_digest_service(fmt: str = "markdown") -> DigestService:
    """Return a digest renderer: ``"markdown"`` (default) or ``"text"`` / ``"plain"``."""
    if fmt.lower() in ("text", "plain", "plaintext"):
        return PlainTextDigestService()
    return MarkdownDigestService()
