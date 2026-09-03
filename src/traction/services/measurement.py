"""Measurement normalization interface and standard service."""

from abc import ABC, abstractmethod
from typing import Optional
from traction.schemas.experiment import ExperimentPlan
from traction.schemas.result import RawExecutionResult, ExperimentResult
from traction.schemas.profile import BenchmarkPrior


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
    """Standard measurement normalizer calculating observed CAC, conversion rates, and window state."""

    def normalize_results(
        self,
        raw_results: list[RawExecutionResult],
        plan: ExperimentPlan,
        benchmark_priors: list[BenchmarkPrior]
    ) -> list[ExperimentResult]:
        allocations_by_channel = {a.channel: a for a in plan.allocations}
        priors_by_channel = {p.channel: p for p in benchmark_priors}

        normalized = []
        for r in raw_results:
            alloc = allocations_by_channel.get(r.channel)
            target_cac = alloc.success_threshold if alloc else 400.0
            eval_window = alloc.evaluation_window_days if alloc else 14

            if r.primary_outcomes > 0:
                observed_cac = round(r.spend / r.primary_outcomes, 2)
            else:
                observed_cac = round(r.spend, 2) if r.spend > 0 else 0.0

            conversion_rate = round(r.primary_outcomes / max(1, r.clicks), 4) if r.clicks > 0 else 0.0
            ctr = round(r.clicks / max(1, r.impressions), 4) if r.impressions > 0 else 0.0

            # Window is complete if days active meets or exceeds evaluation window
            is_complete = r.days_active >= eval_window

            efficiency = round(target_cac / max(1.0, observed_cac), 2) if observed_cac > 0 else 0.0

            normalized.append(ExperimentResult(
                channel=r.channel,
                experiment_id=r.experiment_id,
                spend=r.spend,
                primary_outcomes=r.primary_outcomes,
                observed_cac=observed_cac,
                conversion_rate=conversion_rate,
                click_through_rate=ctr,
                days_observed=r.days_active,
                evaluation_window_days=eval_window,
                is_window_complete=is_complete,
                cost_efficiency_ratio=efficiency,
                raw_metrics=r.raw_telemetry
            ))

        return normalized
