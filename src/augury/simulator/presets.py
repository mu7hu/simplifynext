"""Preset market environments for testing and evaluation."""

from augury.schemas.experiment import Channel
from augury.simulator.channel import ChannelGroundTruth

# Ground truth market configuration for the LedgerAI demo startup
LEDGER_AI_MARKET_PRESET: dict[Channel, ChannelGroundTruth] = {
    Channel.GOOGLE_SEARCH: ChannelGroundTruth(
        channel=Channel.GOOGLE_SEARCH,
        base_unit_cost=12.0,            # $12 CPC
        base_conversion_rate=0.045,      # 4.5% click-to-demo conversion
        saturation_spend=2500.0,
        diminishing_returns_gamma=0.85,
        noise_std=0.12,
        response_delay_days=3,
        min_evaluation_days=14,
        audience_fit_score=1.3           # High search intent for AI ledger software
    ),
    Channel.COLD_EMAIL: ChannelGroundTruth(
        channel=Channel.COLD_EMAIL,
        base_unit_cost=2.0,              # $2 per send/contact
        base_conversion_rate=0.018,      # 1.8% to demo
        saturation_spend=400.0,          # Small TAM, saturates fast
        diminishing_returns_gamma=0.55,
        noise_std=0.15,
        response_delay_days=5,
        min_evaluation_days=14,
        audience_fit_score=1.0
    ),
    Channel.META: ChannelGroundTruth(
        channel=Channel.META,
        base_unit_cost=3.5,              # Cheap clicks
        base_conversion_rate=0.004,      # Low intent for enterprise SaaS
        saturation_spend=1200.0,
        diminishing_returns_gamma=0.60,
        noise_std=0.25,                  # High volatility
        response_delay_days=7,
        min_evaluation_days=14,
        audience_fit_score=0.6           # Underperforming fit
    ),
    Channel.LINKEDIN: ChannelGroundTruth(
        channel=Channel.LINKEDIN,
        base_unit_cost=18.0,             # Expensive CPC
        base_conversion_rate=0.016,
        saturation_spend=2000.0,
        diminishing_returns_gamma=0.80,
        noise_std=0.30,                  # Noisy early on
        response_delay_days=30,          # 30-day enterprise consideration delay
        min_evaluation_days=35,          # Requires long window
        audience_fit_score=0.9
    ),
    Channel.FOUNDER_CONTENT: ChannelGroundTruth(
        channel=Channel.FOUNDER_CONTENT,
        base_unit_cost=8.0,              # Time cost normalized per interaction
        base_conversion_rate=0.0015,     # Very low direct demo booking rate
        saturation_spend=800.0,
        diminishing_returns_gamma=0.50,
        noise_std=0.35,
        response_delay_days=21,
        min_evaluation_days=28,
        audience_fit_score=0.5           # Founder thought leadership takes months to convert
    ),
}
