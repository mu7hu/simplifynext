"""Evaluation metrics aligning with the official SimplifyNext Agentic AI standards."""

from pydantic import BaseModel, Field


class EvaluationMetrics(BaseModel):
    """Benchmark metrics comparing portfolio allocators."""

    strategy_name: str
    total_spend: float
    total_outcomes: int
    blended_cac: float
    cumulative_outcomes_per_dollar: float = Field(description="Total qualified demos / Total dollars spent")
    regret_vs_oracle: int = Field(description="Oracle total outcomes minus strategy outcomes")
    cycles_to_identify_best: int = Field(description="Number of cycles required to establish top allocation on winner")
    final_allocation_distance: float = Field(description="L1 distance from Oracle final allocation vector (0.0 to 2.0)")
    unjustified_early_cut_rate: float = Field(description="Percentage of cuts made before min evaluation window elapsed")

    # SimplifyNext Slide 22 Official Digital AI Agent Metrics:
    schema_validation_pass_rate: float = Field(default=1.0, description="Share of agent outputs parsing and validating on first attempt")
    tool_call_success_rate: float = Field(default=1.0, description="Share of simulation and measurement steps completing successfully")
    task_completion_rate: float = Field(default=1.0, description="Requests resolved end-to-end without human intervention")
    token_cost_per_run: float = Field(default=0.0, description="Estimated LLM API cost in USD")
    loop_discipline_rate: float = Field(default=1.0, description="Ratio of runs converging within max iteration cap")
    answer_fidelity_score: float = Field(default=0.95, description="Fidelity score against ground truth")
