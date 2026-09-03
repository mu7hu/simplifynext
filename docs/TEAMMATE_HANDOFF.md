# Traction teammate handoff

This document defines the integration boundary for the evaluation and founder-experience components. The strategy/orchestration side owns the graph, deterministic validation, approval, ledger, and replanning. The teammate-owned components can replace the stubs below without changing the core contracts.

## Non-negotiable contracts

The primary cross-team schemas are:

- `ExperimentPlan` in `src/traction/schemas/experiment.py`: strategist output passed to execution and analysis.
- `ExperimentResult` in `src/traction/schemas/result.py`: normalized result passed to analysis and the ledger.
- `AnalysisReport` in `src/traction/schemas/analysis.py`: analyst output passed to validation, ledger, digest, and the next planning cycle.

Do not change these schemas casually. If a field must evolve, preserve backwards-compatible defaults and update the tests and this document together.

## A. AnalystAgent

- Interface: `AnalystAgent.analyze_cycle`
- Location: `src/traction/agents/analyst.py`
- Signature: `analyze_cycle(cycle_id: int, plan: ExperimentPlan, results: list[ExperimentResult], benchmark_priors: list[BenchmarkPrior]) -> AnalysisReport`
- Input: the approved plan, normalized comparable results, and benchmark priors.
- Output: `AnalysisReport` with verdicts using `SCALE`, `HOLD`, `CUT`, or `INSUFFICIENT_DATA`; each verdict should include confidence, CAC comparison, evidence count, evaluation-window status, reasoning, budget direction, learning, and attribution warnings where applicable.
- Existing stub: `StubAnalystAgent`, backed by the deterministic local model in `src/traction/models.py`.
- Preserve: `tests/test_analyst.py` and `tests/test_graph.py`.
- Called from: `node_analyst` in `src/traction/graph/nodes.py`, after execution and measurement.
- Example: a 14-day Google result with CAC 280 against target 350 can yield `SCALE`; an incomplete 30-day Founder Content window should not be cut solely on early data.
- Definition of done: deterministic offline tests pass, incomplete windows are protected, and the implementation returns only validated `AnalysisReport` objects.

## B. MeasurementService

- Interface: `MeasurementService.normalize_results`
- Location: `src/traction/services/measurement.py`
- Signature: `normalize_results(raw_results: list[RawExecutionResult], plan: ExperimentPlan, benchmark_priors: list[BenchmarkPrior]) -> list[ExperimentResult]`
- Input: execution telemetry plus the approved plan and priors.
- Output: normalized `ExperimentResult` objects with spend, outcomes, observed CAC, conversion rate, CTR, observed days, evaluation-window completion, and raw metrics.
- Existing stub: `DefaultMeasurementService`.
- Preserve: simulator and graph tests that rely on deterministic normalization.
- Called from: `node_measure`.
- Example: raw spend 800 and 3 outcomes becomes observed CAC 266.67; `days_active < evaluation_window_days` means `is_window_complete=False`.
- Definition of done: cross-channel telemetry maps consistently to this schema, with explicit attribution warnings or quality fields where needed.

## C. IntakeProvider

- Interface: `IntakeProvider.get_founder_brief(startup_id: str) -> FounderBrief`
- Location: `src/traction/services/intake.py`
- Existing stub: `MockIntakeProvider` seeded with LedgerAI.
- Called from: `node_load_context`.
- Preserve: `FounderBrief` fields for budget, goal, initial allocations, soft preferences, and hard exclusions.
- Definition of done: production intake can provide a validated `FounderBrief` without changing strategist or graph code.

## D. ProfilerService

- Interface: `get_startup_profile(startup_id: str) -> StartupProfile` and `get_benchmark_priors(startup_id: str) -> list[BenchmarkPrior]`
- Location: `src/traction/services/profiler.py`
- Existing stub: `MockProfilerService`.
- Called from: `node_load_context`.
- Example priors include channel median CAC, min/max CAC, CPC, conversion rate, minimum evaluation days, and rationale.
- Definition of done: retrieval is deterministic or traceable, returns validated schemas, and does not leak simulator ground truth into normal agent state.

## E. ExecutionService / simulator

- Interface: `ExecutionService.execute_plan(plan: ExperimentPlan) -> list[RawExecutionResult]`
- Location: `src/traction/services/execution.py`
- Existing stub: `SimulatedExecutionService`, backed by `MarketSimulator` in `src/traction/simulator/market.py`.
- Called from: `node_execute`, only after the approval gate returns `APPROVE` or a revalidated `EDIT`.
- Preserve: seeded determinism and the separation between normal plan state and oracle/ground-truth parameters.
- Definition of done: adapters can execute real channels or a richer simulator while maintaining the same raw-result boundary and never bypassing approval.

## F. DigestService

- Interface: `generate_digest(plan: ExperimentPlan, results: list[ExperimentResult], report: AnalysisReport, learnings: list[str]) -> str`
- Location: `src/traction/services/digest.py`
- Existing stub: `MarkdownDigestService`.
- Called from: `node_generate_digest` after ledger persistence.
- Definition of done: founder-facing output explains outcomes, verdicts, learnings, and proposed next-cycle movement without becoming the source of allocation truth.

## G. Frontend integration

The frontend may replace `CLIApprovalGate` in `src/traction/approval/cli.py` with an implementation of `ApprovalGate.evaluate(current_plan, proposed_plan) -> ApprovalDecision`. It must display current/proposed spend, dollar and percentage movement, and the reason for each movement. `EDIT` values must be converted into a revised plan and run through deterministic constraint validation before execution. No UI action may execute an unapproved plan.

The frontend can consume graph events from `graph.stream()` or the `events` state list. It should treat the graph and schemas as the source of workflow state, not reimplement budget arithmetic.

## Integration checklist

- Keep `ExperimentPlan`, `ExperimentResult`, and `AnalysisReport` backwards-compatible.
- Preserve `tests/test_analyst.py`, `tests/test_graph.py`, `tests/test_simulator.py`, and the end-to-end stub-mode command.
- Keep execution after approval and keep all graph loops bounded.
- Keep simulator oracle parameters outside strategist, analyst, and normal graph state.
- Add component-specific tests before replacing a stub in the demo path.
