# Agent Contracts & Team Interfaces

## Boundary Definition
The project is decoupled across a clean 50/50 division of responsibility:

```
[Strategy & Orchestration Half]                    [Evaluation & Services Half]
           YOU                                               TEAMMATE
- LangGraph Supervisor                             - Analyst Agent (Verdicts)
- Strategist Agent (Portfolio Plan)                - Measurement Normalization
- Deterministic Constraint Engine                  - Founder Weekly Digest
- Persistent SQLite Ledger                         - Intake & Profiler Services
- Human Approval Gate                              - Execution Adapters / Simulator
```

## Primary Schemas
### 1. `ExperimentPlan` (Produced by Strategist Agent)
```python
class ExperimentPlan(BaseModel):
    cycle_id: int
    total_budget: float
    primary_goal: str
    allocations: list[Allocation]
    exploration_budget_pct: float
    exploitation_budget_pct: float
    strategy_summary: str
    major_uncertainties: list[str]
```

### 2. `AnalysisReport` (Produced by Analyst Agent)
```python
class AnalysisReport(BaseModel):
    cycle_id: int
    verdicts: list[ExperimentVerdict]
    executive_summary: str
    primary_bottleneck: Optional[str]
    recommended_explore_ratio: float
```
