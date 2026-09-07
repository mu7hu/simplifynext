"""Domain schemas for Augury."""

from augury.schemas.founder import FounderBrief, PrimaryGoal, ChannelPreference, ExclusionRule, GoalType
from augury.schemas.profile import StartupProfile, BenchmarkPrior, StartupStage, IndustrySector
from augury.schemas.experiment import Channel, Allocation, ExperimentPlan
from augury.schemas.result import RawExecutionResult, ExperimentResult
from augury.schemas.analysis import Verdict, ExperimentVerdict, AnalysisReport
from augury.schemas.ledger import LedgerEntry, FailedHypothesis, HistoricalSummary
from augury.schemas.content import (
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
