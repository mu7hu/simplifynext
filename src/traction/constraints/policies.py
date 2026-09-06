"""Deterministic exploration vs exploitation policies."""

from pydantic import BaseModel, Field


class ExploreExploitPolicy(BaseModel):
    """Transparent, deterministic exploration/exploitation policy for hackathon evaluation."""

    initial_explore_pct: float = Field(default=0.40, description="Exploration ratio for cycles 1-2")
    mid_explore_pct: float = Field(default=0.30, description="Exploration ratio for cycles 3-4")
    mature_explore_pct: float = Field(default=0.15, description="Exploration ratio for cycles 5+")
    min_explore_floor: float = Field(default=0.10, description="Guaranteed minimum exploration floor")

    def get_exploration_target(self, cycle_id: int, highest_confidence: float = 0.5) -> float:
        """Compute the recommended exploration ratio based on cycle count and empirical confidence."""
        if cycle_id <= 2:
            base = self.initial_explore_pct
        elif cycle_id <= 4:
            base = self.mid_explore_pct
        else:
            base = self.mature_explore_pct

        # If highest confidence in a winning channel is high (>0.8), allow slight shift toward exploitation
        if highest_confidence > 0.8:
            base = max(self.min_explore_floor, base - 0.05)

        return round(max(self.min_explore_floor, base), 2)

    def get_exploitation_target(self, cycle_id: int, highest_confidence: float = 0.5) -> float:
        """Exploitation share is the complement of exploration share."""
        return round(1.0 - self.get_exploration_target(cycle_id, highest_confidence), 2)
