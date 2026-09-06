"""Tests for the standalone Content Generator Lambda handler."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

from traction.api.content_lambda import handler
from traction.schemas.content import ContentPackage
from traction.schemas.experiment import Channel

from tests._analyst_fixtures import sample_plan

REPO_ROOT = Path(__file__).resolve().parents[1]


def _payload(cycle_id=2, **extra):
    p = {"cycle_id": cycle_id, "plan": sample_plan(cycle_id).model_dump(mode="json")}
    p.update(extra)
    return p


def _ok(resp) -> ContentPackage:
    assert resp["statusCode"] == 200, resp
    assert resp["headers"]["content-type"] == "application/json"
    return ContentPackage.model_validate_json(resp["body"])


def test_handler_function_url_event():
    pkg = _ok(handler({"body": json.dumps(_payload(2))}, None))
    assert pkg.cycle_id == 2
    assert {i.channel for i in pkg.items} == {a.channel for a in sample_plan().allocations}
    assert all(i.assets for i in pkg.items)


def test_handler_direct_payload_and_only_channels():
    pkg = _ok(handler(_payload(3, only_channels=["GOOGLE_SEARCH"], variants=2), None))
    assert pkg.cycle_id == 3
    assert [i.channel for i in pkg.items] == [Channel.GOOGLE_SEARCH]
    assert len(pkg.items[0].assets) == 2


def test_handler_missing_plan_returns_422():
    resp = handler({"body": json.dumps({"cycle_id": 1})}, None)
    assert resp["statusCode"] == 422
    assert json.loads(resp["body"])["error"] == "schema_validation_error"


def test_handler_bad_channel_returns_422():
    resp = handler(_payload(2, only_channels=["NOT_A_CHANNEL"]), None)
    assert resp["statusCode"] == 422


def test_handler_malformed_json_returns_400():
    resp = handler({"body": "{oops"}, None)
    assert resp["statusCode"] == 400


def test_content_lambda_has_no_graph_coupling_at_call_time():
    payload_path = REPO_ROOT / "data" / "sample_content_payload.json"
    script = textwrap.dedent(
        f"""
        import json, sys
        sys.path.insert(0, {str(REPO_ROOT / "src")!r})
        from traction.api.content_lambda import handler
        payload = json.load(open({str(payload_path)!r}))
        resp = handler({{"body": json.dumps(payload)}}, None)
        assert resp["statusCode"] == 200, resp
        leaked = sorted(m for m in sys.modules if m == "traction.graph" or m.startswith("traction.graph.")
                        or m == "langgraph" or m.startswith("langgraph."))
        assert not leaked, f"graph modules leaked into the content lambda runtime: {{leaked}}"
        print("OK")
        """
    )
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    assert "OK" in proc.stdout
