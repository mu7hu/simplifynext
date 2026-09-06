"""Durable run, event and founder-brief API for the hosted frontend."""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import boto3


TABLE_NAME = os.environ.get("RUN_TABLE_NAME", "")
table = boto3.resource("dynamodb").Table(TABLE_NAME) if TABLE_NAME else None
lambda_client = boto3.client("lambda")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _response(status: int, payload: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": {"content-type": "application/json", "access-control-allow-origin": "*"}, "body": json.dumps(payload, default=str)}


def _body(event: dict[str, Any]) -> dict[str, Any]:
    raw = event.get("body", event)
    return json.loads(raw) if isinstance(raw, str) else raw


def _path(event: dict[str, Any]) -> str:
    return event.get("rawPath") or event.get("requestContext", {}).get("http", {}).get("path", "")


def _run_id() -> str:
    return f"run_{uuid.uuid4().hex[:12]}"


def _get(record_id: str) -> dict[str, Any] | None:
    item = table.get_item(Key={"record_id": record_id}).get("Item") if table else None
    return item


def _put(item: dict[str, Any]) -> None:
    table.put_item(Item=item)


def _start_run(payload: dict[str, Any]) -> dict[str, Any]:
    run_id = _run_id()
    item = {
        "record_id": run_id,
        "kind": "run",
        "run_id": run_id,
        "startup_id": payload.get("startup_id", "ledger_ai"),
        "cycle_id": int(payload.get("cycle_id", 1)),
        "status": "RUNNING",
        "created_at": _now(),
        "updated_at": _now(),
        "events": [{"node": "run_manager", "status": "started", "timestamp": _now(), "message": "Cycle run accepted and queued."}],
    }
    _put(item)
    worker_name = os.environ["RUN_CYCLE_FUNCTION_NAME"]
    worker_payload = {**payload, "run_id": run_id, "auto_approve": bool(payload.get("auto_approve", False))}
    lambda_client.invoke(FunctionName=worker_name, InvocationType="Event", Payload=json.dumps(worker_payload).encode())
    return {"run_id": run_id, "status": item["status"], "cycle_id": item["cycle_id"]}


def _save_brief(startup_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = {"record_id": f"brief#{startup_id}", "kind": "brief", "startup_id": startup_id, "updated_at": _now(), "brief": payload}
    _put(item)
    return {"startup_id": startup_id, "saved": True, "updated_at": item["updated_at"]}


def _approve_run(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = _get(run_id)
    if not item:
        raise KeyError("run_not_found")
    worker_name = os.environ["RUN_CYCLE_FUNCTION_NAME"]
    # Keep the founder's submitted brief across the approval boundary.  The
    # resumed worker is a fresh Lambda invocation and must not silently fall
    # back to the seeded intake brief.
    saved_brief = _get(f"brief#{item.get('startup_id', 'ledger_ai')}")
    founder_brief = (saved_brief or {}).get("brief")
    lambda_client.invoke(
        FunctionName=worker_name,
        InvocationType="Event",
        Payload=json.dumps({
            "run_id": run_id,
            "startup_id": item.get("startup_id", "ledger_ai"),
            "cycle_id": int(item.get("cycle_id", 1)),
            "total_budget": float(payload.get("total_budget", 2000)),
            "auto_approve": True,
            "founder_brief": founder_brief,
            "founder_feedback": payload.get("founder_feedback"),
        }, default=str).encode(),
    )
    table.update_item(Key={"record_id": run_id}, UpdateExpression="SET #status = :status, updated_at = :updated", ExpressionAttributeNames={"#status": "status"}, ExpressionAttributeValues={":status": "RUNNING", ":updated": _now()})
    return {"run_id": run_id, "status": "RUNNING", "message": "Approval accepted; execution resumed."}


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:  # noqa: ARG001
    method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "POST"))
    path = _path(event)
    parts = [p for p in path.split("/") if p]
    try:
        if method == "POST" and parts[-1:] == ["runs"]:
            return _response(202, _start_run(_body(event)))
        if method == "POST" and len(parts) >= 3 and parts[-3] == "runs" and parts[-1] == "approve":
            return _response(202, _approve_run(parts[-2], _body(event)))
        if method == "GET" and len(parts) >= 2 and parts[-2] == "runs":
            item = _get(parts[-1])
            return _response(200, item or {"error": "run_not_found"}) if item else _response(404, {"error": "run_not_found"})
        if method == "GET" and len(parts) >= 3 and parts[-3] == "runs" and parts[-1] == "events":
            item = _get(parts[-2])
            return _response(200, {"run_id": parts[-2], "events": (item or {}).get("events", [])}) if item else _response(404, {"error": "run_not_found"})
        if method in {"PUT", "POST"} and len(parts) >= 2 and parts[-2] == "briefs":
            return _response(200, _save_brief(parts[-1], _body(event)))
        if method == "GET" and len(parts) >= 2 and parts[-2] == "briefs":
            item = _get(f"brief#{parts[-1]}")
            return _response(200, item or {"startup_id": parts[-1], "brief": None})
        return _response(404, {"error": "route_not_found", "path": path})
    except Exception as exc:  # pragma: no cover
        return _response(500, {"error": "run_manager_failure", "detail": str(exc)})


lambda_handler = handler
