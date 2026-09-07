"""Small JSON object store abstraction used by intake and profiling services."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol

import boto3


class JsonStore(Protocol):
    def get_json(self, key: str) -> Any:
        ...


class LocalJsonStore:
    def __init__(self, root: str = "data"):
        self.root = Path(root)

    def get_json(self, key: str) -> Any:
        with (self.root / key).open("r", encoding="utf-8") as handle:
            return json.load(handle)


class S3JsonStore:
    def __init__(self, bucket: str, *, prefix: str = "", region_name: str | None = None, client: Any = None):
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = client or boto3.client("s3", region_name=region_name)

    def get_json(self, key: str) -> Any:
        object_key = "/".join(part for part in (self.prefix, key.strip("/")) if part)
        response = self.client.get_object(Bucket=self.bucket, Key=object_key)
        return json.loads(response["Body"].read().decode("utf-8"))
