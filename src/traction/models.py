"""Central model factory supporting AWS Bedrock and high-fidelity local stubs."""

import json
import os
import re
from typing import Any, Optional, Type
from pydantic import BaseModel
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage

from traction.config import settings
from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.analysis import Verdict, ExperimentVerdict, AnalysisReport


class StubStructuredModel:
    """Simulates a structured-output LLM for 100% offline, deterministic local testing."""

    def __init__(self, agent_type: str, schema: Type[BaseModel]):
        self.agent_type = agent_type
        self.schema = schema

    def invoke(self, messages: list[BaseMessage] | list[dict], **kwargs) -> BaseModel:
        # Extract cycle_id from message text if present
        text_dump = ""
        for m in messages:
            if isinstance(m, dict):
                text_dump += str(m.get("content", "")) + " "
            elif hasattr(m, "content"):
                text_dump += str(m.content) + " "

        cycle_id = 1
        cycle_match = re.search(r"\bcycle(?:_id)?\s*[:=]?\s*(\d+)\b", text_dump, re.IGNORECASE)
        if cycle_match:
            cycle_id = max(1, int(cycle_match.group(1)))

        if self.schema == ExperimentPlan or "plan" in self.schema.__name__.lower():
            return self._generate_plan(cycle_id)
        elif self.schema == AnalysisReport or "analysis" in self.schema.__name__.lower():
            return self._generate_analysis(cycle_id)
        else:
            raise ValueError(f"Unsupported schema for stub: {self.schema}")

    def _generate_plan(self, cycle_id: int) -> ExperimentPlan:
        total = 2000.0

        if cycle_id == 1:
            # Respect founder's soft preference
            allocs = [
                Allocation(
                    channel=Channel.GOOGLE_SEARCH,
                    experiment_id="EXP-01-GOOG",
                    current_budget=0.0,
                    proposed_budget=400.0,
                    proposed_share=0.20,
                    hypothesis="High-intent commercial queries for AI ledger will generate qualified demos under $350 CAC.",
                    audience="Mid-market CFOs and Controllers actively searching software",
                    message_angle="Automate multi-entity reconciliations in real-time",
                    expected_outcome_range=(1, 2),
                    confidence=0.60,
                    evaluation_window_days=14,
                    success_threshold=350.0,
                    reason="Initial baseline test for high intent search demand.",
                    evidence_used="Industry benchmark median CAC $320.",
                    is_exploration=False
                ),
                Allocation(
                    channel=Channel.LINKEDIN,
                    experiment_id="EXP-01-LINK",
                    current_budget=0.0,
                    proposed_budget=500.0,
                    proposed_share=0.25,
                    hypothesis="Sponsored content targeting Finance VPs will build pipeline.",
                    audience="VP Finance at companies 50-500 employees",
                    message_angle="Closing the books 5 days faster with autonomous reconciliation",
                    expected_outcome_range=(0, 1),
                    confidence=0.50,
                    evaluation_window_days=30,
                    success_threshold=580.0,
                    reason="Enterprise brand reach and pipeline development.",
                    evidence_used="B2B SaaS benchmark priors.",
                    is_exploration=True
                ),
                Allocation(
                    channel=Channel.META,
                    experiment_id="EXP-01-META",
                    current_budget=0.0,
                    proposed_budget=300.0,
                    proposed_share=0.15,
                    hypothesis="Retargeting website visitors on Meta will convert at low cost.",
                    audience="Finance professionals who visited the landing page",
                    message_angle="Watch a 2-minute demo of LedgerAI in action",
                    expected_outcome_range=(0, 1),
                    confidence=0.40,
                    evaluation_window_days=14,
                    success_threshold=750.0,
                    reason="Exploration of lower CPC retargeting audience.",
                    evidence_used="Prior founder allocation.",
                    is_exploration=True
                ),
                Allocation(
                    channel=Channel.COLD_EMAIL,
                    experiment_id="EXP-01-COLD",
                    current_budget=0.0,
                    proposed_budget=300.0,
                    proposed_share=0.15,
                    hypothesis="Direct personalized outreach to heads of accounting generates quick response.",
                    audience="Heads of Accounting / Controllers in tech & retail",
                    message_angle="Pain point: Month-end close backlog audit risks",
                    expected_outcome_range=(0, 1),
                    confidence=0.55,
                    evaluation_window_days=14,
                    success_threshold=400.0,
                    reason="Targeted outbound testing.",
                    evidence_used="B2B SaaS benchmark priors.",
                    is_exploration=False
                ),
                Allocation(
                    channel=Channel.FOUNDER_CONTENT,
                    experiment_id="EXP-01-FNDR",
                    current_budget=0.0,
                    proposed_budget=500.0,
                    proposed_share=0.25,
                    hypothesis="Founder thought leadership on LinkedIn establishes category authority.",
                    audience="CFO and finance executive network",
                    message_angle="The hidden cost of manual spreadsheet reconciliations",
                    expected_outcome_range=(0, 1),
                    confidence=0.50,
                    evaluation_window_days=28,
                    success_threshold=650.0,
                    reason="Honoring founder's soft prior regarding founder-led content.",
                    evidence_used="Founder brief explicit strategic belief.",
                    is_exploration=True
                )
            ]
            summary = "Cycle 1 Portfolio: Honors founder preference for Founder Content (25%) while testing Google Search and outbound channels."
        elif cycle_id in (2, 3):
            # Evidence accumulates: shift capital toward Google Search
            allocs = [
                Allocation(
                    channel=Channel.GOOGLE_SEARCH,
                    experiment_id=f"EXP-0{cycle_id}-GOOG",
                    current_budget=400.0 if cycle_id == 2 else 600.0,
                    proposed_budget=600.0 if cycle_id == 2 else 800.0,
                    proposed_share=0.30 if cycle_id == 2 else 0.40,
                    hypothesis="Scaling budget on top performing high-intent search keywords maintains sub-$350 CAC.",
                    audience="In-market CFOs actively evaluating ledger tools",
                    message_angle="Top-rated autonomous financial close platform",
                    expected_outcome_range=(2, 3),
                    confidence=0.75,
                    evaluation_window_days=14,
                    success_threshold=350.0,
                    reason="Google Search showed strong conversion efficiency in previous cycle.",
                    evidence_used=f"Observed CAC in Cycle {cycle_id - 1} was below target.",
                    is_exploration=False
                ),
                Allocation(
                    channel=Channel.LINKEDIN,
                    experiment_id=f"EXP-0{cycle_id}-LINK",
                    current_budget=500.0 if cycle_id == 2 else 400.0,
                    proposed_budget=400.0,
                    proposed_share=0.20,
                    hypothesis="Maintain pipeline testing on LinkedIn while 30-day window finishes.",
                    audience="VP Finance mid-market",
                    message_angle="Case study: 70% reduction in month-end close time",
                    expected_outcome_range=(0, 1),
                    confidence=0.50,
                    evaluation_window_days=30,
                    success_threshold=580.0,
                    reason="Evaluation window remains active; avoiding premature cut.",
                    evidence_used="Analyst HOLD verdict due to incomplete evaluation window.",
                    is_exploration=True
                ),
                Allocation(
                    channel=Channel.META,
                    experiment_id=f"EXP-0{cycle_id}-META",
                    current_budget=300.0 if cycle_id == 2 else 200.0,
                    proposed_budget=200.0,
                    proposed_share=0.10,
                    hypothesis="Testing tight retargeting only to reduce wasted spend.",
                    audience="High-intent past visitors",
                    message_angle="Customer testimonial video",
                    expected_outcome_range=(0, 1),
                    confidence=0.35,
                    evaluation_window_days=14,
                    success_threshold=750.0,
                    reason="Reducing allocation due to high observed CAC.",
                    evidence_used="Observed CAC above $800 in prior cycle.",
                    is_exploration=True
                ),
                Allocation(
                    channel=Channel.COLD_EMAIL,
                    experiment_id=f"EXP-0{cycle_id}-COLD",
                    current_budget=300.0,
                    proposed_budget=300.0,
                    proposed_share=0.15,
                    hypothesis="Maintain steady outbound pacing to avoid list saturation.",
                    audience="Controllers at Series A-C SaaS companies",
                    message_angle="Benchmark report: Average days to close by company size",
                    expected_outcome_range=(1, 2),
                    confidence=0.65,
                    evaluation_window_days=14,
                    success_threshold=400.0,
                    reason="Consistent performance within target CAC.",
                    evidence_used="Stable conversion rate in prior cycle.",
                    is_exploration=False
                ),
                Allocation(
                    channel=Channel.FOUNDER_CONTENT,
                    experiment_id=f"EXP-0{cycle_id}-FNDR",
                    current_budget=500.0,
                    proposed_budget=500.0 if cycle_id == 2 else 300.0,
                    proposed_share=0.25 if cycle_id == 2 else 0.15,
                    hypothesis="Testing founder teardowns of public S-1 accounting disclosures.",
                    audience="Finance executives",
                    message_angle="Deep dive: How tech unicorns manage multi-subsidiary close",
                    expected_outcome_range=(0, 1),
                    confidence=0.45,
                    evaluation_window_days=28,
                    success_threshold=650.0,
                    reason="Continuing to monitor founder content; high lag expected.",
                    evidence_used="Analyst noted high observed CAC but window was still ongoing.",
                    is_exploration=True
                )
            ]
            summary = f"Cycle {cycle_id} Portfolio: Progressively scaling Google Search while managing exploratory channels."
        else:
            # Cycle 4 & 5: The Hackathon Demonstration Moment!
            # The Strategist explicitly challenges the founder's initial bias with evidence!
            allocs = [
                Allocation(
                    channel=Channel.GOOGLE_SEARCH,
                    experiment_id=f"EXP-0{cycle_id}-GOOG",
                    current_budget=800.0,
                    proposed_budget=1100.0,
                    proposed_share=0.55,
                    hypothesis="Scale Google Search to become primary growth engine while expanding to high-volume secondary keywords.",
                    audience="Finance decision makers actively searching solutions",
                    message_angle="Automate reconciliations in 48 hours — LedgerAI",
                    expected_outcome_range=(3, 4),
                    confidence=0.90,
                    evaluation_window_days=14,
                    success_threshold=350.0,
                    reason="Google Search is our clear winner, consistently generating qualified demos at ~$310 CAC.",
                    evidence_used="4 consecutive cycles of verified conversion data in Experiment Ledger.",
                    is_exploration=False
                ),
                Allocation(
                    channel=Channel.LINKEDIN,
                    experiment_id=f"EXP-0{cycle_id}-LINK",
                    current_budget=400.0,
                    proposed_budget=300.0,
                    proposed_share=0.15,
                    hypothesis="Maintain targeted ABM campaign for top 100 enterprise accounts.",
                    audience="Named enterprise account list",
                    message_angle="CFO case study ROI breakdown",
                    expected_outcome_range=(0, 1),
                    confidence=0.55,
                    evaluation_window_days=30,
                    success_threshold=580.0,
                    reason="Evaluation window concluded with moderate pipeline generation.",
                    evidence_used="Analyst verdict HOLD with positive leading indicators.",
                    is_exploration=True
                ),
                Allocation(
                    channel=Channel.META,
                    experiment_id=f"EXP-0{cycle_id}-META",
                    current_budget=200.0,
                    proposed_budget=100.0,
                    proposed_share=0.05,
                    hypothesis="Low-cost maintenance retargeting pool.",
                    audience="Demo page dropoffs",
                    message_angle="Limited pilot onboarding offer",
                    expected_outcome_range=(0, 1),
                    confidence=0.30,
                    evaluation_window_days=14,
                    success_threshold=750.0,
                    reason="Minimizing spend on poor performing channel to preserve capital.",
                    evidence_used="Analyst verdict CUT/REDUCE due to persistent sub-par conversion.",
                    is_exploration=True
                ),
                Allocation(
                    channel=Channel.COLD_EMAIL,
                    experiment_id=f"EXP-0{cycle_id}-COLD",
                    current_budget=300.0,
                    proposed_budget=300.0,
                    proposed_share=0.15,
                    hypothesis="Maintain outbound rhythm on verified CFO contacts.",
                    audience="Controllers in mid-market SaaS",
                    message_angle="Audit readiness automation",
                    expected_outcome_range=(1, 2),
                    confidence=0.70,
                    evaluation_window_days=14,
                    success_threshold=400.0,
                    reason="Reliable steady contributor to pipeline.",
                    evidence_used="Steady CAC across past cycles in ledger.",
                    is_exploration=False
                ),
                Allocation(
                    channel=Channel.FOUNDER_CONTENT,
                    experiment_id=f"EXP-0{cycle_id}-FNDR",
                    current_budget=300.0,
                    proposed_budget=200.0,
                    proposed_share=0.10,
                    hypothesis="Retain small experimental presence for founder video clips while reallocating bulk budget to Google.",
                    audience="Finance executives",
                    message_angle="Quick 60-second reconciliation tips",
                    expected_outcome_range=(0, 1),
                    confidence=0.35,
                    evaluation_window_days=28,
                    success_threshold=650.0,
                    reason=(
                        "You asked us to prioritise founder-led content. After four cycles, it is producing "
                        "qualified demos at approximately 3x the cost of Google Search (observed CAC >$1,800 vs $310). "
                        "We recommend reducing content from 25% to 10% and reallocating the difference to Google "
                        "while retaining a smaller test budget."
                    ),
                    evidence_used="Analyst verdict CUT on founder content; 4 cycles of empirical CAC data.",
                    is_exploration=True
                )
            ]
            summary = (
                "Strategic Reallocation: Challenging initial founder preference based on 4 cycles of evidence. "
                "Founder Content reduced to 10% due to ~3x higher CAC than Google Search ($1,800+ vs $310). "
                "Capital scaled aggressively into Google Search (55%) to drive maximum qualified demo volume."
            )

        return ExperimentPlan(
            cycle_id=cycle_id,
            total_budget=total,
            primary_goal="Qualified Demo Bookings",
            allocations=allocs,
            exploration_budget_pct=round(sum(a.proposed_share for a in allocs if a.is_exploration), 2),
            exploitation_budget_pct=round(sum(a.proposed_share for a in allocs if not a.is_exploration), 2),
            strategy_summary=summary,
            major_uncertainties=[
                "Diminishing returns threshold on Google Search at scale",
                "Long-tail conversion lag on LinkedIn enterprise accounts"
            ]
        )

    def _generate_analysis(self, cycle_id: int) -> AnalysisReport:
        if cycle_id <= 2:
            verdicts = [
                ExperimentVerdict(
                    channel=Channel.GOOGLE_SEARCH,
                    experiment_id=f"EXP-0{cycle_id}-GOOG",
                    verdict=Verdict.SCALE,
                    confidence=0.80,
                    observed_cost_per_outcome=310.0,
                    target_cost_per_outcome=350.0,
                    evidence_count=2,
                    evaluation_window_complete=True,
                    reasoning_summary="Observed CAC ($310) outperformed target ($350) with strong search click-through rate.",
                    recommended_budget_direction="INCREASE",
                    learning="High-intent search terms for automated reconciliation are converting efficiently."
                ),
                ExperimentVerdict(
                    channel=Channel.LINKEDIN,
                    experiment_id=f"EXP-0{cycle_id}-LINK",
                    verdict=Verdict.HOLD,
                    confidence=0.40,
                    observed_cost_per_outcome=500.0,
                    target_cost_per_outcome=580.0,
                    evidence_count=1,
                    evaluation_window_complete=False,
                    reasoning_summary="Evaluation window requires 30 days; only 14 days elapsed. Protecting against premature cut.",
                    recommended_budget_direction="MAINTAIN",
                    learning="Enterprise engagement is registering, but sales cycle requires multi-touch attribution window."
                ),
                ExperimentVerdict(
                    channel=Channel.META,
                    experiment_id=f"EXP-0{cycle_id}-META",
                    verdict=Verdict.HOLD,
                    confidence=0.50,
                    observed_cost_per_outcome=850.0,
                    target_cost_per_outcome=750.0,
                    evidence_count=0,
                    evaluation_window_complete=True,
                    reasoning_summary="High impressions and cheap clicks, but low landing page demo conversion.",
                    recommended_budget_direction="DECREASE",
                    learning="Meta traffic shows low purchase intent for enterprise finance software."
                ),
                ExperimentVerdict(
                    channel=Channel.COLD_EMAIL,
                    experiment_id=f"EXP-0{cycle_id}-COLD",
                    verdict=Verdict.HOLD,
                    confidence=0.70,
                    observed_cost_per_outcome=380.0,
                    target_cost_per_outcome=400.0,
                    evidence_count=1,
                    evaluation_window_complete=True,
                    reasoning_summary="Steady conversion within target range; good secondary channel.",
                    recommended_budget_direction="MAINTAIN",
                    learning="Personalized cold email to controllers yields predictable response rates."
                ),
                ExperimentVerdict(
                    channel=Channel.FOUNDER_CONTENT,
                    experiment_id=f"EXP-0{cycle_id}-FNDR",
                    verdict=Verdict.INSUFFICIENT_DATA,
                    confidence=0.30,
                    observed_cost_per_outcome=1800.0,
                    target_cost_per_outcome=650.0,
                    evidence_count=0,
                    evaluation_window_complete=False,
                    reasoning_summary="High qualitative engagement (likes/shares), but 0 demo bookings. Window incomplete.",
                    recommended_budget_direction="MAINTAIN",
                    learning="Founder content generates vanity engagement quickly, but direct demo capture requires time."
                )
            ]
            exec_summary = f"Cycle {cycle_id} Analysis: Google Search is an early leader. Founder Content and LinkedIn have incomplete evaluation windows."
        else:
            # Cycle 3, 4, 5: Conclusive evidence emerges
            verdicts = [
                ExperimentVerdict(
                    channel=Channel.GOOGLE_SEARCH,
                    experiment_id=f"EXP-0{cycle_id}-GOOG",
                    verdict=Verdict.SCALE,
                    confidence=0.92,
                    observed_cost_per_outcome=295.0,
                    target_cost_per_outcome=350.0,
                    evidence_count=4,
                    evaluation_window_complete=True,
                    reasoning_summary="Consistently beats target CAC. Search intent yields high demo qualification rate.",
                    recommended_budget_direction="INCREASE",
                    learning="Category search is the primary high-ROI engine for Seed B2B SaaS."
                ),
                ExperimentVerdict(
                    channel=Channel.LINKEDIN,
                    experiment_id=f"EXP-0{cycle_id}-LINK",
                    verdict=Verdict.HOLD,
                    confidence=0.65,
                    observed_cost_per_outcome=620.0,
                    target_cost_per_outcome=580.0,
                    evidence_count=1,
                    evaluation_window_complete=True,
                    reasoning_summary="Completed 30-day window. Delivers qualified demos but at higher unit cost.",
                    recommended_budget_direction="MAINTAIN",
                    learning="LinkedIn serves well for ABM brand reinforcement rather than primary acquisition."
                ),
                ExperimentVerdict(
                    channel=Channel.META,
                    experiment_id=f"EXP-0{cycle_id}-META",
                    verdict=Verdict.CUT,
                    confidence=0.85,
                    observed_cost_per_outcome=1100.0,
                    target_cost_per_outcome=750.0,
                    evidence_count=0,
                    evaluation_window_complete=True,
                    reasoning_summary="Persistent high CAC (> $1,000) over multiple cycles. Unsuitable for B2B finance demos.",
                    recommended_budget_direction="PAUSE",
                    learning="Broad consumer social ads fail to convert CFOs for core accounting platforms."
                ),
                ExperimentVerdict(
                    channel=Channel.COLD_EMAIL,
                    experiment_id=f"EXP-0{cycle_id}-COLD",
                    verdict=Verdict.HOLD,
                    confidence=0.75,
                    observed_cost_per_outcome=375.0,
                    target_cost_per_outcome=400.0,
                    evidence_count=1,
                    evaluation_window_complete=True,
                    reasoning_summary="Consistently meets target CAC; valuable steady contributor.",
                    recommended_budget_direction="MAINTAIN",
                    learning="Cold email maintains steady unit economics at sub-$400 CAC."
                ),
                ExperimentVerdict(
                    channel=Channel.FOUNDER_CONTENT,
                    experiment_id=f"EXP-0{cycle_id}-FNDR",
                    verdict=Verdict.CUT,
                    confidence=0.88,
                    observed_cost_per_outcome=1850.0,
                    target_cost_per_outcome=650.0,
                    evidence_count=0,
                    evaluation_window_complete=True,
                    reasoning_summary=(
                        "Evaluation window complete. Over 4 cycles, observed CAC ($1,850) is approximately 3x higher "
                        "than Google Search and far exceeds target CAC ($650). Recommend reducing allocation."
                    ),
                    recommended_budget_direction="DECREASE",
                    learning="Founder-led content is ineffective as a primary acquisition channel for immediate demo conversions."
                )
            ]
            exec_summary = (
                f"Cycle {cycle_id} Analysis: Conclusive evidence supports scaling Google Search and reducing "
                "Founder Content. Soft founder preference has been empirically tested and challenged."
            )

        return AnalysisReport(
            cycle_id=cycle_id,
            verdicts=verdicts,
            executive_summary=exec_summary,
            primary_bottleneck="Creative format on social channels vs High intent on search",
            recommended_explore_ratio=0.15
        )


class StubBaseChatModel:
    """Mock base model mimicking LangChain BaseChatModel interface for local stub usage."""

    def __init__(self, agent_type: str = "default"):
        self.agent_type = agent_type

    def with_structured_output(self, schema: Type[BaseModel]) -> StubStructuredModel:
        return StubStructuredModel(self.agent_type, schema)

    def invoke(self, messages: Any, **kwargs: Any) -> AIMessage:
        return AIMessage(content=f"Stub response for {self.agent_type}")


def _resolve_model_id(agent_type: str) -> str:
    """Map an agent type to its configured Bedrock model id (config-driven, never constructed)."""
    if agent_type == "strategist":
        return settings.bedrock_strategist_model
    if agent_type == "analyst":
        if settings.analyst_use_escalation:
            return settings.bedrock_analyst_escalation_model
        return settings.bedrock_analyst_model
    if agent_type == "content":
        if settings.content_use_escalation:
            return settings.bedrock_content_escalation_model
        return settings.bedrock_content_model
    return settings.bedrock_default_model


class ModelFactory:
    """Central factory for instantiating Bedrock or Stub LLM instances."""

    @staticmethod
    def get_model(agent_type: str = "default") -> Any:
        # If offline testing requested or credentials unavailable, return high-fidelity stub
        if settings.use_stub_models:
            return StubBaseChatModel(agent_type=agent_type)

        if _resolve_model_id(agent_type).startswith('amazon.nova'):
            from traction.bedrock_json import BedrockJsonModel
            return BedrockJsonModel(_resolve_model_id(agent_type))

        # Attempt to use real AWS Bedrock ChatBedrockConverse. boto3's default
        # credential chain (env vars / shared profile / instance role) is used;
        # no keys are ever prompted for or cached here.
        try:
            from langchain_aws import ChatBedrockConverse

            return ChatBedrockConverse(
                model=_resolve_model_id(agent_type),
                region_name=settings.aws_default_region,
                credentials_profile_name=settings.aws_profile,
                temperature=0.0,
            )
        except Exception as exc:
            raise RuntimeError(f"Bedrock model initialization failed for {agent_type}") from exc

    @staticmethod
    def bedrock_credentials_available() -> bool:
        """Best-effort check for usable AWS credentials via boto3's default chain.

        Returns False when offline-stub mode is forced or no credentials resolve,
        so callers can pick the deterministic Stub agent without raising.
        """
        if settings.use_stub_models:
            return False
        try:  # pragma: no cover - depends on ambient AWS environment
            import boto3

            creds = boto3.Session(profile_name=settings.aws_profile).get_credentials()
            return creds is not None
        except Exception:  # pragma: no cover
            return False


def get_strategist_model() -> Any:
    return ModelFactory.get_model("strategist")


def get_analyst_model() -> Any:
    return ModelFactory.get_model("analyst")


def get_default_model() -> Any:
    return ModelFactory.get_model("default")


def get_content_model() -> Any:
    return ModelFactory.get_model("content")


def get_analyst_structured_model(schema: Type[BaseModel] = AnalysisReport) -> Any:
    """Return a structured-output client for the Analyst.

    Wraps the configured Bedrock model (or the offline stub) with
    ``with_structured_output(schema)`` so callers get validated Pydantic objects.
    Infra-agnostic: no long-lived state, safe to build per invocation / cold start.
    """
    return get_analyst_model().with_structured_output(schema)


def get_content_structured_model(schema: Type[BaseModel]) -> Any:
    """Structured-output client for the Content Generator (see ``get_analyst_structured_model``)."""
    return get_content_model().with_structured_output(schema)
