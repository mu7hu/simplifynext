"""DynamoDB-backed implementation of the Experiment Ledger.

The SQLite repository remains the default for local development.  This adapter
implements the same repository contract for stateless Lambda functions.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key

from augury.ledger.base import ExperimentLedgerRepository
from augury.schemas.analysis import AnalysisReport, Verdict
from augury.schemas.experiment import Channel, ExperimentPlan
from augury.schemas.ledger import FailedHypothesis, HistoricalSummary, LedgerEntry
from augury.schemas.result import ExperimentResult


class DynamoDBExperimentLedger(ExperimentLedgerRepository):
    """Ledger repository using a DynamoDB table keyed by startup and entry."""

    def __init__(
        self,
        table_name: str,
        *,
        region_name: str | None = None,
        table: Any = None,
    ):
        self.table = table or boto3.resource("dynamodb", region_name=region_name).Table(table_name)

    @staticmethod
    def _key(startup_id: str, cycle_id: int, channel: Channel | str) -> dict[str, str]:
        channel_value = channel.value if isinstance(channel, Channel) else str(channel)
        return {"startup_id": startup_id, "entry_key": f"cycle#{cycle_id}#{channel_value}"}

    @staticmethod
    def _ddb_value(value: Any) -> Any:
        """Convert JSON/Pydantic numbers to DynamoDB-safe numeric values."""
        if isinstance(value, float):
            return Decimal(str(value))
        if isinstance(value, list):
            return [DynamoDBExperimentLedger._ddb_value(item) for item in value]
        if isinstance(value, dict):
            return {key: DynamoDBExperimentLedger._ddb_value(item) for key, item in value.items()}
        return value

    @staticmethod
    def _item_to_entry(item: dict[str, Any]) -> LedgerEntry:
        return LedgerEntry(
            id=None,
            startup_id=item["startup_id"],
            cycle_id=int(item["cycle_id"]),
            channel=Channel(item["channel"]),
            experiment_id=item["experiment_id"],
            hypothesis=item.get("hypothesis", ""),
            audience=item.get("audience", ""),
            message_angle=item.get("message_angle", ""),
            planned_budget=float(item.get("planned_budget", 0.0)),
            actual_spend=float(item.get("actual_spend", 0.0)),
            primary_outcomes=int(item.get("primary_outcomes", 0)),
            observed_cac=float(item.get("observed_cac", 0.0)),
            verdict=Verdict(item.get("verdict", Verdict.INSUFFICIENT_DATA.value)),
            confidence=float(item.get("confidence", 0.0)),
            learning=item.get("learning", ""),
            timestamp=item.get("timestamp", ""),
        )

    def _update(self, startup_id: str, cycle_id: int, channel: Channel, values: dict[str, Any]) -> None:
        names = {f"#{name}": name for name in values}
        assignments = ", ".join(f"{alias} = :{name}" for alias, name in names.items())
        expression_values = {
            f":{name}": self._ddb_value(value) for name, value in values.items()
        }
        self.table.update_item(
            Key=self._key(startup_id, cycle_id, channel),
            UpdateExpression=f"SET {assignments}",
            ExpressionAttributeNames=names,
            ExpressionAttributeValues=expression_values,
        )

    def append_plan(self, startup_id: str, plan: ExperimentPlan) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        for allocation in plan.allocations:
            self.table.update_item(
                Key=self._key(startup_id, plan.cycle_id, allocation.channel),
                UpdateExpression=(
                    "SET cycle_id = :cycle, channel = :channel, experiment_id = :experiment, "
                    "hypothesis = :hypothesis, audience = :audience, message_angle = :angle, "
                    "planned_budget = :budget, #timestamp = if_not_exists(#timestamp, :timestamp), "
                    "actual_spend = if_not_exists(actual_spend, :zero), "
                    "primary_outcomes = if_not_exists(primary_outcomes, :zero), "
                    "observed_cac = if_not_exists(observed_cac, :zero), "
                    "verdict = if_not_exists(verdict, :insufficient), "
                    "confidence = if_not_exists(confidence, :zero), "
                    "learning = if_not_exists(learning, :empty)"
                ),
                ExpressionAttributeNames={"#timestamp": "timestamp"},
                ExpressionAttributeValues={
                    ":cycle": plan.cycle_id,
                    ":channel": allocation.channel.value,
                    ":experiment": allocation.experiment_id,
                    ":hypothesis": allocation.hypothesis,
                    ":audience": allocation.audience,
                    ":angle": allocation.message_angle,
                    ":budget": self._ddb_value(allocation.proposed_budget),
                    ":timestamp": timestamp,
                    ":zero": 0,
                    ":insufficient": Verdict.INSUFFICIENT_DATA.value,
                    ":empty": "",
                },
            )

    def append_results(self, startup_id: str, cycle_id: int, results: list[ExperimentResult]) -> None:
        for result in results:
            self._update(startup_id, cycle_id, result.channel, {
                "actual_spend": result.spend,
                "primary_outcomes": result.primary_outcomes,
                "observed_cac": result.observed_cac,
                "raw_data_json": result.model_dump_json(),
            })

    def append_analysis(self, startup_id: str, report: AnalysisReport) -> None:
        for verdict in report.verdicts:
            self._update(startup_id, report.cycle_id, verdict.channel, {
                "verdict": verdict.verdict.value,
                "confidence": verdict.confidence,
                "learning": verdict.learning,
            })

    def get_startup_history(self, startup_id: str) -> list[LedgerEntry]:
        response = self.table.query(
            KeyConditionExpression=Key("startup_id").eq(startup_id)
        )
        items = list(response.get("Items", []))
        while response.get("LastEvaluatedKey"):
            response = self.table.query(
                KeyConditionExpression=Key("startup_id").eq(startup_id),
                ExclusiveStartKey=response["LastEvaluatedKey"],
            )
            items.extend(response.get("Items", []))
        return sorted((self._item_to_entry(i) for i in items), key=lambda e: (e.cycle_id, e.channel.value))

    def get_channel_history(self, startup_id: str, channel: Channel) -> list[LedgerEntry]:
        return [entry for entry in self.get_startup_history(startup_id) if entry.channel == channel]

    def get_recent_learnings(self, startup_id: str, limit: int = 5) -> list[str]:
        seen: set[str] = set()
        learnings: list[str] = []
        for entry in reversed(self.get_startup_history(startup_id)):
            if entry.learning and entry.learning not in seen:
                seen.add(entry.learning)
                learnings.append(entry.learning)
            if len(learnings) >= limit:
                break
        return learnings

    def get_prior_failed_hypotheses(self, startup_id: str) -> list[FailedHypothesis]:
        return [
            FailedHypothesis(
                channel=entry.channel,
                cycle_id=entry.cycle_id,
                hypothesis=entry.hypothesis,
                reason_failed="Exceeded CAC tolerance / poor conversion",
                learning=entry.learning,
            )
            for entry in reversed(self.get_startup_history(startup_id))
            if entry.verdict == Verdict.CUT
        ]

    def get_historical_summary(self, startup_id: str) -> HistoricalSummary:
        history = self.get_startup_history(startup_id)
        if not history:
            return HistoricalSummary(
                startup_id=startup_id,
                total_cycles_completed=0,
                total_spend=0.0,
                total_outcomes=0,
                lifetime_cac=0.0,
            )

        total_spend = sum(entry.actual_spend for entry in history)
        total_outcomes = sum(entry.primary_outcomes for entry in history)
        channel_stats: dict[str, dict[str, Any]] = {}
        for channel in Channel:
            entries = [entry for entry in history if entry.channel == channel]
            if entries:
                spend = sum(entry.actual_spend for entry in entries)
                outcomes = sum(entry.primary_outcomes for entry in entries)
                channel_stats[channel.value] = {
                    "total_spend": round(spend, 2),
                    "total_outcomes": outcomes,
                    "avg_cac": round(spend / max(1, outcomes), 2),
                    "last_verdict": entries[-1].verdict.value,
                    "cycles_tested": len(entries),
                }

        return HistoricalSummary(
            startup_id=startup_id,
            total_cycles_completed=max(entry.cycle_id for entry in history),
            total_spend=round(total_spend, 2),
            total_outcomes=total_outcomes,
            lifetime_cac=round(total_spend / max(1, total_outcomes), 2),
            channel_lifetime_stats=channel_stats,
            recent_learnings=self.get_recent_learnings(startup_id),
            prior_failed_hypotheses=self.get_prior_failed_hypotheses(startup_id),
        )
