"""Founder intake: turn onboarding answers into a validated :class:`FounderBrief`.

* ``MockIntakeProvider``  - unchanged seeded LedgerAI brief (demo / tests).
* ``FileIntakeProvider``  - production default: reads ``data/founder_briefs/<startup_id>.json``
  (either a full ``FounderBrief`` or a loose ``FounderIntakeForm``) and returns a
  validated brief. Falls back to the bundled LedgerAI brief for ``ledger_ai``.
* ``DictIntakeProvider``  - in-memory mapping, for embedding / API use.
* ``normalize_founder_brief`` / ``FounderIntakeForm`` - the real normalization:
  channel-name canonicalization, allocation renormalization to sum 1.0, goal-type
  inference, preference/exclusion parsing. No graph or strategist coupling.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

from augury.schemas.founder import (
    FounderBrief,
    PrimaryGoal,
    GoalType,
    ChannelPreference,
    ExclusionRule,
)
from augury.schemas.experiment import Channel
from augury.storage.json_store import JsonStore, LocalJsonStore

_DEFAULT_BRIEF_DIR = os.path.join("data", "founder_briefs")

# Loose channel spellings -> canonical Channel value.
_CHANNEL_ALIASES: dict[str, Channel] = {
    "google": Channel.GOOGLE_SEARCH, "google search": Channel.GOOGLE_SEARCH,
    "google ads": Channel.GOOGLE_SEARCH, "search": Channel.GOOGLE_SEARCH,
    "sem": Channel.GOOGLE_SEARCH, "ppc": Channel.GOOGLE_SEARCH, "adwords": Channel.GOOGLE_SEARCH,
    "linkedin": Channel.LINKEDIN, "linked in": Channel.LINKEDIN, "li": Channel.LINKEDIN,
    "linkedin ads": Channel.LINKEDIN,
    "meta": Channel.META, "facebook": Channel.META, "fb": Channel.META,
    "instagram": Channel.META, "ig": Channel.META, "meta ads": Channel.META,
    "cold email": Channel.COLD_EMAIL, "email": Channel.COLD_EMAIL, "outbound": Channel.COLD_EMAIL,
    "cold outreach": Channel.COLD_EMAIL, "outreach": Channel.COLD_EMAIL,
    "founder content": Channel.FOUNDER_CONTENT, "content": Channel.FOUNDER_CONTENT,
    "founder led content": Channel.FOUNDER_CONTENT, "founder-led content": Channel.FOUNDER_CONTENT,
    "organic social": Channel.FOUNDER_CONTENT, "thought leadership": Channel.FOUNDER_CONTENT,
    "founder brand": Channel.FOUNDER_CONTENT,
}

_GOAL_ALIASES: dict[str, GoalType] = {
    "demo": GoalType.DEMO_BOOKINGS, "demos": GoalType.DEMO_BOOKINGS,
    "demo booking": GoalType.DEMO_BOOKINGS, "demo bookings": GoalType.DEMO_BOOKINGS,
    "qualified demo bookings": GoalType.DEMO_BOOKINGS, "meetings": GoalType.DEMO_BOOKINGS,
    "paid": GoalType.PAID_CONVERSIONS, "paid conversion": GoalType.PAID_CONVERSIONS,
    "paid conversions": GoalType.PAID_CONVERSIONS, "purchases": GoalType.PAID_CONVERSIONS,
    "customers": GoalType.PAID_CONVERSIONS, "subscriptions": GoalType.PAID_CONVERSIONS,
    "lead": GoalType.LEAD_SIGNUPS, "leads": GoalType.LEAD_SIGNUPS,
    "signups": GoalType.LEAD_SIGNUPS, "sign ups": GoalType.LEAD_SIGNUPS,
    "waitlist": GoalType.WAITLIST_SIGNUPS, "waitlist signups": GoalType.WAITLIST_SIGNUPS,
}


def canonical_channel(name: Any) -> Optional[str]:
    """Map a loose channel spelling to a ``Channel`` value string, or None if unknown."""
    if name is None:
        return None
    token = str(name).strip()
    if not token:
        return None
    upper = token.upper().replace(" ", "_").replace("-", "_")
    try:
        return Channel(upper).value
    except ValueError:
        pass
    alias = _CHANNEL_ALIASES.get(token.lower().replace("_", " ").replace("-", " "))
    return alias.value if alias is not None else None


def _infer_goal_type(raw: Any, metric_name: str) -> GoalType:
    for candidate in (raw, metric_name):
        if not candidate:
            continue
        key = str(candidate).strip().lower()
        if key in _GOAL_ALIASES:
            return _GOAL_ALIASES[key]
        for alias, gt in _GOAL_ALIASES.items():
            if alias in key:
                return gt
    return GoalType.DEMO_BOOKINGS


def _renormalize_allocations(raw: dict[str, Any], excluded: set[str]) -> dict[str, float]:
    """Canonicalize keys, drop excluded channels, and scale weights to sum to 1.0."""
    weights: dict[str, float] = {}
    for name, value in (raw or {}).items():
        ch = canonical_channel(name)
        if ch is None or ch in excluded:
            continue
        try:
            w = float(value)
        except (TypeError, ValueError):
            continue
        if w < 0:
            continue
        weights[ch] = weights.get(ch, 0.0) + w

    total = sum(weights.values())
    if total <= 0:
        pool = [c.value for c in Channel if c.value not in excluded]
        if not pool:
            return {}
        even = round(1.0 / len(pool), 4)
        shares = {c: even for c in pool}
        shares[pool[0]] = round(shares[pool[0]] + (1.0 - even * len(pool)), 4)
        return shares

    shares = {c: round(w / total, 4) for c, w in weights.items()}
    residual = round(1.0 - sum(shares.values()), 4)
    if residual and shares:
        top = max(shares, key=shares.get)
        shares[top] = round(shares[top] + residual, 4)
    return shares


class FounderIntakeForm(BaseModel):
    """Loose onboarding answers as a founder (or a UI) would submit them."""

    startup_name: str
    stage: str = "Seed"
    one_line_pitch: str
    total_budget: float = Field(gt=0)
    goal_metric: str = "Qualified Demo Bookings"
    goal_type: Optional[str] = None
    target_cac: float = Field(gt=0)
    minimum_acceptable_volume: int = Field(default=5, ge=1)
    # channel -> weight (percentages or fractions; canonicalized + renormalized)
    initial_allocations: dict[str, Any] = Field(default_factory=dict)
    # channel -> free-text note, or list of {channel, note, strength}
    soft_preferences: Any = Field(default_factory=list)
    # list of channel names, or list of {channel, reason}
    hard_exclusions: Any = Field(default_factory=list)


def _parse_exclusions(raw: Any) -> list[ExclusionRule]:
    rules: list[ExclusionRule] = []
    seen: set[str] = set()
    items = raw if isinstance(raw, list) else ([raw] if raw else [])
    for item in items:
        if isinstance(item, dict):
            ch = canonical_channel(item.get("channel"))
            reason = str(item.get("reason") or "Founder hard exclusion")
            permanent = bool(item.get("is_permanent", True))
        else:
            ch = canonical_channel(item)
            reason, permanent = "Founder hard exclusion", True
        if ch and ch not in seen:
            seen.add(ch)
            rules.append(ExclusionRule(channel=ch, reason=reason, is_permanent=permanent))
    return rules


def _parse_preferences(raw: Any, excluded: set[str]) -> list[ChannelPreference]:
    prefs: list[ChannelPreference] = []
    seen: set[str] = set()
    if isinstance(raw, dict):
        items: list[Any] = [{"channel": k, "note": v} for k, v in raw.items()]
    elif isinstance(raw, list):
        items = raw
    else:
        items = []
    for item in items:
        if isinstance(item, dict):
            ch = canonical_channel(item.get("channel"))
            note = str(item.get("note") or item.get("founder_note") or "Founder soft preference")
            strength = item.get("prior_belief_strength", item.get("strength", 0.6))
        else:
            ch, note, strength = canonical_channel(item), "Founder soft preference", 0.6
        try:
            strength = max(0.0, min(1.0, float(strength)))
        except (TypeError, ValueError):
            strength = 0.6
        if ch and ch not in seen and ch not in excluded:
            seen.add(ch)
            prefs.append(ChannelPreference(channel=ch, prior_belief_strength=strength, founder_note=note))
    return prefs


def normalize_founder_brief(form: FounderIntakeForm | dict[str, Any]) -> FounderBrief:
    """Convert loose intake answers into a validated, self-consistent FounderBrief."""
    if not isinstance(form, FounderIntakeForm):
        form = FounderIntakeForm.model_validate(form)

    exclusions = _parse_exclusions(form.hard_exclusions)
    excluded = {e.channel for e in exclusions}
    prefs = _parse_preferences(form.soft_preferences, excluded)
    allocations = _renormalize_allocations(form.initial_allocations, excluded)

    goal = PrimaryGoal(
        goal_type=_infer_goal_type(form.goal_type, form.goal_metric),
        target_cac=form.target_cac,
        minimum_acceptable_volume=form.minimum_acceptable_volume,
        metric_name=form.goal_metric or "Qualified Demo Bookings",
    )

    return FounderBrief(
        startup_name=form.startup_name,
        stage=form.stage or "Seed",
        one_line_pitch=form.one_line_pitch,
        total_budget=form.total_budget,
        primary_goal=goal,
        initial_allocations=allocations,
        soft_preferences=prefs,
        hard_exclusions=exclusions,
    )


def _coerce_to_brief(payload: dict[str, Any]) -> FounderBrief:
    """Accept either a full FounderBrief document or a loose FounderIntakeForm."""
    looks_like_form = "goal_metric" in payload or "target_cac" in payload or (
        "primary_goal" not in payload and "goal_type" in payload
    )
    if looks_like_form:
        return normalize_founder_brief(payload)
    try:
        return FounderBrief.model_validate(payload)
    except Exception:
        return normalize_founder_brief(payload)


class IntakeProvider(ABC):
    """Abstract interface for founder intake providers."""

    @abstractmethod
    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        """Retrieve the founder intake brief."""
        pass


def _ledger_ai_brief() -> FounderBrief:
    return FounderBrief(
        startup_name="LedgerAI",
        stage="Seed",
        one_line_pitch="Autonomous financial reconciliations and AI ledger software for mid-market CFOs",
        total_budget=2000.0,
        primary_goal=PrimaryGoal(
            goal_type=GoalType.DEMO_BOOKINGS,
            target_cac=350.0,
            minimum_acceptable_volume=5,
            metric_name="Qualified Demo Bookings",
        ),
        initial_allocations={
            Channel.GOOGLE_SEARCH.value: 0.20,
            Channel.LINKEDIN.value: 0.25,
            Channel.META.value: 0.15,
            Channel.COLD_EMAIL.value: 0.15,
            Channel.FOUNDER_CONTENT.value: 0.25,
        },
        soft_preferences=[
            ChannelPreference(
                channel=Channel.FOUNDER_CONTENT.value,
                prior_belief_strength=0.8,
                founder_note="I strongly believe founder-led content is strategically important for building trust in B2B finance.",
            )
        ],
        hard_exclusions=[],
    )


class MockIntakeProvider(IntakeProvider):
    """Functional stub returning the seeded LedgerAI demo brief."""

    def __init__(self, brief: Optional[FounderBrief] = None):
        self._brief = brief or _ledger_ai_brief()

    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        return self._brief


class DictIntakeProvider(IntakeProvider):
    """In-memory provider backed by a ``{startup_id: FounderBrief | form dict}`` mapping."""

    def __init__(self, briefs: dict[str, Any], default: Optional[FounderBrief] = None):
        self._briefs: dict[str, FounderBrief] = {}
        for sid, value in briefs.items():
            self._briefs[sid] = value if isinstance(value, FounderBrief) else _coerce_to_brief(dict(value))
        self._default = default

    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        if startup_id in self._briefs:
            return self._briefs[startup_id]
        if self._default is not None:
            return self._default
        raise KeyError(f"No founder brief registered for startup_id={startup_id!r}")


class FileIntakeProvider(IntakeProvider):
    """Production intake: read a validated brief from ``<brief_dir>/<startup_id>.json``.

    The file may be a full ``FounderBrief`` document or a loose
    ``FounderIntakeForm``; both are returned as a validated ``FounderBrief``.
    ``ledger_ai`` falls back to the bundled brief when no file is present.
    """

    def __init__(self, brief_dir: str = _DEFAULT_BRIEF_DIR):
        self.brief_dir = brief_dir

    def _path(self, startup_id: str) -> str:
        safe = "".join(c for c in startup_id if c.isalnum() or c in ("_", "-")).strip() or "default"
        return os.path.join(self.brief_dir, f"{safe}.json")

    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        path = self._path(startup_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                return _coerce_to_brief(json.load(fh))
        if startup_id == "ledger_ai":
            return _ledger_ai_brief()
        raise FileNotFoundError(f"No founder brief file for startup_id={startup_id!r} at {path}")


class JsonIntakeProvider(IntakeProvider):
    """Intake provider backed by a JSON object store such as S3."""

    def __init__(self, store: JsonStore, prefix: str = "founder_briefs"):
        self.store = store
        self.prefix = prefix.strip("/")

    def get_founder_brief(self, startup_id: str) -> FounderBrief:
        safe = "".join(c for c in startup_id if c.isalnum() or c in ("_", "-")) or "default"
        try:
            return _coerce_to_brief(self.store.get_json(f"{self.prefix}/{safe}.json"))
        except Exception:
            if startup_id == "ledger_ai":
                return _ledger_ai_brief()
            raise


def get_intake_provider(brief_dir: str = _DEFAULT_BRIEF_DIR) -> IntakeProvider:
    """File-backed intake when a brief directory exists, else the seeded mock."""
    if os.path.isdir(brief_dir):
        return FileIntakeProvider(brief_dir)
    return MockIntakeProvider()
