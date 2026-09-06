"""Abstract repository interface for persistent organizational memory."""

from abc import ABC, abstractmethod
from typing import Optional
from traction.schemas.experiment import Channel, ExperimentPlan
from traction.schemas.result import ExperimentResult
from traction.schemas.analysis import AnalysisReport
from traction.schemas.ledger import LedgerEntry, HistoricalSummary, FailedHypothesis


class ExperimentLedgerRepository(ABC):
    """Abstract interface for the startup experiment ledger."""

    @abstractmethod
    def append_plan(self, startup_id: str, plan: ExperimentPlan) -> None:
        """Record an approved experiment plan."""
        pass

    @abstractmethod
    def append_results(self, startup_id: str, cycle_id: int, results: list[ExperimentResult]) -> None:
        """Record normalized experiment results."""
        pass

    @abstractmethod
    def append_analysis(self, startup_id: str, report: AnalysisReport) -> None:
        """Record Analyst verdicts and learnings."""
        pass

    @abstractmethod
    def get_startup_history(self, startup_id: str) -> list[LedgerEntry]:
        """Retrieve complete historical ledger entries for a startup."""
        pass

    @abstractmethod
    def get_channel_history(self, startup_id: str, channel: Channel) -> list[LedgerEntry]:
        """Retrieve historical ledger entries filtered by channel."""
        pass

    @abstractmethod
    def get_recent_learnings(self, startup_id: str, limit: int = 5) -> list[str]:
        """Retrieve the most recent distinct learnings to guide future planning."""
        pass

    @abstractmethod
    def get_prior_failed_hypotheses(self, startup_id: str) -> list[FailedHypothesis]:
        """Retrieve hypotheses that failed / resulted in CUT verdicts."""
        pass

    @abstractmethod
    def get_historical_summary(self, startup_id: str) -> HistoricalSummary:
        """Generate a compact historical summary for agent context injection."""
        pass
