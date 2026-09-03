"""Human-in-the-loop approval gate."""

from traction.approval.base import ApprovalGate, ApprovalDecision, ApprovalAction
from traction.approval.cli import CLIApprovalGate, AutoApprovalGate

__all__ = ["ApprovalGate", "ApprovalDecision", "ApprovalAction", "CLIApprovalGate", "AutoApprovalGate"]
