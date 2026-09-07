"""Standalone AWS Lambda handler for the Analyst Agent.

This module is a *separate deployable service*. It deliberately imports nothing
from ``augury.graph`` / the LangGraph supervisor or any other agent - only the
Analyst, the cross-team schemas, and the model factory. Deploy it as its own
Lambda behind a **Function URL** (no API Gateway required).

Request payload (JSON, either the raw body of a Function URL request or a direct
dict invocation)::

    {
      "cycle_id": 3,
      "plan": { ...ExperimentPlan... },
      "results": [ { ...ExperimentResult... }, ... ],
      "benchmark_priors": [ { ...BenchmarkPrior... }, ... ]
    }

Response: HTTP-shaped dict ``{"statusCode": int, "headers": {...}, "body": str}``
where ``body`` is the ``AnalysisReport`` as JSON on success (200), a validation
error report on bad input (422), or an error message on an unexpected failure
(400 for malformed JSON, 500 otherwise).

Local invocation examples
-------------------------
CLI (no AWS needed)::

    python scripts/run_analyst.py path/to/payload.json

Direct handler call (see ``tests/test_analyst_lambda.py``)::

    from augury.api.analyst_lambda import handler
    handler({"body": json.dumps(payload)}, None)

curl against a deployed Function URL::

    curl -sS -X POST "$ANALYST_FUNCTION_URL" \
      -H 'content-type: application/json' \
      --data @payload.json
"""

from __future__ import annotations

import base64
import json
from typing import Any

from pydantic import ValidationError

from augury.agents.analyst import AnalystAgent, BedrockAnalystAgent
from augury.schemas.experiment import ExperimentPlan
from augury.schemas.result import ExperimentResult
from augury.schemas.profile import BenchmarkPrior
from augury.schemas.analysis import AnalysisReport

_JSON_HEADERS = {"content-type": "application/json"}


def _build_agent() -> AnalystAgent:
    """Always the real Analyst: Bedrock reasoning when AWS credentials resolve,
    otherwise its deterministic rule engine analysing the actual payload. (The
    scripted ``StubAnalystAgent`` is intentionally never used here - a standalone
    service must analyse its input, not emit a canned narrative.)"""
    return BedrockAnalystAgent()


def _response(status: int, payload: dict[str, Any] | str) -> dict[str, Any]:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return {"statusCode": status, "headers": dict(_JSON_HEADERS), "body": body}


def _extract_payload(event: Any) -> dict[str, Any]:
    """Accept a Function URL event, an API-GW event, or a direct payload dict."""
    if isinstance(event, (bytes, bytearray, str)):
        return json.loads(event)
    if not isinstance(event, dict):
        raise ValueError("event must be a dict or JSON string")

    if "body" in event and not any(k in event for k in ("cycle_id", "plan")):
        raw = event.get("body")
        if raw is None or raw == "":
            raise ValueError("request body is empty")
        if event.get("isBase64Encoded"):
            raw = base64.b64decode(raw).decode("utf-8")
        if isinstance(raw, (bytes, bytearray)):
            raw = raw.decode("utf-8")
        return json.loads(raw) if isinstance(raw, str) else raw

    return event


def analyze_payload(payload: dict[str, Any]) -> AnalysisReport:
    """Validate a raw payload into schemas and run the Analyst. Raises ValidationError/KeyError."""
    if "plan" not in payload:
        raise KeyError("plan")
    cycle_id = int(payload.get("cycle_id") or payload["plan"].get("cycle_id", 1))
    plan = ExperimentPlan.model_validate(payload["plan"])
    results = [ExperimentResult.model_validate(r) for r in payload.get("results", [])]
    priors = [BenchmarkPrior.model_validate(p) for p in payload.get("benchmark_priors", [])]

    agent = _build_agent()
    return agent.analyze_cycle(cycle_id=cycle_id, plan=plan, results=results, benchmark_priors=priors)


def handler(event: Any, context: Any = None) -> dict[str, Any]:  # noqa: ARG001 - Lambda signature
    """AWS Lambda entrypoint (Function URL friendly)."""
    try:
        payload = _extract_payload(event)
    except (json.JSONDecodeError, ValueError) as exc:
        return _response(400, {"error": "invalid_request", "detail": str(exc)})

    try:
        report = analyze_payload(payload)
    except KeyError as exc:
        return _response(422, {"error": "schema_validation_error", "detail": f"missing field: {exc}"})
    except ValidationError as exc:
        return _response(422, {"error": "schema_validation_error", "detail": json.loads(exc.json())})
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return _response(500, {"error": "analyst_failure", "detail": str(exc)})

    return _response(200, report.model_dump_json())


# Alias so either name works as the Lambda "Handler" setting.
lambda_handler = handler
