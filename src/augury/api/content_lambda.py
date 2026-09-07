"""Standalone AWS Lambda handler for the Content Generator Agent.

Same shape as ``augury.api.analyst_lambda``: a separate deployable service that
imports nothing from ``augury.graph`` / the supervisor / other agents. Deploy
behind a **Function URL** (no API Gateway).

Request payload (JSON body of a Function URL request, or a direct dict)::

    {
      "cycle_id": 3,
      "plan": { ...ExperimentPlan... },
      "startup_profile": { ...StartupProfile... },   # optional
      "founder_brief": { ...FounderBrief... },       # optional
      "only_channels": ["GOOGLE_SEARCH", "LINKEDIN"],# optional
      "variants": 3                                   # optional override
    }

Response: ``{"statusCode": int, "headers": {...}, "body": str}`` - ``body`` is the
``ContentPackage`` JSON on success (200); a validation report (422); a bad-JSON
error (400); an unexpected-failure error (500).

Local invocation::

    python scripts/run_content.py path/to/payload.json --pretty

    from augury.api.content_lambda import handler
    handler({"body": json.dumps(payload)}, None)

    curl -sS -X POST "$CONTENT_FUNCTION_URL" -H 'content-type: application/json' --data @payload.json
"""

from __future__ import annotations

import base64
import json
from typing import Any, Optional

from pydantic import ValidationError

from augury.agents.content import ContentGeneratorAgent, BedrockContentGeneratorAgent
from augury.schemas.experiment import Channel, ExperimentPlan
from augury.schemas.profile import StartupProfile
from augury.schemas.founder import FounderBrief
from augury.schemas.content import ContentPackage

_JSON_HEADERS = {"content-type": "application/json"}


def _build_agent(variants: Optional[int] = None) -> ContentGeneratorAgent:
    """The real generator: Bedrock when AWS credentials resolve, deterministic templates otherwise."""
    return BedrockContentGeneratorAgent(variants=variants)


def _response(status: int, payload: dict[str, Any] | str) -> dict[str, Any]:
    body = payload if isinstance(payload, str) else json.dumps(payload)
    return {"statusCode": status, "headers": dict(_JSON_HEADERS), "body": body}


def _extract_payload(event: Any) -> dict[str, Any]:
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


def generate_from_payload(payload: dict[str, Any]) -> ContentPackage:
    """Validate a raw payload into schemas and run the Content Generator."""
    if "plan" not in payload:
        raise KeyError("plan")
    cycle_id = int(payload.get("cycle_id") or payload["plan"].get("cycle_id", 1))
    plan = ExperimentPlan.model_validate(payload["plan"])

    profile = (
        StartupProfile.model_validate(payload["startup_profile"])
        if payload.get("startup_profile") is not None else None
    )
    brief = (
        FounderBrief.model_validate(payload["founder_brief"])
        if payload.get("founder_brief") is not None else None
    )
    only = payload.get("only_channels")
    only_channels = [Channel(c) for c in only] if only else None
    variants = payload.get("variants")

    agent = _build_agent(int(variants) if variants is not None else None)
    return agent.generate_content(
        cycle_id=cycle_id,
        plan=plan,
        startup_profile=profile,
        founder_brief=brief,
        only_channels=only_channels,
    )


def handler(event: Any, context: Any = None) -> dict[str, Any]:  # noqa: ARG001 - Lambda signature
    try:
        payload = _extract_payload(event)
    except (json.JSONDecodeError, ValueError) as exc:
        return _response(400, {"error": "invalid_request", "detail": str(exc)})

    try:
        package = generate_from_payload(payload)
    except KeyError as exc:
        return _response(422, {"error": "schema_validation_error", "detail": f"missing field: {exc}"})
    except (ValidationError,) as exc:
        return _response(422, {"error": "schema_validation_error", "detail": json.loads(exc.json())})
    except ValueError as exc:  # e.g. bad channel name in only_channels
        return _response(422, {"error": "schema_validation_error", "detail": str(exc)})
    except Exception as exc:  # pragma: no cover - defensive
        return _response(500, {"error": "content_failure", "detail": str(exc)})

    return _response(200, package.model_dump_json())


lambda_handler = handler
