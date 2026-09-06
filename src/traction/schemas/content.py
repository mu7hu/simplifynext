"""Marketing content generation schemas (new; not part of the frozen cross-team contracts).

The Content Generator Agent reads ``ExperimentPlan`` / ``Allocation`` data
(channel, hypothesis, audience, message_angle) and produces channel-appropriate
draft creative. These schemas are the agent's *output* contract only - they never
feed budget or allocation logic.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from traction.schemas.experiment import Channel


class ContentFormat(str, Enum):
    """Creative format, derived from the channel."""
    SEARCH_AD = "SEARCH_AD"
    LINKEDIN_SPONSORED = "LINKEDIN_SPONSORED"
    META_AD = "META_AD"
    COLD_EMAIL = "COLD_EMAIL"
    FOUNDER_POST = "FOUNDER_POST"


CHANNEL_FORMAT: dict[Channel, ContentFormat] = {
    Channel.GOOGLE_SEARCH: ContentFormat.SEARCH_AD,
    Channel.LINKEDIN: ContentFormat.LINKEDIN_SPONSORED,
    Channel.META: ContentFormat.META_AD,
    Channel.COLD_EMAIL: ContentFormat.COLD_EMAIL,
    Channel.FOUNDER_CONTENT: ContentFormat.FOUNDER_POST,
}


class ContentAsset(BaseModel):
    """One self-contained creative variant for a channel."""
    variant_label: str = Field(description="Short label, e.g. 'A', 'B', 'pain-led'")
    format: ContentFormat
    headline: str = Field(default="", description="Primary headline / subject line")
    body: str = Field(default="", description="Primary body text / ad description / email body")
    call_to_action: str = Field(default="", description="CTA text or button label")
    # Optional structured extras for formats that need them.
    secondary_headlines: list[str] = Field(default_factory=list, description="Extra headlines (e.g. RSA)")
    hashtags: list[str] = Field(default_factory=list)
    char_counts: dict[str, int] = Field(default_factory=dict, description="Length of key fields for QA")
    length_warnings: list[str] = Field(default_factory=list, description="Fields exceeding channel limits")


class ChannelContent(BaseModel):
    """All generated creative for a single planned channel/experiment."""
    channel: Channel
    experiment_id: str
    format: ContentFormat
    hypothesis: str
    audience: str
    message_angle: str
    assets: list[ContentAsset] = Field(default_factory=list, min_length=1)
    targeting_notes: str = Field(default="", description="Audience / placement guidance for the operator")
    compliance_notes: str = Field(default="", description="Claims to substantiate, disclaimers, brand-safety notes")


class ContentPackage(BaseModel):
    """Complete content drop for one planning cycle."""
    cycle_id: int = Field(ge=1)
    startup_name: str = Field(default="")
    items: list[ChannelContent] = Field(default_factory=list)
    summary: str = Field(default="", description="One-paragraph overview of the creative direction")
    disclaimer: str = Field(
        default=(
            "Draft creative for review. Does not set budgets or allocations, and "
            "must be fact-checked and brand-reviewed before publishing."
        )
    )
