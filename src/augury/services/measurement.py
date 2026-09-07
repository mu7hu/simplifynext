"""Measurement normalization: raw channel telemetry -> comparable ExperimentResults.

``DefaultMeasurementService`` is the production normalizer. It is deterministic
(pure arithmetic, no clocks, no RNG), maps every supported channel's telemetry
onto the single :class:`ExperimentResult` schema, and attaches explicit
data-quality and attribution signals under ``raw_metrics`` (the schema itself is
a frozen cross-team contract and must not grow new columns).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from augury.schemas.experiment import Channel, Allocation, ExperimentPlan
from augury.schemas.result import RawExecutionResult, ExperimentResult
from augury.schemas.profile import BenchmarkPrior

_DEFAULT_TARGET_CAC = 400.0
_DEFAULT_WINDOW_DAYS = 14

_STOPWORDS = {
    "the", "and", "for", "with", "who", "that", "this", "are", "was", "have", "has",
    "companies", "company", "employees", "size", "past", "core", "high", "low", "mid",
    "market", "targeting", "target", "audience", "segment", "people", "users", "team",
    "teams", "at", "in", "of", "to", "a", "an", "on", "or",
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _significant_tokens(text: str) -> set[str]:
    out: set[str] = set()
    for chunk in str(text or "").lower().replace("/", " ").replace("-", " ").split():
        word = "".join(c for c in chunk if c.isalnum())
        if len(word) > 3 and word not in _STOPWORDS:
            out.add(word)
    return out


def _audience_overlap(allocations: Iterable[Allocation]) -> dict[Channel, list[Channel]]:
    """Channels whose audience text meaningfully overlaps another channel's this cycle."""
    allocs = list(allocations)
    tokens = {a.channel: _significant_tokens(a.audience) for a in allocs}
    overlaps: dict[Channel, list[Channel]] = {a.channel: [] for a in allocs}
    for i, a in enumerate(allocs):
        for b in allocs[i + 1:]:
            if len(tokens[a.channel] & tokens[b.channel]) >= 2:
                overlaps[a.channel].append(b.channel)
                overlaps[b.channel].append(a.channel)
    return {ch: others for ch, others in overlaps.items() if others}


def _priors_by_channel(priors: Iterable[BenchmarkPrior]) -> dict[Channel, BenchmarkPrior]:
    out: dict[Channel, BenchmarkPrior] = {}
    for p in priors:
        try:
            out[Channel(p.channel)] = p
        except ValueError:
            continue
    return out


class MeasurementService(ABC):
    """Abstract interface for normalizing raw telemetry into comparable ExperimentResults."""

    @abstractmethod
    def normalize_results(
        self,
        raw_results: list[RawExecutionResult],
        plan: ExperimentPlan,
        benchmark_priors: list[BenchmarkPrior]
    ) -> list[ExperimentResult]:
        pass


class DefaultMeasurementService(MeasurementService):
    """Standard measurement normalizer.

    Calculates observed CAC, conversion rate, CTR and evaluation-window state, and
    records quality / attribution context in ``raw_metrics``:

    * ``data_quality`` - ``high`` / ``medium`` / ``low`` from outcome volume + window state
    * ``window_progress`` / ``days_remaining`` - evaluation-window completion detail
    * ``response_delay_suspected`` - pipeline building (leads) but conversions not yet in
    * ``attribution_risk`` / ``attribution_warning`` - overlapping audiences this cycle
    * ``benchmark_cac_median`` / ``benchmark_cac_ratio`` - observed CAC vs industry prior
    """

    def normalize_results(
        self,
        raw_results: list[RawExecutionResult],
        plan: ExperimentPlan,
        benchmark_priors: list[BenchmarkPrior]
    ) -> list[ExperimentResult]:
        alloc_by_ch: dict[Channel, Allocation] = {a.channel: a for a in plan.allocations}
        prior_by_ch = _priors_by_channel(benchmark_priors)
        overlaps = _audience_overlap(plan.allocations)

        normalized: list[ExperimentResult] = []
        for r in raw_results:
            alloc = alloc_by_ch.get(r.channel)
            prior = prior_by_ch.get(r.channel)
            normalized.append(
                self._normalize_one(r, alloc, prior, overlaps.get(r.channel, []))
            )
        return normalized

    # ------------------------------------------------------------------ internal

    def _normalize_one(
        self,
        r: RawExecutionResult,
        alloc: Optional[Allocation],
        prior: Optional[BenchmarkPrior],
        overlap_with: list[Channel],
    ) -> ExperimentResult:
        target_cac = self._target_cac(alloc, prior)
        eval_window = self._eval_window(alloc, prior)

        spend = round(float(r.spend), 2)
        outcomes = int(r.primary_outcomes)
        clicks = int(r.clicks)
        impressions = int(r.impressions)
        leads = int(r.leads)
        days_observed = max(1, int(r.days_active))

        if outcomes > 0:
            observed_cac = round(spend / outcomes, 2)
        else:
            observed_cac = spend if spend > 0 else 0.0

        conversion_rate = _clamp(round(outcomes / clicks, 4)) if clicks > 0 else 0.0
        ctr = _clamp(round(clicks / impressions, 4)) if impressions > 0 else 0.0
        is_window_complete = days_observed >= eval_window
        cost_efficiency_ratio = round(target_cac / observed_cac, 2) if observed_cac > 0 else 0.0

        raw_metrics = self._quality_block(
            r=r,
            alloc=alloc,
            prior=prior,
            overlap_with=overlap_with,
            spend=spend,
            outcomes=outcomes,
            clicks=clicks,
            leads=leads,
            impressions=impressions,
            observed_cac=observed_cac,
            target_cac=target_cac,
            eval_window=eval_window,
            days_observed=days_observed,
            is_window_complete=is_window_complete,
        )

        return ExperimentResult(
            channel=r.channel,
            experiment_id=r.experiment_id,
            spend=spend,
            primary_outcomes=outcomes,
            observed_cac=observed_cac,
            conversion_rate=conversion_rate,
            click_through_rate=ctr,
            days_observed=days_observed,
            evaluation_window_days=eval_window,
            is_window_complete=is_window_complete,
            cost_efficiency_ratio=cost_efficiency_ratio,
            raw_metrics=raw_metrics,
        )

    @staticmethod
    def _target_cac(alloc: Optional[Allocation], prior: Optional[BenchmarkPrior]) -> float:
        if alloc is not None and alloc.success_threshold and alloc.success_threshold > 0:
            return float(alloc.success_threshold)
        if prior is not None and prior.median_cac > 0:
            return float(prior.median_cac)
        return _DEFAULT_TARGET_CAC

    @staticmethod
    def _eval_window(alloc: Optional[Allocation], prior: Optional[BenchmarkPrior]) -> int:
        if alloc is not None and alloc.evaluation_window_days > 0:
            return int(alloc.evaluation_window_days)
        if prior is not None and prior.min_evaluation_days > 0:
            return int(prior.min_evaluation_days)
        return _DEFAULT_WINDOW_DAYS

    @staticmethod
    def _quality_block(
        *,
        r: RawExecutionResult,
        alloc: Optional[Allocation],
        prior: Optional[BenchmarkPrior],
        overlap_with: list[Channel],
        spend: float,
        outcomes: int,
        clicks: int,
        leads: int,
        impressions: int,
        observed_cac: float,
        target_cac: float,
        eval_window: int,
        days_observed: int,
        is_window_complete: bool,
    ) -> dict[str, Any]:
        telemetry_delay = float(r.raw_telemetry.get("delay_damping", 1.0)) if isinstance(r.raw_telemetry, dict) else 1.0
        response_delay_suspected = telemetry_delay < 1.0 or (
            not is_window_complete and outcomes == 0 and leads > 0
        )

        if outcomes >= 5 and is_window_complete:
            data_quality = "high"
        elif outcomes == 0 or not is_window_complete:
            data_quality = "low"
        else:
            data_quality = "medium"

        if outcomes == 0:
            vs_target = "no_outcomes"
        elif observed_cac < target_cac * 0.98:
            vs_target = "under"
        elif observed_cac > target_cac * 1.02:
            vs_target = "over"
        else:
            vs_target = "at"

        attribution_risk = bool(overlap_with)
        attribution_warning = None
        if attribution_risk:
            names = ", ".join(c.value for c in overlap_with)
            attribution_warning = (
                f"Audience overlaps with {names} this cycle; observed CAC for "
                f"{r.channel.value} may be distorted by multi-touch attribution."
            )

        block: dict[str, Any] = {
            "impressions": impressions,
            "clicks": clicks,
            "leads": leads,
            "target_cac": round(target_cac, 2),
            "evaluation_window_days": eval_window,
            "days_observed": days_observed,
            "window_progress": round(min(1.0, days_observed / eval_window), 3) if eval_window else 1.0,
            "days_remaining": max(0, eval_window - days_observed),
            "cost_per_click_observed": round(spend / clicks, 2) if clicks > 0 else None,
            "cost_per_lead_observed": round(spend / leads, 2) if leads > 0 else None,
            "sample_size": outcomes,
            "data_quality": data_quality,
            "vs_target": vs_target,
            "response_delay_suspected": response_delay_suspected,
            "attribution_risk": attribution_risk,
            "attribution_warning": attribution_warning,
            "benchmark_cac_median": round(prior.median_cac, 2) if prior is not None else None,
            "benchmark_cac_ratio": (
                round(observed_cac / prior.median_cac, 2)
                if prior is not None and prior.median_cac > 0 and observed_cac > 0
                else None
            ),
            "is_exploration": bool(alloc.is_exploration) if alloc is not None else None,
        }
        # Preserve upstream adapter/simulator telemetry without letting it collide
        # with the normalized keys above.
        if isinstance(r.raw_telemetry, dict):
            for k, v in r.raw_telemetry.items():
                block.setdefault(f"telemetry_{k}", v)
        return block
