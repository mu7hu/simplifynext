"""Profiler service interface and mock for startup profiles and benchmark priors."""

from abc import ABC, abstractmethod
from typing import Optional
from traction.schemas.profile import StartupProfile, BenchmarkPrior, StartupStage, IndustrySector
from traction.schemas.experiment import Channel


class ProfilerService(ABC):
    """Abstract interface for profiling startups and retrieving benchmark priors."""

    @abstractmethod
    def get_startup_profile(self, startup_id: str) -> StartupProfile:
        pass

    @abstractmethod
    def get_benchmark_priors(self, startup_id: str) -> list[BenchmarkPrior]:
        pass


class MockProfilerService(ProfilerService):
    """Functional stub providing realistic B2B SaaS Seed benchmarks."""

    def get_startup_profile(self, startup_id: str) -> StartupProfile:
        return StartupProfile(
            startup_id=startup_id,
            startup_name="LedgerAI",
            stage=StartupStage.SEED,
            sector=IndustrySector.B2B_SAAS,
            target_acv=18000.0,
            sales_cycle_days=45,
            primary_outcome_metric="Qualified Demo Bookings"
        )

    def get_benchmark_priors(self, startup_id: str) -> list[BenchmarkPrior]:
        return [
            BenchmarkPrior(
                channel=Channel.GOOGLE_SEARCH.value,
                median_cac=320.0,
                min_cac=220.0,
                max_cac=550.0,
                avg_cpc=11.50,
                avg_conversion_rate=0.04,
                min_evaluation_days=14,
                rationale="High buyer intent for B2B financial software categories"
            ),
            BenchmarkPrior(
                channel=Channel.LINKEDIN.value,
                median_cac=580.0,
                min_cac=350.0,
                max_cac=1100.0,
                avg_cpc=16.00,
                avg_conversion_rate=0.02,
                min_evaluation_days=30,
                rationale="Long consideration cycle; enterprise titles have high CPC"
            ),
            BenchmarkPrior(
                channel=Channel.META.value,
                median_cac=750.0,
                min_cac=450.0,
                max_cac=1500.0,
                avg_cpc=3.20,
                avg_conversion_rate=0.005,
                min_evaluation_days=14,
                rationale="Low immediate intent for B2B; high bounce rate on demo bookings"
            ),
            BenchmarkPrior(
                channel=Channel.COLD_EMAIL.value,
                median_cac=400.0,
                min_cac=250.0,
                max_cac=700.0,
                avg_cpc=2.00,
                avg_conversion_rate=0.015,
                min_evaluation_days=14,
                rationale="Cost effective for niche CFO list; risk of domain burn if scaled"
            ),
            BenchmarkPrior(
                channel=Channel.FOUNDER_CONTENT.value,
                median_cac=650.0,
                min_cac=300.0,
                max_cac=1800.0,
                avg_cpc=7.50,
                avg_conversion_rate=0.003,
                min_evaluation_days=30,
                rationale="High long-term brand equity, but slow and expensive for direct short-term demo capture"
            ),
        ]
