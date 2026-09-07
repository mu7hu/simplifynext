"""Interactive CLI approval gate and automated test gate."""

from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from augury.approval.base import ApprovalGate, ApprovalDecision, ApprovalAction
from augury.schemas.experiment import ExperimentPlan
from augury.constraints.budget import validate_budget_sum


class CLIApprovalGate(ApprovalGate):
    """Interactive command-line approval gate with rich formatted tables."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def evaluate(self, current_plan: Optional[ExperimentPlan], proposed_plan: ExperimentPlan) -> ApprovalDecision:
        self.console.print("\n")
        self.console.print(Panel.fit(
            f"[bold cyan]Augury Human Approval Gate — Cycle {proposed_plan.cycle_id}[/bold cyan]\n"
            f"[yellow]Strategy:[/yellow] {proposed_plan.strategy_summary}",
            title="Founder Review Required"
        ))

        table = Table(title=f"Proposed Portfolio Reallocation (${proposed_plan.total_budget:,.2f})")
        table.add_column("Channel", style="cyan", no_wrap=True)
        table.add_column("Current $", justify="right")
        table.add_column("Proposed $", justify="right", style="bold green")
        table.add_column("Change", justify="right")
        table.add_column("Share %", justify="right")
        table.add_column("Type", style="magenta")
        table.add_column("Reason / Hypothesis", style="dim")

        for a in proposed_plan.allocations:
            diff = a.proposed_budget - a.current_budget
            if diff > 0:
                diff_str = f"[green]+${diff:,.2f}[/green]"
            elif diff < 0:
                diff_str = f"[red]-${abs(diff):,.2f}[/red]"
            else:
                diff_str = "$0.00"

            type_str = "Explore" if a.is_exploration else "Exploit"
            table.add_row(
                a.channel.value,
                f"${a.current_budget:,.2f}",
                f"${a.proposed_budget:,.2f}",
                diff_str,
                f"{a.proposed_share*100:.1f}%",
                type_str,
                f"{a.reason} ({a.hypothesis[:50]}...)"
            )

        self.console.print(table)

        # In interactive mode, prompt user
        prompt = (
            "\n[bold yellow]Options:[/bold yellow]\n"
            "  [A] Approve plan and authorize execution\n"
            "  [R] Reject plan and request strategic replan\n"
            "  [E] Edit allocations manually\n"
            "Choose action [A/R/E] (default: A): "
        )
        self.console.print(prompt, end="")
        try:
            choice = input().strip().upper()
        except EOFError:
            choice = "A"

        if choice == "R":
            self.console.print("[red]Plan rejected by founder.[/red] Please provide feedback for the Strategist: ", end="")
            feedback = input().strip() or "Founder requested replan without specific comment."
            return ApprovalDecision(action=ApprovalAction.REJECT, feedback=feedback)

        elif choice == "E":
            self.console.print("[cyan]Manual allocation edit initiated.[/cyan]")
            edits = {}
            for a in proposed_plan.allocations:
                self.console.print(f"Spend for {a.channel.value} (current proposed ${a.proposed_budget:.2f}): $", end="")
                val_str = input().strip()
                val = float(val_str) if val_str else a.proposed_budget
                edits[a.channel.value] = val
            return ApprovalDecision(action=ApprovalAction.EDIT, revised_allocations=edits)

        else:
            self.console.print("[bold green]Plan APPROVED by founder. Authorizing execution...[/bold green]")
            return ApprovalDecision(action=ApprovalAction.APPROVE)


class AutoApprovalGate(ApprovalGate):
    """Auto-approver for automated benchmarks, unit tests, and headless evaluations."""

    def __init__(self, default_action: ApprovalAction = ApprovalAction.APPROVE):
        self.default_action = default_action

    def evaluate(self, current_plan: Optional[ExperimentPlan], proposed_plan: ExperimentPlan) -> ApprovalDecision:
        return ApprovalDecision(action=self.default_action)
