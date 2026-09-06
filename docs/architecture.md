# Traction: System Architecture

## Overview
Traction is an autonomous cross-channel marketing experimentation and budget allocation system designed for early-stage founders. Rather than generating ad copy or marketing fluff, Traction treats a startup's marketing budget as a venture portfolio of empirical experiments under market noise and conversion latency.

```
                    ┌────────────────────────┐
                    │      Founder Intake    │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  Context & Priors      │
                    │  (Benchmark Priors)    │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   Strategist Agent     │ ◄─── Persistent Learnings & History
                    │ (Portfolio Allocation) │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  Deterministic Checks  │ (Budget sum, hard exclusions, floors)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  Human Approval Gate   │ (Approve / Reject / Edit)
                    └───────────┬────────────┘
                                │ (Approved)
                                ▼
                    ┌────────────────────────┐
                    │   Execution Service    │
                    │   / Market Simulator   │
                    └───────────┬────────────┘
                                │ Raw Telemetry
                                ▼
                    ┌────────────────────────┐
                    │ Measurement Normalizer │ (Comparable CAC, conversion rates)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │     Analyst Agent      │
                    │ (SCALE/HOLD/CUT/NODATA)│
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │  Experiment Ledger     │ (SQLite persistent organizational memory)
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ Weekly Founder Digest  │
                    └────────────────────────┘
```

## Agent Responsibilities
1. **Supervisor / Orchestration Layer (LangGraph StateGraph)**:
   - Manages cycle progression, bounded self-repair, and loop caps (`MAX_GRAPH_ITERATIONS`).
   - Implements event streaming (`graph.stream()`).
   - Strictly forbids deploying capital without explicit approval.
2. **Strategist Agent**:
   - Manages exploration vs. exploitation trade-offs.
   - Respects founder soft priors in early cycles, but challenges founder biases with empirical evidence as data accumulates.
   - Generates hypotheses, target audiences, and success thresholds.
3. **Analyst Agent**:
   - Analyzes normalized telemetry against benchmarks and target thresholds.
   - Issues one of four verdicts: `SCALE`, `HOLD`, `CUT`, or first-class `INSUFFICIENT_DATA`.
   - Protects experiments with long evaluation windows from premature cuts.

## Deterministic vs LLM Boundary
- **LLMs (AWS Bedrock Claude Sonnet / Haiku)**:
  - Hypothesis formulation under uncertainty.
  - Interpreting multi-channel trade-offs.
  - Formulating actionable learnings and explaining budget shifts to the founder.
- **Deterministic Python**:
  - Exact budget summation and micro-cent rounding adjustments.
  - Enforcing hard exclusions ($0 allocation).
  - Risk caps (maximum channel concentration) and exploration floors.
  - Calculating observed CAC, CTR, and conversion rates.
  - SQLite ledger persistence and transaction guarantees.
