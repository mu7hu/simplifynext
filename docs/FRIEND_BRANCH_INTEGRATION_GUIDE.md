# Traction — branch integration guide

This is the handoff for the teammate-owned branch. The objective is to merge both branches into one complete, bounded, offline-runnable system.

## System ownership diagram

```text
Founder input
     │
     ▼
┌────────────────────────────────────────────────────────────────────┐
│ MY BRANCH — strategy and orchestration                             │
│                                                                    │
│ load context → Strategist → validate → human approval              │
│       ▲                                      │ approved             │
│       │                                      ▼                      │
│ ledger learnings ◄── persist ◄── Analyst ◄── Measure ◄── Execute   │
│       │                                      │                      │
│       └────────────── replan next cycle ◄── Digest                  │
└────────────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────────────┐
│ YOUR BRANCH — evaluation and founder experience                    │
│                                                                    │
│ Intake → Profiler → Execution adapters/simulator                   │
│ Measurement normalizer → Analyst verdicts → Digest → Frontend      │
└────────────────────────────────────────────────────────────────────┘
```

## Done versus remaining

```text
DONE ON MY BRANCH                          REMAINING ON YOUR BRANCH
────────────────────────                   ─────────────────────────
✓ Pydantic contracts                       □ Production Analyst Agent
✓ LangGraph Supervisor                     □ Production Measurement
✓ Deterministic Strategist                 □ Real Intake provider/UI
✓ Budget and constraint engine              □ Startup profiler/retrieval
✓ Explore/exploit policy                   □ Real execution adapters
✓ SQLite experiment ledger                 □ Founder digest improvements
✓ Human approval gate                      □ Frontend integration
✓ Baseline allocators
✓ Evaluation harness
✓ Deterministic simulator stub
✓ AgentCore-compatible entrypoint
✓ 19 automated tests passing
✓ Five-cycle local demo passing
```

The current teammate-owned stubs are `StubAnalystAgent`, `DefaultMeasurementService`, `MockIntakeProvider`, `MockProfilerService`, `SimulatedExecutionService`, and `MarkdownDigestService`.

## Stable contracts

The three contracts must not be changed casually:

1. `ExperimentPlan` — `src/traction/schemas/experiment.py` — Strategist output consumed by execution and analysis.
2. `ExperimentResult` — `src/traction/schemas/result.py` — normalized measurement output consumed by Analyst and Ledger.
3. `AnalysisReport` — `src/traction/schemas/analysis.py` — Analyst output consumed by validation, Ledger, Digest, and the next planning cycle.

Supported verdicts are exactly `SCALE`, `HOLD`, `CUT`, and `INSUFFICIENT_DATA`.

## Interfaces to implement or replace

### Analyst

File: `src/traction/agents/analyst.py`

```python
analyze_cycle(
    cycle_id: int,
    plan: ExperimentPlan,
    results: list[ExperimentResult],
    benchmark_priors: list[BenchmarkPrior],
) -> AnalysisReport
```

Compare results with targets and priors, preserve `INSUFFICIENT_DATA` for incomplete windows, include confidence and learning, and return a validated `AnalysisReport`.

### Measurement

File: `src/traction/services/measurement.py`

```python
normalize_results(
    raw_results: list[RawExecutionResult],
    plan: ExperimentPlan,
    benchmark_priors: list[BenchmarkPrior],
) -> list[ExperimentResult]
```

Normalize cross-channel telemetry into comparable spend, outcomes, CAC, conversion rate, CTR, observation days, window status, and raw metrics.

### Intake and Profiler

Files: `src/traction/services/intake.py` and `src/traction/services/profiler.py`

```python
get_founder_brief(startup_id: str) -> FounderBrief
get_startup_profile(startup_id: str) -> StartupProfile
get_benchmark_priors(startup_id: str) -> list[BenchmarkPrior]
```

Return validated schemas. Founder preferences are soft priors; hard exclusions are absolute.

### Execution

File: `src/traction/services/execution.py`

```python
execute_plan(plan: ExperimentPlan) -> list[RawExecutionResult]
```

Execution is called only after approval. Real adapters may replace the simulator, but must not bypass approval or expose hidden oracle values to agents.

### Digest and Frontend

File: `src/traction/services/digest.py`

```python
generate_digest(
    plan: ExperimentPlan,
    results: list[ExperimentResult],
    report: AnalysisReport,
    learnings: list[str],
) -> str
```

The frontend may replace `CLIApprovalGate` with `ApprovalGate.evaluate(...)`. It must show current/proposed spend, dollar and percentage movement, and reason. Edited allocations must be revalidated by deterministic Python before execution.

## Recommended merge process

```text
strategy branch ──┐
                  ├── integration branch ── tests ── demo ── frontend
teammate branch ──┘
```

1. Create an integration branch.
2. Merge or rebase the strategy branch and teammate branch.
3. Keep the existing schema contracts unless a change is agreed first.
4. Replace each stub behind its existing abstract interface.
5. Run tests after each replacement.
6. Run the offline demo before enabling live providers.
7. Add fake-provider tests so default tests never require AWS credentials.
8. Integrate the frontend last; consume graph events instead of duplicating budget arithmetic.

## Definition of done

- `python -m pytest -q` passes.
- `python scripts/run_demo.py` completes five cycles offline.
- `python scripts/run_cycle.py --startup-id ledger_ai --cycle-id 1 --budget 2000` works without AWS credentials.
- `python scripts/run_evaluation.py --startups 5 --cycles 6` completes.
- No execution occurs before approval.
- Edited allocations are revalidated.
- SQLite history and learnings persist across cycles.
- Analyst correctly handles all four verdict types and incomplete windows.
- Oracle ground truth stays outside normal agent state.
- Providers can be swapped in without changing the three primary schemas.

See `docs/TEAMMATE_HANDOFF.md` for the detailed per-component contract, call site, example data, preserved tests, and ownership notes.
