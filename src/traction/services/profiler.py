"""Startup profiling and industry benchmark priors.

* ``MockProfilerService``  - unchanged hard-coded LedgerAI profile + priors.
* ``FileProfilerService``  - production default: reads ``data/example_profiles/<startup_id>.json``
  for the profile and ``data/benchmark_priors/<sector>_<stage>.json`` (or a
  ``<startup_id>.json`` override) for priors. Deterministic and traceable - every
  value comes from a named data file or the documented built-in default.
* ``DictProfilerService`` - in-memory mapping for embedding / API / tests.

This module never imports ``traction.simulator`` - profiler output must not carry
hidden ground-truth parameters into normal agent state.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from traction.schemas.profile import StartupProfile, BenchmarkPrior, StartupStage, IndustrySector
from traction.schemas.experiment import Channel

_DEFAULT_PROFILE_DIR = os.path.join("data", "example_profiles")
_DEFAULT_PRIORS_DIR = os.path.join("data", "benchmark_priors")

_STAGE_SLUGS = {
    StartupStage.PRE_SEED: "pre_seed",
    StartupStage.SEED: "seed",
    StartupStage.SERIES_A: "series_a",
}


def _load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _sector_slug(sector: IndustrySector | str) -> str:
    value = sector.value if isinstance(sector, IndustrySector) else str(sector)
    return value.strip().lower()


def _stage_slug(stage: StartupStage | str) -> str:
    if isinstance(stage, StartupStage):
        return _STAGE_SLUGS[stage]
    return str(stage).strip().lower().replace("-", "_").replace(" ", "_")


def priors_key(sector: IndustrySector | str, stage: StartupStage | str) -> str:
    """Traceable filename stem for a sector/stage prior set, e.g. ``b2b_saas_seed``."""
    return f"{_sector_slug(sector)}_{_stage_slug(stage)}"


def _ledger_ai_profile(startup_id: str = "ledger_ai") -> StartupProfile:
    return StartupProfile(
        startup_id=startup_id,
        startup_name="LedgerAI",
        stage=StartupStage.SEED,
        sector=IndustrySector.B2B_SAAS,
        target_acv=18000.0,
        sales_cycle_days=45,
        primary_outcome_metric="Qualified Demo Bookings",
    )


def default_b2b_saas_seed_priors() -> list[BenchmarkPrior]:
    """Documented built-in fallback (matches ``data/benchmark_priors/b2b_saas_seed.json``)."""
    return [
        BenchmarkPrior(channel=Channel.GOOGLE_SEARCH.value, median_cac=320.0, min_cac=220.0, max_cac=550.0,
                       avg_cpc=11.50, avg_conversion_rate=0.04, min_evaluation_days=14,
                       rationale="High buyer intent for B2B financial software categories"),
        BenchmarkPrior(channel=Channel.LINKEDIN.value, median_cac=580.0, min_cac=350.0, max_cac=1100.0,
                       avg_cpc=16.00, avg_conversion_rate=0.02, min_evaluation_days=30,
                       rationale="Long consideration cycle; enterprise titles have high CPC"),
        BenchmarkPrior(channel=Channel.META.value, median_cac=750.0, min_cac=450.0, max_cac=1500.0,
                       avg_cpc=3.20, avg_conversion_rate=0.005, min_evaluation_days=14,
                       rationale="Low immediate intent for B2B; high bounce rate on demo bookings"),
        BenchmarkPrior(channel=Channel.COLD_EMAIL.value, median_cac=400.0, min_cac=250.0, max_cac=700.0,
                       avg_cpc=2.00, avg_conversion_rate=0.015, min_evaluation_days=14,
                       rationale="Cost effective for niche CFO list; risk of domain burn if scaled"),
        BenchmarkPrior(channel=Channel.FOUNDER_CONTENT.value, median_cac=650.0, min_cac=300.0, max_cac=1800.0,
                       avg_cpc=7.50, avg_conversion_rate=0.003, min_evaluation_days=30,
                       rationale="High long-term brand equity, but slow and expensive for direct short-term demo capture"),
    ]


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
        return _ledger_ai_profile(startup_id)

    def get_benchmark_priors(self, startup_id: str) -> list[BenchmarkPrior]:
        return default_b2b_saas_seed_priors()


class DictProfilerService(ProfilerService):
    """In-memory profiler backed by ``{startup_id: ...}`` mappings."""

    def __init__(
        self,
        profiles: dict[str, Any],
        priors: Optional[dict[str, Any]] = None,
        default_profile: Optional[StartupProfile] = None,
        default_priors: Optional[list[BenchmarkPrior]] = None,
    ):
        self._profiles: dict[str, StartupProfile] = {
            sid: v if isinstance(v, StartupProfile) else StartupProfile.model_validate(v)
            for sid, v in profiles.items()
        }
        self._priors: dict[str, list[BenchmarkPrior]] = {}
        for sid, plist in (priors or {}).items():
            self._priors[sid] = [p if isinstance(p, BenchmarkPrior) else BenchmarkPrior.model_validate(p) for p in plist]
        self._default_profile = default_profile
        self._default_priors = default_priors

    def get_startup_profile(self, startup_id: str) -> StartupProfile:
        if startup_id in self._profiles:
            return self._profiles[startup_id]
        if self._default_profile is not None:
            return self._default_profile
        raise KeyError(f"No startup profile registered for startup_id={startup_id!r}")

    def get_benchmark_priors(self, startup_id: str) -> list[BenchmarkPrior]:
        if startup_id in self._priors:
            return list(self._priors[startup_id])
        if self._default_priors is not None:
            return list(self._default_priors)
        return default_b2b_saas_seed_priors()


class FileProfilerService(ProfilerService):
    """Production profiler reading validated JSON from the data directories.

    Profile:  ``<profile_dir>/<startup_id>.json``  -> ``StartupProfile``
    Priors:   ``<priors_dir>/<startup_id>.json``   (per-startup override), else
              ``<priors_dir>/<sector>_<stage>.json``, else
              ``<priors_dir>/<sector>_seed.json``, else the built-in default.
    """

    def __init__(self, profile_dir: str = _DEFAULT_PROFILE_DIR, priors_dir: str = _DEFAULT_PRIORS_DIR):
        self.profile_dir = profile_dir
        self.priors_dir = priors_dir

    @staticmethod
    def _safe(startup_id: str) -> str:
        return "".join(c for c in startup_id if c.isalnum() or c in ("_", "-")).strip() or "default"

    def get_startup_profile(self, startup_id: str) -> StartupProfile:
        path = os.path.join(self.profile_dir, f"{self._safe(startup_id)}.json")
        if os.path.exists(path):
            return StartupProfile.model_validate(_load_json(path))
        if startup_id == "ledger_ai":
            return _ledger_ai_profile(startup_id)
        raise FileNotFoundError(f"No startup profile for startup_id={startup_id!r} at {path}")

    def get_benchmark_priors(self, startup_id: str) -> list[BenchmarkPrior]:
        candidates: list[str] = [os.path.join(self.priors_dir, f"{self._safe(startup_id)}.json")]
        try:
            profile = self.get_startup_profile(startup_id)
            candidates.append(os.path.join(self.priors_dir, f"{priors_key(profile.sector, profile.stage)}.json"))
            candidates.append(os.path.join(self.priors_dir, f"{_sector_slug(profile.sector)}_seed.json"))
        except FileNotFoundError:
            pass

        for path in candidates:
            if os.path.exists(path):
                data = _load_json(path)
                return [BenchmarkPrior.model_validate(p) for p in data]
        return default_b2b_saas_seed_priors()


def get_profiler_service(
    profile_dir: str = _DEFAULT_PROFILE_DIR,
    priors_dir: str = _DEFAULT_PRIORS_DIR,
) -> ProfilerService:
    """File-backed profiler when the data directories exist, else the seeded mock."""
    if os.path.isdir(profile_dir):
        return FileProfilerService(profile_dir, priors_dir)
    return MockProfilerService()
