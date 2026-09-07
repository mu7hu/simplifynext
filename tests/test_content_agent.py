"""Component tests for the Content Generator Agent."""

from __future__ import annotations

from augury.agents.content import BedrockContentGeneratorAgent, get_content_generator_agent
from augury.schemas.content import (
    ContentPackage,
    ChannelContent,
    ContentAsset,
    ContentFormat,
    CHANNEL_FORMAT,
)
from augury.schemas.experiment import Channel
from augury.services.intake import MockIntakeProvider

from tests._analyst_fixtures import sample_plan


def _agent(variants=3):
    return BedrockContentGeneratorAgent(force_deterministic=True, variants=variants)


def test_generates_one_item_per_channel_with_correct_format():
    pkg = _agent().generate_content(2, sample_plan())
    assert isinstance(pkg, ContentPackage)
    assert {i.channel for i in pkg.items} == {a.channel for a in sample_plan().allocations}
    for item in pkg.items:
        assert isinstance(item, ChannelContent)
        assert item.format == CHANNEL_FORMAT[item.channel]
        assert 1 <= len(item.assets) <= 3
        assert all(isinstance(a, ContentAsset) for a in item.assets)
        assert all(a.headline and a.body and a.call_to_action for a in item.assets)
        # variants are distinct
        assert len({(a.headline, a.body) for a in item.assets}) == len(item.assets)
        assert len({a.variant_label for a in item.assets}) == len(item.assets)


def test_variants_override_and_content_carries_experiment_context():
    pkg = _agent(variants=2).generate_content(4, sample_plan())
    for item, alloc in zip(pkg.items, sample_plan().allocations):
        assert len(item.assets) == 2
        assert item.experiment_id == alloc.experiment_id
        assert item.hypothesis == alloc.hypothesis
        assert item.audience == alloc.audience
        assert item.message_angle == alloc.message_angle


def test_only_channels_filter():
    pkg = _agent().generate_content(2, sample_plan(), only_channels=[Channel.GOOGLE_SEARCH])
    assert [i.channel for i in pkg.items] == [Channel.GOOGLE_SEARCH]


def test_search_ad_stays_within_headline_limit():
    pkg = _agent().generate_content(2, sample_plan())
    g = next(i for i in pkg.items if i.channel == Channel.GOOGLE_SEARCH)
    for a in g.assets:
        assert len(a.headline) <= 30
        assert not a.length_warnings  # deterministic templates fit
        assert a.secondary_headlines  # RSA needs extras


def test_startup_name_resolved_from_brief():
    brief = MockIntakeProvider().get_founder_brief("ledger_ai")
    pkg = _agent().generate_content(2, sample_plan(), founder_brief=brief)
    assert pkg.startup_name == "LedgerAI"
    assert "LedgerAI" in pkg.items[0].assets[0].headline or "LedgerAI" in pkg.items[0].assets[0].body \
        or any("LedgerAI" in s for s in pkg.items[0].assets[0].secondary_headlines)


def test_deterministic_output_is_stable():
    a = _agent().generate_content(2, sample_plan())
    b = _agent().generate_content(2, sample_plan())
    assert a.model_dump() == b.model_dump()


def test_get_content_generator_agent_factory():
    assert isinstance(get_content_generator_agent(), BedrockContentGeneratorAgent)


# --------------------------------------------------------------------------- #
# Mocked Bedrock: sloppy LLM output must be normalized by post-processing.     #
# --------------------------------------------------------------------------- #

class _FakeModel:
    def __init__(self, cc: ChannelContent):
        self._cc = cc
        self.calls = 0

    def invoke(self, messages, **kwargs):
        self.calls += 1
        return self._cc


def test_postprocess_forces_allocation_context_and_flags_length():
    plan = sample_plan()
    alloc = plan.allocations[0]  # GOOGLE_SEARCH
    sloppy = ChannelContent.model_construct(
        channel=Channel.META,                       # wrong channel
        experiment_id="WRONG",
        format=ContentFormat.META_AD,               # wrong format
        hypothesis="unrelated",
        audience="unrelated",
        message_angle="unrelated",
        assets=[
            ContentAsset.model_construct(
                variant_label="A", format=ContentFormat.META_AD,
                headline="This headline is deliberately way longer than thirty characters for a search ad",
                body="short body", call_to_action="", secondary_headlines=[], hashtags=[],
                char_counts={}, length_warnings=[],
            )
        ],
        targeting_notes="", compliance_notes="",
    )
    agent = BedrockContentGeneratorAgent(structured_model=_FakeModel(sloppy), variants=3)
    pkg = agent.generate_content(2, plan, only_channels=[Channel.GOOGLE_SEARCH])

    item = pkg.items[0]
    assert item.channel == Channel.GOOGLE_SEARCH            # corrected from allocation
    assert item.format == ContentFormat.SEARCH_AD
    assert item.experiment_id == alloc.experiment_id
    assert item.hypothesis == alloc.hypothesis
    a0 = item.assets[0]
    assert a0.length_warnings and any("headline" in w for w in a0.length_warnings)
    assert a0.call_to_action                                # backfilled
    assert a0.char_counts["headline"] == len(a0.headline)


def test_llm_failure_falls_back_to_templates():
    class _Boom:
        def invoke(self, *a, **k):
            raise RuntimeError("bedrock down")

    agent = BedrockContentGeneratorAgent(structured_model=_Boom(), variants=3)
    pkg = agent.generate_content(2, sample_plan())
    assert isinstance(pkg, ContentPackage)
    assert all(len(i.assets) >= 1 for i in pkg.items)
