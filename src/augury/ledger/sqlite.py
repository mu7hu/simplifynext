"""SQLite implementation of the persistent Experiment Ledger."""

import json
import os
import sqlite3
from typing import Optional
from augury.ledger.base import ExperimentLedgerRepository
from augury.schemas.experiment import Channel, ExperimentPlan
from augury.schemas.result import ExperimentResult
from augury.schemas.analysis import AnalysisReport, Verdict
from augury.schemas.ledger import LedgerEntry, HistoricalSummary, FailedHypothesis


class SQLiteExperimentLedger(ExperimentLedgerRepository):
    """Persistent SQLite-backed repository for the Experiment Ledger."""

    def __init__(self, db_path: str = "data/augury.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ledger_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    startup_id TEXT NOT NULL,
                    cycle_id INTEGER NOT NULL,
                    channel TEXT NOT NULL,
                    experiment_id TEXT NOT NULL,
                    hypothesis TEXT NOT NULL,
                    audience TEXT NOT NULL,
                    message_angle TEXT NOT NULL,
                    planned_budget REAL NOT NULL,
                    actual_spend REAL NOT NULL DEFAULT 0.0,
                    primary_outcomes INTEGER NOT NULL DEFAULT 0,
                    observed_cac REAL NOT NULL DEFAULT 0.0,
                    verdict TEXT NOT NULL DEFAULT 'INSUFFICIENT_DATA',
                    confidence REAL NOT NULL DEFAULT 0.0,
                    learning TEXT NOT NULL DEFAULT '',
                    raw_data_json TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_ledger_startup_cycle 
                ON ledger_entries (startup_id, cycle_id)
            """)
            conn.commit()

    def append_plan(self, startup_id: str, plan: ExperimentPlan) -> None:
        with self._get_connection() as conn:
            for a in plan.allocations:
                # Check if entry already exists for this cycle and channel
                existing = conn.execute(
                    "SELECT id FROM ledger_entries WHERE startup_id = ? AND cycle_id = ? AND channel = ?",
                    (startup_id, plan.cycle_id, a.channel.value)
                ).fetchone()

                from datetime import datetime
                now_iso = datetime.utcnow().isoformat()

                if existing:
                    conn.execute("""
                        UPDATE ledger_entries 
                        SET planned_budget = ?, hypothesis = ?, audience = ?, message_angle = ?, experiment_id = ?
                        WHERE id = ?
                    """, (a.proposed_budget, a.hypothesis, a.audience, a.message_angle, a.experiment_id, existing["id"]))
                else:
                    conn.execute("""
                        INSERT INTO ledger_entries (
                            startup_id, cycle_id, channel, experiment_id, hypothesis, audience, message_angle,
                            planned_budget, actual_spend, primary_outcomes, observed_cac, verdict, confidence,
                            learning, raw_data_json, timestamp
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, 0, 0.0, 'INSUFFICIENT_DATA', 0.0, '', ?, ?)
                    """, (
                        startup_id, plan.cycle_id, a.channel.value, a.experiment_id, a.hypothesis,
                        a.audience, a.message_angle, a.proposed_budget, json.dumps(a.model_dump()), now_iso
                    ))
            conn.commit()

    def append_results(self, startup_id: str, cycle_id: int, results: list[ExperimentResult]) -> None:
        with self._get_connection() as conn:
            for r in results:
                conn.execute("""
                    UPDATE ledger_entries 
                    SET actual_spend = ?, primary_outcomes = ?, observed_cac = ?,
                        raw_data_json = ?
                    WHERE startup_id = ? AND cycle_id = ? AND channel = ?
                """, (
                    r.spend, r.primary_outcomes, r.observed_cac,
                    json.dumps(r.model_dump()), startup_id, cycle_id, r.channel.value
                ))
            conn.commit()

    def append_analysis(self, startup_id: str, report: AnalysisReport) -> None:
        with self._get_connection() as conn:
            for v in report.verdicts:
                conn.execute("""
                    UPDATE ledger_entries 
                    SET verdict = ?, confidence = ?, learning = ?
                    WHERE startup_id = ? AND cycle_id = ? AND channel = ?
                """, (
                    v.verdict.value, v.confidence, v.learning,
                    startup_id, report.cycle_id, v.channel.value
                ))
            conn.commit()

    def get_startup_history(self, startup_id: str) -> list[LedgerEntry]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM ledger_entries WHERE startup_id = ? ORDER BY cycle_id ASC, channel ASC",
                (startup_id,)
            ).fetchall()

            entries = []
            for r in rows:
                entries.append(LedgerEntry(
                    id=r["id"],
                    startup_id=r["startup_id"],
                    cycle_id=r["cycle_id"],
                    channel=Channel(r["channel"]),
                    experiment_id=r["experiment_id"],
                    hypothesis=r["hypothesis"],
                    audience=r["audience"],
                    message_angle=r["message_angle"],
                    planned_budget=r["planned_budget"],
                    actual_spend=r["actual_spend"],
                    primary_outcomes=r["primary_outcomes"],
                    observed_cac=r["observed_cac"],
                    verdict=Verdict(r["verdict"]),
                    confidence=r["confidence"],
                    learning=r["learning"],
                    timestamp=r["timestamp"]
                ))
            return entries

    def get_channel_history(self, startup_id: str, channel: Channel) -> list[LedgerEntry]:
        all_entries = self.get_startup_history(startup_id)
        return [e for e in all_entries if e.channel == channel]

    def get_recent_learnings(self, startup_id: str, limit: int = 5) -> list[str]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT DISTINCT learning FROM ledger_entries 
                WHERE startup_id = ? AND learning != '' 
                ORDER BY cycle_id DESC, id DESC LIMIT ?
            """, (startup_id, limit)).fetchall()
            return [r["learning"] for r in rows]

    def get_prior_failed_hypotheses(self, startup_id: str) -> list[FailedHypothesis]:
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT channel, cycle_id, hypothesis, learning 
                FROM ledger_entries 
                WHERE startup_id = ? AND verdict = 'CUT'
                ORDER BY cycle_id DESC
            """, (startup_id,)).fetchall()

            return [
                FailedHypothesis(
                    channel=Channel(r["channel"]),
                    cycle_id=r["cycle_id"],
                    hypothesis=r["hypothesis"],
                    reason_failed="Exceeded CAC tolerance / poor conversion",
                    learning=r["learning"]
                )
                for r in rows
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
                channel_lifetime_stats={},
                recent_learnings=[],
                prior_failed_hypotheses=[]
            )

        total_cycles = max(e.cycle_id for e in history)
        total_spend = sum(e.actual_spend for e in history)
        total_outcomes = sum(e.primary_outcomes for e in history)
        lifetime_cac = round(total_spend / max(1, total_outcomes), 2)

        channel_stats: dict[str, dict] = {}
        for c in Channel:
            c_entries = [e for e in history if e.channel == c]
            if c_entries:
                c_spend = sum(e.actual_spend for e in c_entries)
                c_outcomes = sum(e.primary_outcomes for e in c_entries)
                last_verdict = c_entries[-1].verdict.value
                channel_stats[c.value] = {
                    "total_spend": round(c_spend, 2),
                    "total_outcomes": c_outcomes,
                    "avg_cac": round(c_spend / max(1, c_outcomes), 2),
                    "last_verdict": last_verdict,
                    "cycles_tested": len(c_entries)
                }

        return HistoricalSummary(
            startup_id=startup_id,
            total_cycles_completed=total_cycles,
            total_spend=round(total_spend, 2),
            total_outcomes=total_outcomes,
            lifetime_cac=lifetime_cac,
            channel_lifetime_stats=channel_stats,
            recent_learnings=self.get_recent_learnings(startup_id, limit=5),
            prior_failed_hypotheses=self.get_prior_failed_hypotheses(startup_id)
        )
