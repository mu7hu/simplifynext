"""Structured observability and event logging for Augury."""

import json
import logging
import sys
import time
from typing import Any, Optional


class StructuredJsonFormatter(logging.Formatter):
    """Formats log records as structured JSON, safe for production and OTEL pipelines."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include custom extra metadata if present
        for key in ["cycle_id", "node", "agent", "latency_ms", "tokens_in", "tokens_out", 
                    "estimated_cost_usd", "verdict", "channel", "error"]:
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry)


def get_logger(name: str = "augury") -> logging.Logger:
    """Obtain a structured logger configured for Augury."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger("augury")
