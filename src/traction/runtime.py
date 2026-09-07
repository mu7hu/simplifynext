"""Environment-aware dependency factories for local and serverless runtimes."""

from __future__ import annotations

from traction.config import settings
from traction.ledger.base import ExperimentLedgerRepository
from traction.ledger.sqlite import SQLiteExperimentLedger
from traction.services.intake import IntakeProvider, FileIntakeProvider, JsonIntakeProvider
from traction.services.profiler import ProfilerService, FileProfilerService, JsonProfilerService
from traction.storage.json_store import LocalJsonStore, S3JsonStore


def get_runtime_ledger() -> ExperimentLedgerRepository:
    if settings.ledger_backend.lower() == "dynamodb":
        if not settings.dynamodb_ledger_table:
            raise RuntimeError("DYNAMODB_LEDGER_TABLE is required when LEDGER_BACKEND=dynamodb")
        from traction.ledger.dynamodb import DynamoDBExperimentLedger

        return DynamoDBExperimentLedger(settings.dynamodb_ledger_table, region_name=settings.aws_default_region)
    return SQLiteExperimentLedger(settings.ledger_db_path)


def get_runtime_storage():
    if settings.storage_backend.lower() == "s3":
        if not settings.aws_data_bucket:
            raise RuntimeError("AWS_DATA_BUCKET is required when STORAGE_BACKEND=s3")
        return S3JsonStore(settings.aws_data_bucket, region_name=settings.aws_default_region)
    return LocalJsonStore("data")


def get_runtime_intake() -> IntakeProvider:
    storage = get_runtime_storage()
    if settings.storage_backend.lower() == "s3":
        return JsonIntakeProvider(storage)
    return FileIntakeProvider("data/founder_briefs")


def get_runtime_profiler() -> ProfilerService:
    storage = get_runtime_storage()
    if settings.storage_backend.lower() == "s3":
        return JsonProfilerService(storage)
    return FileProfilerService("data/example_profiles", "data/benchmark_priors")
