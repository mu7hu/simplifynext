"""Tests for the standalone Analyst Lambda handler.

Verifies it is invocable with a plain event, returns a valid AnalysisReport JSON,
emits 4xx payloads on bad input, and has ZERO import coupling to the graph /
orchestration layer at call time.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

from augury.api.analyst_lambda import handler
from augury.schemas.analysis import AnalysisReport, Verdict
from augury.schemas.experiment import Channel

from tests._analyst_fixtures import payload_dict

REPO_ROOT = Path(__file__).resolve().parents[1]


def _parse_ok(response: dict) -> AnalysisReport:
    assert response["statusCode"] == 200, response
    assert response["headers"]["content-type"] == "application/json"
    # body is the report serialized with model_dump_json()
    return AnalysisReport.model_validate_json(response["body"])


def test_handler_function_url_event():
    event = {"body": json.dumps(payload_dict(2)), "requestContext": {"http": {"method": "POST"}}}
    report = _parse_ok(handler(event, None))
    assert report.cycle_id == 2
    assert {v.channel for v in report.verdicts} == {Channel.GOOGLE_SEARCH, Channel.COLD_EMAIL, Channel.FOUNDER_CONTENT}
    # Window protection survives the serialization round-trip.
    fc = next(v for v in report.verdicts if v.channel == Channel.FOUNDER_CONTENT)
    assert fc.verdict == Verdict.INSUFFICIENT_DATA


def test_handler_direct_payload_dict():
    report = _parse_ok(handler(payload_dict(3), None))
    assert report.cycle_id == 3


def test_handler_base64_body():
    import base64

    raw = json.dumps(payload_dict(2)).encode("utf-8")
    event = {"body": base64.b64encode(raw).decode("ascii"), "isBase64Encoded": True}
    _parse_ok(handler(event, None))


def test_handler_malformed_json_returns_400():
    resp = handler({"body": "{not json"}, None)
    assert resp["statusCode"] == 400
    assert json.loads(resp["body"])["error"] == "invalid_request"


def test_handler_schema_validation_returns_422():
    bad = payload_dict(2)
    bad["plan"]["allocations"][0]["proposed_share"] = 5.0  # > 1.0, violates schema
    resp = handler({"body": json.dumps(bad)}, None)
    assert resp["statusCode"] == 422
    assert json.loads(resp["body"])["error"] == "schema_validation_error"


def test_handler_missing_plan_returns_422():
    resp = handler({"body": json.dumps({"cycle_id": 1, "results": []})}, None)
    assert resp["statusCode"] == 422


def test_lambda_has_no_graph_coupling_at_call_time():
    """Import ONLY the lambda module in a fresh interpreter, invoke it, and assert
    that no augury.graph / langgraph module was pulled in."""
    payload_path = REPO_ROOT / "data" / "sample_analyst_payload.json"
    script = textwrap.dedent(
        f"""
        import json, sys
        sys.path.insert(0, {str(REPO_ROOT / "src")!r})
        from augury.api.analyst_lambda import handler
        payload = json.load(open({str(payload_path)!r}))
        resp = handler({{"body": json.dumps(payload)}}, None)
        assert resp["statusCode"] == 200, resp
        leaked = sorted(m for m in sys.modules if m == "augury.graph" or m.startswith("augury.graph.") or m == "langgraph" or m.startswith("langgraph."))
        assert not leaked, f"graph/orchestration modules leaked into the lambda runtime: {{leaked}}"
        print("OK")
        """
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "OK" in proc.stdout
