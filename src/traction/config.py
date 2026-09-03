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
    bedrock_analyst_model: str = Field(default=BEDROCK_SONNET_MODEL_ID, alias="BEDROCK_ANALYST_MODEL")

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


settings = Settings()
