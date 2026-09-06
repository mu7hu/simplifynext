"""Component tests for the real IntakeProvider implementations."""

from __future__ import annotations

import json

import pytest

from traction.schemas.founder import FounderBrief, GoalType
from traction.services.intake import (
    FileIntakeProvider,
    DictIntakeProvider,
    MockIntakeProvider,
    FounderIntakeForm,
    normalize_founder_brief,
    get_intake_provider,
    canonical_channel,
)

LOOSE_FORM = {
    "startup_name": "PayFlow",
    "stage": "Pre-Seed",
    "one_line_pitch": "Instant B2B payment reconciliation",
    "total_budget": 3000,
    "goal_metric": "Booked product demos",
    "target_cac": 420,
    "initial_allocations": {
        "google": 40,
        "fb": 20,
        "cold outreach": 20,
        "founder-led content": 20,
        "linkedin ads": 0,
    },
    "soft_preferences": {"content": "Founder audience trusts building-in-public posts"},
    "hard_exclusions": ["instagram"],
}


def test_channel_canonicalization():
    assert canonical_channel("google") == "GOOGLE_SEARCH"
    assert canonical_channel("FB") == "META"
    assert canonical_channel("cold outreach") == "COLD_EMAIL"
    assert canonical_channel("founder-led content") == "FOUNDER_CONTENT"
    assert canonical_channel("GOOGLE_SEARCH") == "GOOGLE_SEARCH"
    assert canonical_channel("tiktok") is None


def test_normalize_form_produces_valid_brief():
    brief = normalize_founder_brief(LOOSE_FORM)
    assert isinstance(brief, FounderBrief)
    assert brief.total_budget == 3000
    assert brief.primary_goal.goal_type == GoalType.DEMO_BOOKINGS
    assert brief.primary_goal.target_cac == 420

    # META is hard-excluded -> absent from allocations and gets an ExclusionRule.
    assert {e.channel for e in brief.hard_exclusions} == {"META"}
    assert "META" not in brief.initial_allocations

    # Weights (40/20/20/20, li=0) renormalize to sum 1.0 over the 3 funded channels.
    assert abs(sum(brief.initial_allocations.values()) - 1.0) < 1e-6
    assert brief.initial_allocations["GOOGLE_SEARCH"] == 0.5
    assert all(0.0 <= v <= 1.0 for v in brief.initial_allocations.values())

    # Soft preference dict {channel: note} -> ChannelPreference on FOUNDER_CONTENT.
    assert [p.channel for p in brief.soft_preferences] == ["FOUNDER_CONTENT"]
    assert brief.soft_preferences[0].prior_belief_strength == 0.6


def test_empty_allocations_fall_back_to_even_split():
    form = dict(LOOSE_FORM, initial_allocations={}, hard_exclusions=[])
    brief = normalize_founder_brief(form)
    assert abs(sum(brief.initial_allocations.values()) - 1.0) < 1e-6
    assert len(brief.initial_allocations) == 5  # all channels


def test_goal_type_inference_variants():
    assert normalize_founder_brief(dict(LOOSE_FORM, goal_metric="waitlist signups")).primary_goal.goal_type == GoalType.WAITLIST_SIGNUPS
    assert normalize_founder_brief(dict(LOOSE_FORM, goal_metric="paid customers")).primary_goal.goal_type == GoalType.PAID_CONVERSIONS
    assert normalize_founder_brief(dict(LOOSE_FORM, goal_type="LEAD_SIGNUPS", goal_metric="x")).primary_goal.goal_type == GoalType.LEAD_SIGNUPS


def test_file_intake_provider_reads_bundled_ledger_ai():
    brief = FileIntakeProvider().get_founder_brief("ledger_ai")
    assert isinstance(brief, FounderBrief)
    assert brief.startup_name == "LedgerAI"
    assert brief.total_budget == 2000.0
    assert any(p.channel == "FOUNDER_CONTENT" for p in brief.soft_preferences)
    assert abs(sum(brief.initial_allocations.values()) - 1.0) < 1e-6


def test_file_intake_provider_loads_form_file(tmp_path):
    d = tmp_path / "briefs"
    d.mkdir()
    (d / "payflow.json").write_text(json.dumps(LOOSE_FORM), encoding="utf-8")
    brief = FileIntakeProvider(str(d)).get_founder_brief("payflow")
    assert brief.startup_name == "PayFlow"
    assert "META" not in brief.initial_allocations


def test_file_intake_provider_missing_file_raises(tmp_path):
    d = tmp_path / "briefs"
    d.mkdir()
    with pytest.raises(FileNotFoundError):
        FileIntakeProvider(str(d)).get_founder_brief("does_not_exist")
    # ledger_ai still falls back to the bundled brief even with no file present.
    assert FileIntakeProvider(str(d)).get_founder_brief("ledger_ai").startup_name == "LedgerAI"


def test_dict_intake_provider_with_default():
    default = MockIntakeProvider().get_founder_brief("ledger_ai")
    prov = DictIntakeProvider({"payflow": LOOSE_FORM}, default=default)
    assert prov.get_founder_brief("payflow").startup_name == "PayFlow"
    assert prov.get_founder_brief("anything_else").startup_name == "LedgerAI"


def test_dict_intake_provider_without_default_raises():
    with pytest.raises(KeyError):
        DictIntakeProvider({}).get_founder_brief("missing")


def test_get_intake_provider_prefers_file_dir(tmp_path):
    d = tmp_path / "briefs"
    d.mkdir()
    assert isinstance(get_intake_provider(str(d)), FileIntakeProvider)
    assert isinstance(get_intake_provider(str(tmp_path / "nope")), MockIntakeProvider)


def test_full_form_model_roundtrips():
    form = FounderIntakeForm.model_validate(LOOSE_FORM)
    brief = normalize_founder_brief(form)
    # Re-validating the dumped brief is still a valid FounderBrief (graph-ready).
    assert FounderBrief.model_validate(brief.model_dump()) == brief
