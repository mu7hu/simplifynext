"""Run the Content Generator Agent in isolation from a JSON payload file.

Usage::

    python scripts/run_content.py path/to/payload.json
    python scripts/run_content.py path/to/payload.json --pretty

Payload shape (same as the Lambda handler)::

    {
      "cycle_id": 3,
      "plan": { ...ExperimentPlan... },
      "startup_profile": { ...StartupProfile... },   # optional
      "founder_brief": { ...FounderBrief... },       # optional
      "only_channels": ["GOOGLE_SEARCH"],            # optional
      "variants": 3                                   # optional
    }

Prints the ``ContentPackage`` as JSON. No graph, no orchestration, no AWS
required (falls back to deterministic templates without credentials).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from augury.api.content_lambda import generate_from_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Augury Content Generator Agent on a JSON payload.")
    parser.add_argument("payload", help="Path to a JSON file with cycle_id / plan / (optional) context")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON output")
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    try:
        package = generate_from_payload(payload)
    except Exception as exc:  # noqa: BLE001 - surface any validation/generation error
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(package.model_dump_json(indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
