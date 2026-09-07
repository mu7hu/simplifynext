"""CLI runner to execute a single marketing cycle."""

import argparse
import sys
import os
sys.path.insert(0, os.path.abspath("src"))

from augury.config import settings
from augury.api.agentcore_app import entrypoint


def main():
    parser = argparse.ArgumentParser(description="Run a single Augury cycle.")
    parser.add_argument("--startup-id", default="ledger_ai", help="Startup identifier")
    parser.add_argument("--cycle-id", type=int, default=1, help="Cycle number to run")
    parser.add_argument("--budget", type=float, default=2000.0, help="Cycle budget")
    args = parser.parse_args()

    req = {
        "startup_id": args.startup_id,
        "cycle_id": args.cycle_id,
        "total_budget": args.budget,
        "auto_approve": True
    }

    res = entrypoint(req)
    print(f"Cycle {res['cycle_id']} Completed for {res['startup_id']}")
    print(f"Strategy: {res['strategy_summary']}")
    print(f"Verdicts: {len(res['verdicts'])} channels evaluated")
    print(f"\n{res['digest_markdown']}")


if __name__ == "__main__":
    main()
