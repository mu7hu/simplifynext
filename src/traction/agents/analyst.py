"""Analyst Agent: Evaluates normalized results and issues structured verdicts."""

from abc import ABC, abstractmethod
from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from traction.config import settings
from traction.logging import logger
from traction.models import get_analyst_model
from traction.schemas.experiment import ExperimentPlan
from traction.schemas.result import ExperimentResult
from traction.schemas.profile import BenchmarkPrior
from traction.schemas.analysis import AnalysisReport, ExperimentVerdict, Verdict
from traction.agents.prompts import ANALYST_SYSTEM_PROMPT


class AnalystAgent(ABC):
    """Abstract interface for the Analyst Agent (Teammate's primary ownership area)."""

    @abstractmethod
    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        pass


class StubAnalystAgent(AnalystAgent):
    """High-fidelity working stub for the Analyst Agent so the system runs end-to-end immediately."""

    def __init__(self, model=None):
        self.model = model or get_analyst_model()
        self.structured_model = self.model.with_structured_output(AnalysisReport)

    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        # Pass state to model or stub to generate structured report
        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content=f"Analyze cycle {cycle_id} results across channels.")
        ]
        logger.info(f"Analyst evaluating cycle {cycle_id}", extra={"cycle_id": cycle_id, "agent": "analyst"})
        report = self.structured_model.invoke(messages)
        return report


class LLMAnalystAgent(AnalystAgent):
    """Full LLM Analyst Agent invoking Claude Sonnet / Haiku via AWS Bedrock."""

    def __init__(self, model=None):
        self.model = model or get_analyst_model()
        self.structured_model = self.model.with_structured_output(AnalysisReport)

    def analyze_cycle(
        self,
        cycle_id: int,
        plan: ExperimentPlan,
        results: list[ExperimentResult],
        benchmark_priors: list[BenchmarkPrior]
    ) -> AnalysisReport:
        lines = [
            f"# Performance Data for Cycle {cycle_id}",
            "## Normalized Channel Results:"
        ]
        for r in results:
            lines.append(
                f"- Channel: {r.channel.value} | Spend: ${r.spend:.2f} | Outcomes: {r.primary_outcomes} | "
                f"CAC: ${r.observed_cac:.2f} | Days Observed: {r.days_observed}/{r.evaluation_window_days} "
                f"(Window Complete: {r.is_window_complete})"
            )

        messages = [
            SystemMessage(content=ANALYST_SYSTEM_PROMPT),
            HumanMessage(content="\n".join(lines))
        ]
        logger.info(f"LLM Analyst evaluating cycle {cycle_id}", extra={"cycle_id": cycle_id, "agent": "analyst"})
        return self.structured_model.invoke(messages)
