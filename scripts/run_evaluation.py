"""Run the comparative evaluation benchmark harness across 12 cycles."""

import argparse
import sys
import os
from rich.console import Console
from rich.table import Table

sys.path.insert(0, os.path.abspath("src"))

from traction.evaluation.harness import EvaluationHarness


def main():
    parser = argparse.ArgumentParser(description="Run comparative evaluation benchmark.")
    parser.add_argument("--startups", type=int, default=5, help="Number of simulated startups")
    parser.add_argument("--cycles", type=int, default=12, help="Number of cycles per startup")
    parser.add_argument("--csv", default="eval_results.csv", help="CSV output destination")
    parser.add_argument("--json", default="eval_summary.json", help="JSON output destination")
    args = parser.parse_args()

    console = Console()
    console.print(f"[bold cyan]Running Benchmark: {args.startups} Startups x {args.cycles} Cycles[/bold cyan]")

    harness = EvaluationHarness(num_startups=args.startups, num_cycles=args.cycles)
    summary = harness.run_all(csv_path=args.csv, json_path=args.json)

    table = Table(title="Comparative Benchmark Results")
    table.add_column("Strategy", style="cyan")
    table.add_column("Total Spend", justify="right")
    table.add_column("Total Outcomes", justify="right")
    table.add_column("Blended CAC", justify="right")
    table.add_column("Outcomes/$", justify="right", style="bold green")
    table.add_column("Regret vs Oracle", justify="right")
    table.add_column("Cycles to Best", justify="right")
    table.add_column("Distance to Oracle", justify="right")

    for name, m in summary.items():
        table.add_row(
            name,
            f"${m['total_spend']:,.2f}",
            str(m["total_outcomes"]),
            f"${m['blended_cac']:.2f}",
            f"{m['cumulative_outcomes_per_dollar']:.4f}",
            str(m["regret_vs_oracle"]),
            str(m["cycles_to_identify_best"]),
            f"{m['final_allocation_distance']:.2f}"
        )

    console.print(table)
    console.print(f"[green]Evaluation saved to {args.csv} and {args.json}[/green]")


if __name__ == "__main__":
    main()
