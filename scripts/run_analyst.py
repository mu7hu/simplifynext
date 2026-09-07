"""Run the Analyst Agent in isolation from a JSON payload file.

Usage::

    python scripts/run_analyst.py path/to/payload.json
    python scripts/run_analyst.py path/to/payload.json --pretty

The payload has the same shape the Lambda handler accepts::

    {
      "cycle_id": 3,
      "plan": { ...ExperimentPlan... },
      "results": [ { ...ExperimentResult... }, ... ],
      "benchmark_priors": [ { ...BenchmarkPrior... }, ... ]
    }

Prints the resulting ``AnalysisReport`` as JSON to stdout. No graph, no
orchestration state, no AWS required (falls back to the deterministic analyst
when credentials are absent). Exit code is non-zero on validation failure.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from augury.api.analyst_lambda import analyze_payload  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Augury Analyst Agent on a JSON payload.")
    parser.add_argument("payload", help="Path to a JSON file with cycle_id / plan / results / benchmark_priors")
    parser.add_argument("--pretty", action="store_true", help="Indent the JSON output")
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    try:
        report = analyze_payload(payload)
    except Exception as exc:  # noqa: BLE001 - surface any validation/analysis error to the shell
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(report.model_dump_json(indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
