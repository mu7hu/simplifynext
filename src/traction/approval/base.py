"""Human approval gate interface and decision models."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from traction.schemas.experiment import ExperimentPlan


class ApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    EDIT = "EDIT"


class ApprovalDecision(BaseModel):
    action: ApprovalAction
    revised_allocations: Optional[dict[str, float]] = Field(default=None, description="Manual edits if action is EDIT")
    feedback: Optional[str] = Field(default=None, description="Founder notes explaining rejection or modification")


class ApprovalGate(ABC):
    """Abstract human-in-the-loop gate."""

    @abstractmethod
    def evaluate(self, current_plan: Optional[ExperimentPlan], proposed_plan: ExperimentPlan) -> ApprovalDecision:
        """Present proposed allocations to founder and collect decision."""
        pass
