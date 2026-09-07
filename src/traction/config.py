"""Central configuration and constants for the Traction system."""

import os
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# ---------------------------------------------------------------------------
# Strict Bedrock Model Constants (Read from constants, never dynamically construct)
# ---------------------------------------------------------------------------
BEDROCK_HAIKU_MODEL_ID: str = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
BEDROCK_SONNET_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
# Cheap serverless reasoning options for the Analyst (Amazon Nova family).
BEDROCK_NOVA_MICRO_MODEL_ID: str = "amazon.nova-micro-v1:0"
BEDROCK_NOVA_LITE_MODEL_ID: str = "amazon.nova-lite-v1:0"
DEFAULT_BEDROCK_REGION: str = "ap-southeast-1"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # AWS Configuration
    aws_profile: Optional[str] = Field(default=None, alias="AWS_PROFILE")
    aws_default_region: str = Field(default=DEFAULT_BEDROCK_REGION, alias="AWS_DEFAULT_REGION")
    aws_access_key_id: Optional[str] = Field(default=None, alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: Optional[str] = Field(default=None, alias="AWS_SECRET_ACCESS_KEY")
    aws_session_token: Optional[str] = Field(default=None, alias="AWS_SESSION_TOKEN")

    # Bedrock Model Names
    bedrock_default_model: str = Field(default=BEDROCK_HAIKU_MODEL_ID, alias="BEDROCK_DEFAULT_MODEL")
    bedrock_strategist_model: str = Field(default=BEDROCK_SONNET_MODEL_ID, alias="BEDROCK_STRATEGIST_MODEL")
    # The Analyst defaults to a cheap model (Claude Haiku on Bedrock). Set
    # BEDROCK_ANALYST_MODEL to a Nova id (see BEDROCK_NOVA_*_MODEL_ID) for an even
    # cheaper option, or flip ANALYST_USE_ESCALATION=true to route through
    # BEDROCK_ANALYST_ESCALATION_MODEL when reasoning quality genuinely requires it.
    bedrock_analyst_model: str = Field(default=BEDROCK_HAIKU_MODEL_ID, alias="BEDROCK_ANALYST_MODEL")
    bedrock_analyst_escalation_model: str = Field(
        default=BEDROCK_SONNET_MODEL_ID, alias="BEDROCK_ANALYST_ESCALATION_MODEL"
    )
    analyst_use_escalation: bool = Field(default=False, alias="ANALYST_USE_ESCALATION")
    # Content Generator Agent: cheap model by default; escalate behind a flag.
    bedrock_content_model: str = Field(default=BEDROCK_HAIKU_MODEL_ID, alias="BEDROCK_CONTENT_MODEL")
    bedrock_content_escalation_model: str = Field(
        default=BEDROCK_SONNET_MODEL_ID, alias="BEDROCK_CONTENT_ESCALATION_MODEL"
    )
    content_use_escalation: bool = Field(default=False, alias="CONTENT_USE_ESCALATION")
    content_variants_per_channel: int = Field(default=3, ge=1, le=10, alias="CONTENT_VARIANTS_PER_CHANNEL")

    # Mode: Local Stub / Offline Development
    use_stub_models: bool = Field(default=True, alias="USE_STUB_MODELS")

    # Bounded Loop Guardrails
    max_agent_retries: int = Field(default=2, alias="MAX_AGENT_RETRIES")
    max_graph_iterations: int = Field(default=20, alias="MAX_GRAPH_ITERATIONS")

    # Exploration vs Exploitation Defaults
    default_explore_pct: float = Field(default=0.30, alias="DEFAULT_EXPLORE_PCT")
    min_explore_pct: float = Field(default=0.10, alias="MIN_EXPLORE_PCT")

    # SQLite Persistent Ledger
    ledger_db_path: str = Field(default="data/traction.db", alias="LEDGER_DB_PATH")
    ledger_backend: str = Field(default="sqlite", alias="LEDGER_BACKEND")
    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    aws_data_bucket: Optional[str] = Field(default=None, alias="AWS_DATA_BUCKET")
    dynamodb_ledger_table: Optional[str] = Field(default=None, alias="DYNAMODB_LEDGER_TABLE")


settings = Settings()
