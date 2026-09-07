"""Content Generator Agent: turns approved allocations into draft channel creative.

Built on the same shape as the Analyst Agent:

* ``ContentGeneratorAgent`` (ABC) - infra-agnostic interface.
* ``BedrockContentGeneratorAgent`` - Amazon Bedrock reasoning (cheap model by
  default, ``settings.bedrock_content_model``) with a deterministic template
  engine as the offline / failure fallback.
* ``get_content_generator_agent()`` - the real agent, ready for standalone use
  (see ``augury.api.content_lambda`` and ``scripts/run_content.py``).

It only *reads* ``ExperimentPlan`` / ``Allocation`` data and emits a
``ContentPackage``; it never touches budgets, allocations, or graph state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable, Optional

from langchain_core.messages import SystemMessage, HumanMessage

from augury.config import settings
from augury.logging import logger
from augury.models import ModelFactory, get_content_structured_model
from augury.schemas.content import GeneratedCreativePackage
from augury.schemas.experiment import Channel, Allocation, ExperimentPlan
from augury.schemas.content import (
    ContentFormat,
    ContentAsset,
    ChannelContent,
    ContentPackage,
    CHANNEL_FORMAT,
)
from augury.agents.prompts import CONTENT_SYSTEM_PROMPT, CONTENT_HUMAN_PREAMBLE

# Per-format soft length limits (chars). Overflow is flagged, not dropped.
_LIMITS: dict[ContentFormat, dict[str, int]] = {
    ContentFormat.SEARCH_AD: {"headline": 30, "body": 90, "secondary_headline": 30},
    ContentFormat.LINKEDIN_SPONSORED: {"headline": 70, "body": 700},
    ContentFormat.META_AD: {"headline": 40, "body": 300},
    ContentFormat.COLD_EMAIL: {"headline": 60, "body": 900},
    ContentFormat.FOUNDER_POST: {"headline": 120, "body": 1500},
}

_ANGLES = ["outcome-led", "pain-led", "speed-led", "proof-led", "cost-led", "curiosity-led", "authority-led"]
_CTAS = ["Book a demo", "See it in action", "Get a 15-min walkthrough", "Start free"]


def _clip(text: str, limit: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _normalize_multiline(text: str) -> str:
    """Collapse intra-line whitespace but keep paragraph breaks. No truncation."""
    lines = [" ".join(line.split()) for line in str(text or "").splitlines()]
    return "\n".join(lines).strip("\n")


def _clip_multiline(text: str, limit: int) -> str:
    """Like :func:`_normalize_multiline`, then enforce a total length."""
    joined = _normalize_multiline(text)
    if len(joined) <= limit:
        return joined
    return joined[: max(0, limit - 1)].rstrip() + "…"


def _first_words(text: str, n: int) -> str:
    return " ".join(str(text or "").split()[:n])


class ContentGeneratorAgent(ABC):
    """Abstract interface for the Content Generator Agent."""

    @abstractmethod
    def generate_content(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        *,
        startup_profile: Any = None,
        founder_brief: Any = None,
        only_channels: Optional[Iterable[Channel]] = None,
    ) -> ContentPackage:
        ...


class BedrockContentGeneratorAgent(ContentGeneratorAgent):
    """Bedrock-backed generator with a deterministic template fallback."""

    def __init__(
        self,
        structured_model: Any = None,
        *,
        force_deterministic: bool = False,
        variants: Optional[int] = None,
    ):
        self.variants = max(1, int(variants if variants is not None else settings.content_variants_per_channel))
        if force_deterministic:
            self._structured_model = None
        elif structured_model is not None:
            self._structured_model = structured_model
        elif not settings.use_stub_models:
            self._structured_model = get_content_structured_model(GeneratedCreativePackage)
        elif ModelFactory.bedrock_credentials_available():
            try:
                self._structured_model = get_content_structured_model(ChannelContent)
            except Exception as exc:  # pragma: no cover - ambient AWS
                logger.warning(f"content model unavailable ({exc}); deterministic only", extra={"agent": "content"})
                self._structured_model = None
        else:
            self._structured_model = None

    # ------------------------------------------------------------------ public

    def generate_content(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        *,
        startup_profile: Any = None,
        founder_brief: Any = None,
        only_channels: Optional[Iterable[Channel]] = None,
    ) -> ContentPackage:
        name = _resolve_name(founder_brief, startup_profile)
        pitch = getattr(founder_brief, "one_line_pitch", "") or ""
        wanted = set(only_channels) if only_channels is not None else None

        items: list[ChannelContent] = []
        used_llm = 0
        for alloc in plan.allocations:
            if wanted is not None and alloc.channel not in wanted:
                continue
            cc, via_llm = self._one_channel(alloc, cycle_id, name, pitch)
            used_llm += int(via_llm)
            items.append(self._postprocess_channel(cc, alloc))

        summary = (
            f"Cycle {cycle_id}: draft creative for {len(items)} channel(s) "
            f"({self.variants} variants each) aligned to each experiment's hypothesis and audience."
        )
        package = ContentPackage(cycle_id=cycle_id, startup_name=name, items=items, summary=summary)
        logger.info(
            f"Content generated for cycle {cycle_id}",
            extra={"cycle_id": cycle_id, "agent": "content",
                   "channel": ",".join(i.channel.value for i in items)},
        )
        # Guarantee a re-validated object, never a raw dict.
        return ContentPackage.model_validate(package.model_dump())

    # ------------------------------------------------------------------ per channel

    def _one_channel(self, alloc: Allocation, cycle_id: int, name: str, pitch: str) -> tuple[ChannelContent, bool]:
        if self._structured_model is not None:
            try:
                messages = [
                    SystemMessage(content=CONTENT_SYSTEM_PROMPT),
                    HumanMessage(content=self._prompt(alloc, cycle_id, name, pitch)),
                ]
                raw = self._structured_model.invoke(messages)
                if isinstance(raw, GeneratedCreativePackage):
                    fmt = CHANNEL_FORMAT[alloc.channel]
                    cc = ChannelContent(channel=alloc.channel, experiment_id=alloc.experiment_id, format=fmt,
                        hypothesis=alloc.hypothesis, audience=alloc.audience, message_angle=alloc.message_angle,
                        assets=[ContentAsset(format=fmt, **a.model_dump()) for a in raw.assets],
                        targeting_notes=raw.targeting_notes, compliance_notes=raw.compliance_notes)
                else:
                    cc = raw if isinstance(raw, ChannelContent) else ChannelContent.model_validate(raw)
                return cc, True
            except Exception as exc:
                if not settings.use_stub_models:
                    raise RuntimeError(f"Bedrock Content failed for {alloc.channel.value}; no fallback was used") from exc
                logger.warning(
                    f"content model failed for {alloc.channel.value} ({exc}); using templates",
                    extra={"cycle_id": cycle_id, "agent": "content"},
                )
        return self._deterministic_channel(alloc, name, pitch), False

    def _prompt(self, alloc: Allocation, cycle_id: int, name: str, pitch: str) -> str:
        fmt = CHANNEL_FORMAT[alloc.channel]
        limits = ", ".join(f"{k}<= {v}" for k, v in _LIMITS[fmt].items())
        return "\n".join([
            CONTENT_HUMAN_PREAMBLE,
            f"\nStartup: {name or 'the startup'}",
            f"One-liner: {pitch or '(not provided)'}",
            f"Cycle: {cycle_id}",
            f"\nChannel: {alloc.channel.value}  -> format {fmt.value} (limits: {limits})",
            f"Experiment: {alloc.experiment_id}",
            f"Hypothesis: {alloc.hypothesis}",
            f"Audience: {alloc.audience}",
            f"Message angle: {alloc.message_angle}",
            f"\nProduce {self.variants} distinct variant asset(s).",
        ])

    def _deterministic_channel(self, alloc: Allocation, name: str, pitch: str) -> ChannelContent:
        fmt = CHANNEL_FORMAT[alloc.channel]
        builder = {
            ContentFormat.SEARCH_AD: self._search_ad,
            ContentFormat.LINKEDIN_SPONSORED: self._linkedin,
            ContentFormat.META_AD: self._meta,
            ContentFormat.COLD_EMAIL: self._cold_email,
            ContentFormat.FOUNDER_POST: self._founder_post,
        }[fmt]
        assets = [builder(alloc, name, pitch, _ANGLES[i % len(_ANGLES)], i) for i in range(self.variants)]
        return ChannelContent(
            channel=alloc.channel,
            experiment_id=alloc.experiment_id,
            format=fmt,
            hypothesis=alloc.hypothesis,
            audience=alloc.audience,
            message_angle=alloc.message_angle,
            assets=assets,
            targeting_notes=f"Target: {alloc.audience}. Derived from experiment {alloc.experiment_id}.",
            compliance_notes="Template draft - verify every claim and add required disclaimers before publishing.",
        )

    # ---- format templates (deterministic, distinct per variant, within limits) ----

    def _search_ad(self, a: Allocation, name: str, pitch: str, angle: str, i: int) -> ContentAsset:
        brand = name or "Our platform"
        msg, aud = a.message_angle, _first_words(a.audience, 3)
        heads = [
            _clip(msg or brand, 30),
            _clip(f"{brand} for {aud}", 30),
            _clip(f"{aud}: less busywork", 30),
            _clip(f"{msg} — fast", 30),
            _clip(f"Try {brand} free", 30),
        ]
        bodies = [
            _clip(f"{msg}. Built for {a.audience}.", 90),
            _clip(f"{a.hypothesis} See how {brand} helps.", 90),
            _clip(f"{msg}. Book a 15-minute demo today.", 90),
        ]
        return ContentAsset(
            variant_label=f"{chr(65 + i)} · {angle}",
            format=ContentFormat.SEARCH_AD,
            headline=heads[i % len(heads)],
            body=bodies[i % len(bodies)],
            call_to_action=_CTAS[i % len(_CTAS)],
            secondary_headlines=[
                heads[(i + 1) % len(heads)],
                heads[(i + 2) % len(heads)],
                _clip("Book a demo today", 30),
            ],
        )

    def _linkedin(self, a: Allocation, name: str, pitch: str, angle: str, i: int) -> ContentAsset:
        brand = name or "We"
        hooks = [
            f"{_first_words(a.audience, 5)}: {a.message_angle}.",
            f"Most teams accept this as normal. It isn't: {a.message_angle}.",
            f"A question we hear every week from {_first_words(a.audience, 4)}: can this be faster?",
        ]
        body = (
            f"{hooks[i % len(hooks)]}\n\n{a.hypothesis} "
            f"{brand} helps teams get there without adding headcount. "
            f"If that's on your roadmap this quarter, it's worth 15 minutes."
        )
        return ContentAsset(
            variant_label=f"{chr(65 + i)} · {angle}",
            format=ContentFormat.LINKEDIN_SPONSORED,
            headline=_clip(f"{a.message_angle}" if i % 2 == 0 else f"{brand}: {_first_words(a.message_angle, 6)}", 70),
            body=_clip_multiline(body, _LIMITS[ContentFormat.LINKEDIN_SPONSORED]["body"]),
            call_to_action=_CTAS[i % len(_CTAS)],
        )

    def _meta(self, a: Allocation, name: str, pitch: str, angle: str, i: int) -> ContentAsset:
        opens = [a.message_angle, f"Built for {_first_words(a.audience, 4)}.", "See it work in 2 minutes."]
        rot = opens[i % len(opens):] + opens[: i % len(opens)]
        return ContentAsset(
            variant_label=f"{chr(65 + i)} · {angle}",
            format=ContentFormat.META_AD,
            headline=_clip([a.message_angle, name or "See a demo", f"{_first_words(a.audience,2)} — faster"][i % 3] or "See a demo", 40),
            body=_clip_multiline("\n".join(rot), 300),
            call_to_action=_CTAS[i % len(_CTAS)],
        )

    def _cold_email(self, a: Allocation, name: str, pitch: str, angle: str, i: int) -> ContentAsset:
        brand = name or "our team"
        subjects = [
            _clip(a.message_angle or "Quick question", 60),
            _clip(f"{_first_words(a.audience, 3)} — quick idea", 60),
            _clip(f"re: {_first_words(a.hypothesis, 5)}", 60),
        ]
        body = (
            f"Hi there,\n\n"
            f"Most {_first_words(a.audience, 5)} I speak with run into the same thing: "
            f"{a.hypothesis.rstrip('.')}.\n\n"
            f"{a.message_angle}. That's what {brand} does. Worth a quick look?\n\n"
            f"- Sent on behalf of {brand}"
        )
        return ContentAsset(
            variant_label=f"{chr(65 + i)} · {angle}",
            format=ContentFormat.COLD_EMAIL,
            headline=subjects[i % len(subjects)],
            body=_clip_multiline(body, _LIMITS[ContentFormat.COLD_EMAIL]["body"]),
            call_to_action=_CTAS[i % len(_CTAS)],
        )

    def _founder_post(self, a: Allocation, name: str, pitch: str, angle: str, i: int) -> ContentAsset:
        brand = name or "our product"
        opens = [
            f"A pattern I keep seeing with {_first_words(a.audience, 5)}:",
            f"We almost didn't build {brand}. Here's what changed my mind:",
            f"Unpopular opinion for {_first_words(a.audience, 4)}:",
        ]
        body = (
            f"{opens[i % len(opens)]}\n\n"
            f"{a.hypothesis} It's rarely a people problem — it's a tooling gap.\n\n"
            f"That gap is why we built {brand}. {a.message_angle}. "
            f"Happy to walk anyone through what we've learned."
        )
        heads = [f"Why we built {brand}", f"The {_first_words(a.audience, 2)} tooling gap", f"What {brand} taught us"]
        return ContentAsset(
            variant_label=f"{chr(65 + i)} · {angle}",
            format=ContentFormat.FOUNDER_POST,
            headline=_clip(heads[i % len(heads)], 120),
            body=_clip_multiline(body, _LIMITS[ContentFormat.FOUNDER_POST]["body"]),
            call_to_action="DM me for a walkthrough",
        )

    # ---- validation / normalization ------------------------------------

    def _postprocess_channel(self, cc: ChannelContent, alloc: Allocation) -> ChannelContent:
        fmt = CHANNEL_FORMAT[alloc.channel]
        limits = _LIMITS[fmt]

        seen: set[tuple[str, str]] = set()
        assets: list[ContentAsset] = []
        for idx, asset in enumerate(cc.assets or []):
            headline = " ".join(str(asset.headline or "").split())
            body = _normalize_multiline(asset.body)
            key = (headline.lower(), body.lower())
            if key in seen:
                continue
            seen.add(key)

            warnings: list[str] = []
            if headline and len(headline) > limits["headline"]:
                warnings.append(f"headline {len(headline)}/{limits['headline']}")
            if body and len(body) > limits["body"]:
                warnings.append(f"body {len(body)}/{limits['body']}")
            sec = list(asset.secondary_headlines or [])
            if "secondary_headline" in limits:
                for s in sec:
                    if len(s) > limits["secondary_headline"]:
                        warnings.append(f"secondary_headline {len(s)}/{limits['secondary_headline']}")

            assets.append(ContentAsset(
                variant_label=asset.variant_label or f"{chr(65 + idx)}",
                format=fmt,
                headline=headline,
                body=body,
                call_to_action=asset.call_to_action or (_CTAS[idx % len(_CTAS)] if settings.use_stub_models else ''),
                secondary_headlines=sec,
                hashtags=list(asset.hashtags or []),
                char_counts={
                    "headline": len(headline),
                    "body": len(body),
                    "call_to_action": len(asset.call_to_action or ""),
                },
                length_warnings=warnings,
            ))

        if not assets:  # LLM returned nothing usable -> deterministic backfill
            if not settings.use_stub_models:
                raise ValueError('Bedrock returned no usable content assets')
            assets = self._deterministic_channel(alloc, "", "").assets
        assets = assets[: self.variants] if len(assets) > self.variants else assets

        return ChannelContent(
            channel=alloc.channel,
            experiment_id=alloc.experiment_id,
            format=fmt,
            hypothesis=alloc.hypothesis,
            audience=alloc.audience,
            message_angle=alloc.message_angle,
            assets=assets,
            targeting_notes=cc.targeting_notes or f"Target: {alloc.audience}.",
            compliance_notes=cc.compliance_notes or "Draft - verify claims and add disclaimers before publishing.",
        )


def _resolve_name(founder_brief: Any, startup_profile: Any) -> str:
    for obj in (founder_brief, startup_profile):
        n = getattr(obj, "startup_name", None)
        if n:
            return str(n)
    return ""


def get_content_generator_agent(variants: Optional[int] = None) -> ContentGeneratorAgent:
    """The real Content Generator: Bedrock when credentials resolve, deterministic templates otherwise."""
    return BedrockContentGeneratorAgent(variants=variants)
