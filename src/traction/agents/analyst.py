"""Analyst Agent: Evaluates normalized results and issues structured verdicts.

Three concrete implementations share one infra-agnostic ABC:

* ``StubAnalystAgent``    - deterministic scripted narrative for fast offline demos/tests.
* ``LLMAnalystAgent``     - thin single-shot Bedrock call (legacy, kept for compatibility).
* ``BedrockAnalystAgent`` - production agent: Amazon Bedrock reasoning with a
  deterministic rule-engine fallback and mandatory safety post-processing
  (evaluation-window protection, verdict/field validation, attribution warnings).

``get_analyst_agent()`` picks ``BedrockAnalystAgent`` when AWS credentials resolve
and ``StubAnalystAgent`` otherwise, so the graph, the standalone Lambda handler
(``traction.api.analyst_lambda``) and the CLI (``scripts/run_analyst.py``) all get
the right agent without any of them knowing about the others.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from traction.config import settings
from traction.logging import logger
from traction.models import ModelFactory, get_analyst_model, get_analyst_structured_model
from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import ExperimentResult
from traction.schemas.profile import BenchmarkPrior
from traction.schemas.analysis import AnalysisReport, ExperimentVerdict, Verdict
from traction.agents.prompts import ANALYST_SYSTEM_PROMPT, ANALYST_HUMAN_PREAMBLE

_VALID_DIRECTIONS = {"INCREASE", "MAINTAIN", "DECREASE", "PAUSE"}
_DIRECTION_SYNONYMS = {
    "INCREASE": "INCREASE", "SCALE": "INCREASE", "UP": "INCREASE", "GROW": "INCREASE",
    "MAINTAIN": "MAINTAIN", "HOLD": "MAINTAIN", "KEEP": "MAINTAIN", "STEADY": "MAINTAIN",
    "DECREASE": "DECREASE", "REDUCE": "DECREASE", "CUT": "DECREASE", "DOWN": "DECREASE",
    "PAUSE": "PAUSE", "STOP": "PAUSE", "KILL": "PAUSE", "OFF": "PAUSE",
}
_STOPWORDS = {
    "the", "and", "for", "with", "who", "that", "this", "are", "was", "have", "has",
    "companies", "company", "employees", "size", "past", "core", "high", "low", "mid",
    "market", "targeting", "target", "audience", "segment", "people", "users", "team",
    "teams", "at", "in", "of", "to", "a", "an", "on", "or",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _normalize_direction(raw: Any) -> str:
    token = str(raw or "").strip().upper()
    if token in _VALID_DIRECTIONS:
        return token
    if token in _DIRECTION_SYNONYMS:
        return _DIRECTION_SYNONYMS[token]
    for word in token.replace("-", " ").replace("_", " ").split():
        if word in _VALID_DIRECTIONS:
            return word
        if word in _DIRECTION_SYNONYMS:
            return _DIRECTION_SYNONYMS[word]
    return "MAINTAIN"


def _significant_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for chunk in str(text or "").lower().replace("/", " ").replace("-", " ").split():
        word = "".join(c for c in chunk if c.isalnum())
        if len(word) > 3 and word not in _STOPWORDS:
            out.add(word)
    return out


def _audience_overlap(allocations: Iterable[Allocation]) -> dict[Channel, list[Channel]]:
    """Map each channel to the other channels whose audience meaningfully overlaps it."""
    allocs = list(allocations)
    tokens = {a.channel: _significant_tokens(a.audience) for a in allocs}
    overlaps: dict[Channel, list[Channel]] = {a.channel: [] for a in allocs}
    for i, a in enumerate(allocs):
        for b in allocs[i + 1:]:
            shared = tokens[a.channel] & tokens[b.channel]
            if len(shared) >= 2:
                overlaps[a.channel].append(b.channel)
                overlaps[b.channel].append(a.channel)
    return {ch: others for ch, others in overlaps.items() if others}


class AnalystAgent(ABC):
    """Abstract interface for the Analyst Agent (Teammate's primary ownership area)."""

    @abstractmethod
    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        pass


class StubAnalystAgent(AnalystAgent):
    """High-fidelity working stub for the Analyst Agent so the system runs end-to-end immediately."""

    def __init__(self, model=None):
        self.model = model or get_analyst_model()
        self.structured_model = self.model.with_structured_output(AnalysisReport)

    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        # Pass state to model or stub to generate structured report
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=f"Analyze cycle {cycle_id} results across channels.")
        ]
        logger.info(f"Analyst evaluating cycle {cycle_id}", extra={"cycle_id": cycle_id, "agent": "analyst"})
        report = self.structured_model.invoke(messages)
        return report


class LLMAnalystAgent(AnalystAgent):
    """Full LLM Analyst Agent invoking Claude Sonnet / Haiku via AWS Bedrock."""

    def __init__(self, model=None):
        self.model = model or get_analyst_model()
        self.structured_model = self.model.with_structured_output(AnalysisReport)

    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        lines = [
            f"# Performance Data for Cycle {cycle_id}",
            "## Normalized Channel Results:"
        ]
        for r in results:
            lines.append(
                f"- Channel: {r.channel.value} | Spend: ${r.spend:.2f} | Outcomes: {r.primary_outcomes} | "
                f"CAC: ${r.observed_cac:.2f} | Days Observed: {r.days_observed}/{r.evaluation_window_days} "
                f"(Window Complete: {r.is_window_complete})"
            )

        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content="\n".join(lines))
        ]
        logger.info(f"LLM Analyst evaluating cycle {cycle_id}", extra={"cycle_id": cycle_id, "agent": "analyst"})
        return self.structured_model.invoke(messages)


class BedrockAnalystAgent(AnalystAgent):
    """Production Analyst Agent.

    Reasoning runs on Amazon Bedrock (cheap model by default, see
    ``settings.bedrock_analyst_model``). Every report - whether produced by the
    LLM or by the deterministic fallback - is run through
    :meth:`_postprocess_report`, which enforces the non-negotiable safety rules:
    incomplete evaluation windows are never CUT, benchmark priors backstop sparse
    CAC comparisons, every channel gets exactly one verdict, and the result is a
    re-validated :class:`AnalysisReport` (never a raw dict).

    The class holds no long-lived mutable state and no in-memory caches, so it is
    safe to construct per invocation / per Lambda cold start.
    """

    def __init__(self, structured_model: Any = None, *, force_deterministic: bool = False):
        if force_deterministic:
            self._structured_model = None
        elif structured_model is not None:
            self._structured_model = structured_model
        elif not settings.use_stub_models:
            self._structured_model = get_analyst_structured_model(AnalysisReport)
        elif ModelFactory.bedrock_credentials_available():
            try:
                self._structured_model = get_analyst_structured_model(AnalysisReport)
            except Exception as exc:  # pragma: no cover - depends on ambient AWS env
                logger.warning(
                    f"Could not build Bedrock analyst model ({exc}); deterministic engine only",
                    extra={"agent": "analyst"},
                )
                self._structured_model = None
        else:
            self._structured_model = None

    # ------------------------------------------------------------------ public

    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        report: Optional[AnalysisReport] = None
        source = "deterministic"

        if self._structured_model is not None:
            try:
                messages = [
                    SystemMessage(content=ANALYST_SYSTEM_PROMPT),
                    HumanMessage(content=self._build_prompt(cycle_id, plan, results, benchmark_priors)),
                ]
                raw = self._structured_model.invoke(messages)
                report = raw if isinstance(raw, AnalysisReport) else AnalysisReport.model_validate(raw)
                if not settings.use_stub_models and {v.channel for v in report.verdicts} != {a.channel for a in plan.allocations}:
                    raise ValueError('Bedrock analysis must cover every planned channel exactly')
                source = "bedrock"
            except Exception as exc:
                if not settings.use_stub_models:
                    raise RuntimeError("Bedrock Analyst failed; no fallback was used") from exc
                logger.warning(
                    f"Bedrock analyst call failed ({exc}); falling back to deterministic analysis",
                    extra={"cycle_id": cycle_id, "agent": "analyst"},
                )
                report = None

        if report is None:
            report = self._deterministic_analysis(cycle_id, plan, results, benchmark_priors)

        report = self._postprocess_report(report, cycle_id, plan, results, benchmark_priors)
        logger.info(
            f"Analyst evaluated cycle {cycle_id} ({source})",
            extra={
                "cycle_id": cycle_id,
                "agent": "analyst",
                "verdict": ",".join(f"{v.channel.value}:{v.verdict.value}" for v in report.verdicts),
            },
        )
        return report

    # ------------------------------------------------------------------ prompt

    def _build_prompt(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior],
    ) -> str:
        res_by_ch = {r.channel: r for r in results}
        prior_by_ch = _priors_by_channel(benchmark_priors)
        overlaps = _audience_overlap(plan.allocations)

        lines = [
            ANALYST_HUMAN_PREAMBLE,
            f"\n# Cycle {cycle_id} - primary goal: {plan.primary_goal}",
            f"Total budget deployed: ${plan.total_budget:,.2f}",
            "\n## Channels",
        ]
        for a in plan.allocations:
            r = res_by_ch.get(a.channel)
            p = prior_by_ch.get(a.channel)
            lines.append(f"\n### {a.channel.value}  (experiment {a.experiment_id})")
            lines.append(f"- hypothesis: {a.hypothesis}")
            lines.append(f"- audience: {a.audience}")
            lines.append(
                f"- target CAC (success_threshold): ${a.success_threshold:,.2f} | "
                f"evaluation_window_days: {a.evaluation_window_days} | exploration: {a.is_exploration}"
            )
            if p:
                lines.append(
                    f"- benchmark prior CAC: median ${p.median_cac:,.2f} (min ${p.min_cac:,.2f} / "
                    f"max ${p.max_cac:,.2f}), min_evaluation_days {p.min_evaluation_days}"
                )
            else:
                lines.append("- benchmark prior CAC: (none supplied)")
            if r:
                lines.append(
                    f"- observed: spend ${r.spend:,.2f} | outcomes {r.primary_outcomes} | "
                    f"observed CAC ${r.observed_cac:,.2f} | CTR {r.click_through_rate:.4f} | "
                    f"conversion {r.conversion_rate:.4f}"
                )
                lines.append(
                    f"- window: {r.days_observed}/{r.evaluation_window_days} days "
                    f"(complete={r.is_window_complete})"
                )
            else:
                lines.append("- observed: NO RESULTS REPORTED for this channel")
            if a.channel in overlaps:
                names = ", ".join(c.value for c in overlaps[a.channel])
                lines.append(f"- audience overlap this cycle with: {names}")

        lines.append(f"\nReturn a valid AnalysisReport for cycle_id={cycle_id}.")
        return "\n".join(lines)

    # --------------------------------------------------------- deterministic

    def _deterministic_analysis(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior],
    ) -> AnalysisReport:
        res_by_ch = {r.channel: r for r in results}
        alloc_by_ch = {a.channel: a for a in plan.allocations}
        prior_by_ch = _priors_by_channel(benchmark_priors)
        overlaps = _audience_overlap(plan.allocations)

        channels: list[Channel] = [a.channel for a in plan.allocations] or list(res_by_ch.keys())
        verdicts: list[ExperimentVerdict] = []
        for ch in channels:
            verdicts.append(
                self._verdict_for_channel(
                    channel=ch,
                    alloc=alloc_by_ch.get(ch),
                    result=res_by_ch.get(ch),
                    prior=prior_by_ch.get(ch),
                    overlap_with=overlaps.get(ch, []),
                )
            )

        counts = {v: 0 for v in Verdict}
        for v in verdicts:
            counts[v.verdict] += 1
        summary = (
            f"Cycle {cycle_id}: {counts[Verdict.SCALE]} SCALE, {counts[Verdict.HOLD]} HOLD, "
            f"{counts[Verdict.CUT]} CUT, {counts[Verdict.INSUFFICIENT_DATA]} INSUFFICIENT_DATA "
            f"across {len(verdicts)} channels."
        )

        bottleneck = self._diagnose_bottleneck(verdicts, res_by_ch)
        explore_ratio = _clamp(
            round(settings.default_explore_pct - 0.05 * counts[Verdict.CUT], 2),
            settings.min_explore_pct,
            0.4,
        )

        return AnalysisReport(
            cycle_id=cycle_id,
            verdicts=verdicts,
            executive_summary=summary,
            primary_bottleneck=bottleneck,
            recommended_explore_ratio=explore_ratio,
        )

    def _verdict_for_channel(
        self,
        channel: Channel,
        alloc: Optional[Allocation],
        result: Optional[ExperimentResult],
        prior: Optional[BenchmarkPrior],
        overlap_with: list[Channel],
    ) -> ExperimentVerdict:
        target = _target_cac(alloc, prior)
        experiment_id = (
            (alloc.experiment_id if alloc else None)
            or (result.experiment_id if result else None)
            or f"EXP-{channel.value}"
        )
        attribution = None
        if overlap_with:
            attribution = (
                "Overlapping audience this cycle with "
                + ", ".join(c.value for c in overlap_with)
                + "; multi-touch attribution may distort this channel's observed CAC."
            )

        if result is None:
            return ExperimentVerdict(
                channel=channel,
                experiment_id=experiment_id,
                verdict=Verdict.INSUFFICIENT_DATA,
                confidence=0.1,
                observed_cost_per_outcome=0.0,
                target_cost_per_outcome=target,
                evidence_count=0,
                evaluation_window_complete=False,
                reasoning_summary="No execution results reported for this channel; nothing to evaluate yet.",
                recommended_budget_direction="MAINTAIN",
                learning=f"{channel.value}: awaiting first execution data before a verdict can be formed.",
                attribution_warning=attribution,
            )

        observed = float(result.observed_cac)
        evidence = int(result.primary_outcomes)
        window_complete = bool(result.is_window_complete)
        material_spend = result.spend >= 100.0
        root_cause = _root_cause(result)

        # Sparse-evidence CAC comparison leans on the benchmark prior.
        effective_target = target
        if evidence <= 1 and prior is not None:
            effective_target = (target + prior.median_cac) / 2.0
        ceiling = prior.max_cac if prior is not None else effective_target * 2.0

        # --- Rule 1: incomplete evaluation window is protected from CUT. ---
        if not window_complete:
            if evidence >= 2 and observed <= effective_target:
                verdict, direction, conf = Verdict.HOLD, "MAINTAIN", 0.45
                reasoning = (
                    f"Early CAC ${observed:,.2f} is under target ${effective_target:,.2f}, but the "
                    f"{result.days_observed}/{result.evaluation_window_days}-day window is not complete - "
                    f"holding rather than scaling on partial data."
                )
            else:
                verdict, direction, conf = Verdict.INSUFFICIENT_DATA, "MAINTAIN", 0.25
                reasoning = (
                    f"Evaluation window incomplete ({result.days_observed}/{result.evaluation_window_days} days) "
                    f"with only {evidence} outcome(s); protected from a premature CUT. {root_cause}".strip()
                )
            return ExperimentVerdict(
                channel=channel,
                experiment_id=experiment_id,
                verdict=verdict,
                confidence=_clamp(conf),
                observed_cost_per_outcome=max(0.0, observed),
                target_cost_per_outcome=target,
                evidence_count=evidence,
                evaluation_window_complete=False,
                reasoning_summary=reasoning,
                recommended_budget_direction=direction,
                learning=(
                    f"{channel.value}: needs the full {result.evaluation_window_days}-day window before "
                    f"its ${observed:,.2f} CAC can be trusted."
                ),
                attribution_warning=attribution,
            )

        # --- Window complete from here on. ---
        if evidence == 0:
            if material_spend:
                verdict, direction, conf = Verdict.CUT, "PAUSE", 0.82
                reasoning = (
                    f"Full {result.evaluation_window_days}-day window elapsed with ${result.spend:,.2f} spent "
                    f"and zero qualified outcomes - structural conversion failure. {root_cause}".strip()
                )
                learning = f"{channel.value} produced no outcomes at meaningful spend; not viable for this goal as configured."
            else:
                verdict, direction, conf = Verdict.INSUFFICIENT_DATA, "DECREASE", 0.3
                reasoning = (
                    f"Window complete but only ${result.spend:,.2f} spent and no outcomes - too little signal "
                    f"to conclude. {root_cause}".strip()
                )
                learning = f"{channel.value}: underfunded test yielded no signal; either fund it properly or drop it."
        elif observed <= effective_target:
            if evidence >= 2:
                verdict, direction = Verdict.SCALE, "INCREASE"
                conf = _clamp(0.55 + 0.1 * evidence, high=0.9)
                reasoning = (
                    f"Observed CAC ${observed:,.2f} beats target ${effective_target:,.2f} across {evidence} "
                    f"outcomes with a complete window."
                )
                learning = f"{channel.value} converts qualified outcomes below target CAC; primary channel to scale."
            else:
                verdict, direction, conf = Verdict.HOLD, "MAINTAIN", 0.5
                reasoning = (
                    f"Observed CAC ${observed:,.2f} is under target ${effective_target:,.2f} but rests on a single "
                    f"outcome; hold and gather more evidence before scaling."
                )
                learning = f"{channel.value} shows an efficient first outcome; promising but not yet proven."
        elif observed <= effective_target * 1.25:
            verdict, direction, conf = Verdict.HOLD, "MAINTAIN", 0.55
            reasoning = (
                f"Observed CAC ${observed:,.2f} is modestly above target ${effective_target:,.2f} "
                f"({evidence} outcomes); borderline - hold and optimise. {root_cause}".strip()
            )
            learning = f"{channel.value} is near target CAC; worth another cycle of creative/landing-page iteration."
        else:
            over_ceiling = observed > ceiling
            if observed > effective_target * 1.5 or over_ceiling:
                verdict, direction = Verdict.CUT, "DECREASE"
                conf = _clamp(0.6 + (0.15 if over_ceiling else 0.0) + 0.03 * evidence, high=0.9)
                reasoning = (
                    f"Observed CAC ${observed:,.2f} exceeds target ${effective_target:,.2f} by "
                    f"{observed / max(1.0, effective_target):.1f}x"
                    + (f" and is above the benchmark ceiling ${ceiling:,.2f}" if over_ceiling else "")
                    + f" with a complete window. {root_cause}"
                ).strip()
                learning = f"{channel.value} runs well over target CAC even with the window complete; reallocate away."
            else:
                verdict, direction, conf = Verdict.HOLD, "DECREASE", 0.5
                reasoning = (
                    f"Observed CAC ${observed:,.2f} is above target ${effective_target:,.2f} but not yet "
                    f"decisively - trim budget rather than cut outright. {root_cause}".strip()
                )
                learning = f"{channel.value} is trending expensive; reduce exposure while confirming the trend."

        return ExperimentVerdict(
            channel=channel,
            experiment_id=experiment_id,
            verdict=verdict,
            confidence=_clamp(conf),
            observed_cost_per_outcome=max(0.0, observed),
            target_cost_per_outcome=target,
            evidence_count=evidence,
            evaluation_window_complete=True,
            reasoning_summary=reasoning,
            recommended_budget_direction=direction,
            learning=learning,
            attribution_warning=attribution,
        )

    @staticmethod
    def _diagnose_bottleneck(
        verdicts: list[ExperimentVerdict],
        res_by_ch: dict[Channel, ExperimentResult],
    ) -> Optional[str]:
        creative, landing = [], []
        for v in verdicts:
            r = res_by_ch.get(v.channel)
            if not r or r.primary_outcomes > 0:
                continue
            if r.click_through_rate and r.click_through_rate < 0.01:
                creative.append(v.channel.value)
            elif r.click_through_rate and r.click_through_rate >= 0.01 and r.conversion_rate < 0.01:
                landing.append(v.channel.value)
        if landing:
            return f"Downstream conversion (landing page / offer) on: {', '.join(landing)}."
        if creative:
            return f"Creative / messaging (low click-through) on: {', '.join(creative)}."
        return None

    # ----------------------------------------------------------- validation

    def _postprocess_report(
        self,
        report: AnalysisReport,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior],
    ) -> AnalysisReport:
        """Enforce the non-negotiable safety rules on any report, LLM or deterministic."""
        res_by_ch = {r.channel: r for r in results}
        alloc_by_ch = {a.channel: a for a in plan.allocations}
        prior_by_ch = _priors_by_channel(benchmark_priors)
        overlaps = _audience_overlap(plan.allocations)

        seen: set[Channel] = set()
        clean: list[ExperimentVerdict] = []
        for v in report.verdicts:
            if v.channel in seen:
                continue  # drop duplicate verdicts for the same channel
            seen.add(v.channel)
            r = res_by_ch.get(v.channel)
            alloc = alloc_by_ch.get(v.channel)

            direction = _normalize_direction(v.recommended_budget_direction)
            confidence = round(_clamp(float(v.confidence)), 3)
            verdict = v.verdict
            reasoning = v.reasoning_summary
            window_complete = v.evaluation_window_complete
            evidence = int(v.evidence_count)
            observed = max(0.0, float(v.observed_cost_per_outcome))
            target = v.target_cost_per_outcome if v.target_cost_per_outcome and v.target_cost_per_outcome > 0 else _target_cac(alloc, prior_by_ch.get(v.channel))

            if r is not None:
                window_complete = bool(r.is_window_complete)
                evidence = int(r.primary_outcomes)
                observed = float(r.observed_cac)
                target = _target_cac(alloc, prior_by_ch.get(v.channel))
                # Rule: never CUT a channel whose evaluation window is incomplete.
                if not r.is_window_complete and verdict == Verdict.CUT:
                    verdict = Verdict.INSUFFICIENT_DATA
                    direction = "MAINTAIN"
                    confidence = min(confidence, 0.4)
                    reasoning = (
                        f"[WINDOW GUARD] Evaluation window incomplete "
                        f"({r.days_observed}/{r.evaluation_window_days} days); downgraded from CUT to "
                        f"INSUFFICIENT_DATA. Original rationale: {reasoning}"
                    )

            attribution = v.attribution_warning
            if attribution is None and v.channel in overlaps:
                attribution = (
                    "Overlapping audience this cycle with "
                    + ", ".join(c.value for c in overlaps[v.channel])
                    + "; multi-touch attribution may distort this channel's observed CAC."
                )

            clean.append(
                ExperimentVerdict(
                    channel=v.channel,
                    experiment_id=v.experiment_id or (alloc.experiment_id if alloc else f"EXP-{v.channel.value}"),
                    verdict=verdict,
                    confidence=confidence,
                    observed_cost_per_outcome=observed,
                    target_cost_per_outcome=target,
                    evidence_count=evidence,
                    evaluation_window_complete=window_complete,
                    reasoning_summary=reasoning,
                    recommended_budget_direction=direction,
                    learning=v.learning,
                    attribution_warning=attribution,
                )
            )

        # Coverage: every planned channel must have exactly one verdict.
        for a in plan.allocations:
            if a.channel not in seen:
                clean.append(
                    self._verdict_for_channel(
                        channel=a.channel,
                        alloc=a,
                        result=res_by_ch.get(a.channel),
                        prior=prior_by_ch.get(a.channel),
                        overlap_with=overlaps.get(a.channel, []),
                    )
                )

        rebuilt = AnalysisReport(
            cycle_id=cycle_id,
            verdicts=clean,
            executive_summary=report.executive_summary or f"Cycle {cycle_id} analysis.",
            primary_bottleneck=report.primary_bottleneck,
            recommended_explore_ratio=round(
                _clamp(float(report.recommended_explore_ratio), settings.min_explore_pct, 0.5), 3
            ),
        )
        # Final guarantee: return a re-validated object, never a raw dict.
        return AnalysisReport.model_validate(rebuilt.model_dump())


def _priors_by_channel(benchmark_priors: Iterable[BenchmarkPrior]) -> dict[Channel, BenchmarkPrior]:
    out: dict[Channel, BenchmarkPrior] = {}
    for p in benchmark_priors:
        try:
            out[Channel(p.channel)] = p
        except ValueError:
            continue
    return out


def _target_cac(alloc: Optional[Allocation], prior: Optional[BenchmarkPrior]) -> float:
    if alloc is not None and alloc.success_threshold and alloc.success_threshold > 0:
        return float(alloc.success_threshold)
    if prior is not None and prior.median_cac > 0:
        return float(prior.median_cac)
    return 400.0  # schema requires target_cost_per_outcome > 0


def _root_cause(result: ExperimentResult) -> str:
    ctr = result.click_through_rate
    conv = result.conversion_rate
    if ctr and ctr < 0.01:
        return f"Low click-through ({ctr * 100:.2f}%) points to a creative/message problem."
    if ctr and ctr >= 0.01 and conv is not None and conv < 0.01:
        return f"Clicks land but conversion ({conv * 100:.2f}%) is weak - likely a landing-page/offer problem."
    return ""


def get_analyst_agent() -> AnalystAgent:
    """Return the right Analyst implementation for the current environment.

    ``BedrockAnalystAgent`` when AWS credentials resolve (real serverless
    reasoning with deterministic safeguards); ``StubAnalystAgent`` otherwise, so
    offline demos and tests stay fast and fully deterministic.
    """
    if not settings.use_stub_models:
        return BedrockAnalystAgent()
    return StubAnalystAgent()
