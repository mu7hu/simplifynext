"""Domain schemas for Traction."""

from traction.schemas.founder import FounderBrief, PrimaryGoal, ChannelPreference, ExclusionRule, GoalType
from traction.schemas.profile import StartupProfile, BenchmarkPrior, StartupStage, IndustrySector
from traction.schemas.experiment import Channel, Allocation, ExperimentPlan
from traction.schemas.result import RawExecutionResult, ExperimentResult
from traction.schemas.analysis import Verdict, ExperimentVerdict, AnalysisReport
from traction.schemas.ledger import LedgerEntry, FailedHypothesis, HistoricalSummary
from traction.schemas.content import (
    ContentFormat,
    ContentAsset,
    ChannelContent,
    ContentPackage,
    CHANNEL_FORMAT,
)

__all__ = [
    "FounderBrief",
    "PrimaryGoal",
    "ChannelPreference",
    "ExclusionRule",
    "GoalType",
    "StartupProfile",
    "BenchmarkPrior",
    "StartupStage",
    "IndustrySector",
    "Channel",
    "Allocation",
    "ExperimentPlan",
    "RawExecutionResult",
    "ExperimentResult",
    "Verdict",
    "ExperimentVerdict",
    "AnalysisReport",
    "LedgerEntry",
    "FailedHypothesis",
    "HistoricalSummary",
    "ContentFormat",
    "ContentAsset",
    "ChannelContent",
    "ContentPackage",
    "CHANNEL_FORMAT",
]
