"""Component tests for the real ProfilerService implementations."""

from __future__ import annotations

import json

import pytest

from traction.schemas.profile import StartupProfile, BenchmarkPrior, StartupStage, IndustrySector
from traction.services.profiler import (
    FileProfilerService,
    DictProfilerService,
    MockProfilerService,
    get_profiler_service,
    priors_key,
    default_b2b_saas_seed_priors,
)

REQUIRED_PRIOR_FIELDS = {
    "channel", "median_cac", "min_cac", "max_cac", "avg_cpc",
    "avg_conversion_rate", "min_evaluation_days", "rationale",
}


def test_priors_key_stem():
    assert priors_key(IndustrySector.B2B_SAAS, StartupStage.SEED) == "b2b_saas_seed"
    assert priors_key(IndustrySector.MARKETPLACE, StartupStage.SERIES_A) == "marketplace_series_a"
    assert priors_key("B2C_SUBSCRIPTION", "PRE_SEED") == "b2c_subscription_pre_seed"


def test_file_profiler_reads_bundled_ledger_ai():
    prof = FileProfilerService().get_startup_profile("ledger_ai")
    assert isinstance(prof, StartupProfile)
    assert prof.startup_name == "LedgerAI"
    assert prof.stage == StartupStage.SEED
    assert prof.sector == IndustrySector.B2B_SAAS
    assert prof.startup_id == "ledger_ai"


def test_file_profiler_priors_are_validated_and_complete():
    priors = FileProfilerService().get_benchmark_priors("ledger_ai")
    assert len(priors) == 5
    assert all(isinstance(p, BenchmarkPrior) for p in priors)
    for p in priors:
        assert REQUIRED_PRIOR_FIELDS <= set(p.model_dump().keys())
        assert p.min_cac <= p.median_cac <= p.max_cac
        assert p.min_evaluation_days >= 1


def test_file_profiler_matches_mock_for_ledger_ai():
    """The file-backed path must reproduce the seeded mock exactly (demo stability)."""
    fp, mock = FileProfilerService(), MockProfilerService()
    assert fp.get_startup_profile("ledger_ai").model_dump() == mock.get_startup_profile("ledger_ai").model_dump()
    assert [p.model_dump() for p in fp.get_benchmark_priors("ledger_ai")] == \
           [p.model_dump() for p in mock.get_benchmark_priors("ledger_ai")]


def test_file_profiler_missing_profile_raises(tmp_path):
    fp = FileProfilerService(str(tmp_path / "profiles"), str(tmp_path / "priors"))
    with pytest.raises(FileNotFoundError):
        fp.get_startup_profile("unknown_co")
    # Priors still degrade gracefully to the documented default.
    assert fp.get_benchmark_priors("unknown_co") == default_b2b_saas_seed_priors()


def test_file_profiler_sector_stage_prior_selection(tmp_path):
    pdir = tmp_path / "profiles"
    bdir = tmp_path / "priors"
    pdir.mkdir()
    bdir.mkdir()
    (pdir / "acme.json").write_text(json.dumps({
        "startup_id": "acme", "startup_name": "Acme", "stage": "SERIES_A",
        "sector": "MARKETPLACE", "target_acv": 5000.0, "sales_cycle_days": 20,
        "primary_outcome_metric": "Paid conversions",
    }), encoding="utf-8")
    (bdir / "marketplace_series_a.json").write_text(json.dumps([{
        "channel": "GOOGLE_SEARCH", "median_cac": 90.0, "min_cac": 40.0, "max_cac": 200.0,
        "avg_cpc": 2.5, "avg_conversion_rate": 0.06, "min_evaluation_days": 10,
        "rationale": "Marketplace demand capture",
    }]), encoding="utf-8")

    fp = FileProfilerService(str(pdir), str(bdir))
    priors = fp.get_benchmark_priors("acme")
    assert len(priors) == 1 and priors[0].median_cac == 90.0


def test_file_profiler_per_startup_prior_override(tmp_path):
    pdir = tmp_path / "profiles"
    bdir = tmp_path / "priors"
    pdir.mkdir()
    bdir.mkdir()
    (bdir / "acme.json").write_text(json.dumps([{
        "channel": "LINKEDIN", "median_cac": 999.0, "min_cac": 500.0, "max_cac": 1500.0,
        "avg_cpc": 20.0, "avg_conversion_rate": 0.01, "min_evaluation_days": 30,
        "rationale": "Custom override for this account",
    }]), encoding="utf-8")
    fp = FileProfilerService(str(pdir), str(bdir))
    priors = fp.get_benchmark_priors("acme")  # no profile needed - override wins
    assert len(priors) == 1 and priors[0].median_cac == 999.0


def test_dict_profiler_service():
    prof = MockProfilerService().get_startup_profile("ledger_ai")
    dp = DictProfilerService({"ledger_ai": prof}, priors={"ledger_ai": default_b2b_saas_seed_priors()})
    assert dp.get_startup_profile("ledger_ai").startup_name == "LedgerAI"
    assert len(dp.get_benchmark_priors("ledger_ai")) == 5
    # Unknown id -> default priors, but no default profile -> KeyError.
    assert dp.get_benchmark_priors("other") == default_b2b_saas_seed_priors()
    with pytest.raises(KeyError):
        dp.get_startup_profile("other")


def test_get_profiler_service_factory(tmp_path):
    (tmp_path / "profiles").mkdir()
    assert isinstance(get_profiler_service(str(tmp_path / "profiles"), str(tmp_path / "priors")), FileProfilerService)
    assert isinstance(get_profiler_service(str(tmp_path / "nope"), str(tmp_path / "priors")), MockProfilerService)


def test_profiler_does_not_import_simulator_ground_truth():
    """Profiler output must not carry hidden simulator ground truth — the module
    must not import from traction.simulator at all."""
    import ast
    import traction.services.profiler as prof_mod

    tree = ast.parse(open(prof_mod.__file__, encoding="utf-8").read())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(m.startswith("traction.simulator") for m in imported), imported
    assert "ChannelGroundTruth" not in imported

    # The output schemas carry no hidden ground-truth physics parameters.
    ground_truth_fields = {
        "base_unit_cost", "base_conversion_rate", "saturation_spend",
        "diminishing_returns_gamma", "noise_std", "audience_fit_score", "response_delay_days",
    }
    for prior in FileProfilerService().get_benchmark_priors("ledger_ai"):
        assert ground_truth_fields.isdisjoint(prior.model_dump().keys())
