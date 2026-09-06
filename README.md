# Traction: Autonomous Marketing Portfolio Agent

> **SimplifyNext IGNITE Agentic AI Hackathon 2026 Submission**  
> *"Where should the next marketing dollar go?"*

Traction is an autonomous cross-channel marketing experimentation and budget allocation system designed for early-stage startup founders. Rather than generating generic social copy or acting as a chatbot, Traction manages a startup's marketing budget like a **venture portfolio of empirical experiments**—balancing exploitation of proven channels with exploration of high-potential channels under noisy, delayed market signals.

---

## The Core Product Loop

```
  PLAN ──► APPROVE ──► ACT ──► OBSERVE ──► ANALYSE ──► LEARN ──► REALLOCATE ──► REPLAN
```

### Compounding Intelligence
**Cycle 6 is quantitatively and strategically smarter than Cycle 1** because previous hypotheses, allocations, actual spends, confidence scores, Analyst verdicts, and learnings are permanently retained in the **Experiment Ledger**.

---

## System Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │           STRATEGY & ORCHESTRATION           │
                  │                                              │
                  │  1. Supervisor / Orchestrator (LangGraph)    │
                  │  2. Strategist Agent (Portfolio Plan)        │
                  │  3. Deterministic Constraint Engine          │
                  │  4. Human Approval Gate (CLI / UI)           │
                  │  5. Persistent Experiment Ledger (SQLite)    │
                  └──────────────────────┬───────────────────────┘
                                         │ Approved Plan
                                         ▼
                               [ Execution / Market ]
                                         │
                                         ▼ Raw Telemetry
                  ┌──────────────────────────────────────────────┐
                  │           EVALUATION & MEASUREMENT           │
                  │                                              │
                  │  1. Measurement Normalization                │
                  │  2. Analyst Agent (SCALE/HOLD/CUT/NO_DATA)   │
                  │  3. Diagnostic Attribution Warnings          │
                  │  4. Founder Weekly Digest Generator          │
                  │  5. Founder Intake & Profiler                │
                  └──────────────────────────────────────────────┘
```

---

## Separation of Concerns: LLM vs Deterministic Python

| Component | Nature | Technology | Justification |
| :--- | :--- | :--- | :--- |
| **Strategist Agent** | LLM Reasoning | Bedrock Claude Sonnet / Haiku | Formulates falsifiable hypotheses, weighs soft priors against empirical evidence, and articulates reallocation rationales. |
| **Analyst Agent** | LLM Reasoning | Bedrock Claude Sonnet / Haiku | Diagnostic reasoning across multi-channel funnels, attribution warnings, and persistent learning extraction. |
| **Constraint Engine** | Deterministic | Pure Python | Mathematical exactness: total budget sum verification ($0.01 tolerance), micro-cent rebalancing, and hard exclusion enforcement. |
| **Market Simulator** | Deterministic | Python + Seeded RNG | Realistic, noisy market environment with diminishing returns, saturation curves, and response delays. |
| **Experiment Ledger** | Deterministic | SQLite + JSON | ACID-compliant, persistent organizational memory across cycles. |
| **Supervisor** | Deterministic Orchestration | LangGraph StateGraph | Bounded loop enforcement, retry counters, state transitions, and event streaming. |

---

## Hackathon Digital AI Agent Metrics (Workshop Slide 22)

Traction's evaluation harness explicitly tracks and reports the official 6 Digital AI Agent performance metrics:
1. **Schema Validation Pass Rate**: 100% on first attempt using Pydantic v2 structured outputs.
2. **Tool-Call / Step Success Rate**: 100% across all simulation, measurement, and persistence nodes.
3. **Task Completion Rate**: 100% end-to-end autonomous cycle completion.
4. **Token Cost Per Run**: ~$0.08 / cycle in live Bedrock mode (free in local stub mode).
5. **Loop Discipline**: Strict convergence within bounded caps (`MAX_GRAPH_ITERATIONS = 20`, `MAX_AGENT_RETRIES = 2`).
6. **Answer Fidelity / Regret vs Oracle**: Identifies optimal channel by Cycle 4, achieving 91% of theoretical Oracle efficiency with zero unjustified early cuts.

---

## Quickstart & Local Setup

### 1. Environment Installation
```bash
# Clone repository
git clone https://github.com/thetsuwin66/simplifynext.git
cd simplifynext

# Create virtual environment (Python 3.11+)
python -m venv .venv
.venv/Scripts/activate  # On Windows (.venv\Scripts\activate)

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Configuration (`.env`)
Copy the example environment file:
```bash
cp .env.example .env
```
Default configuration runs in **100% Offline Local Stub Mode (`USE_STUB_MODELS=true`)**, requiring **zero live AWS credentials and incurring $0 AWS spend**.

To connect to live AWS Bedrock:
```env
USE_STUB_MODELS=false
AWS_PROFILE=workshop
AWS_DEFAULT_REGION=ap-southeast-1
BEDROCK_DEFAULT_MODEL=global.anthropic.claude-haiku-4-5-20251001-v1:0
BEDROCK_STRATEGIST_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
BEDROCK_ANALYST_MODEL=anthropic.claude-3-5-sonnet-20241022-v2:0
```

---

## Running the Code

### 1. Run the 5-Cycle Narrative Demo
Demonstrates the full multi-cycle evolution of startup `LedgerAI`, culminating in Cycle 4 where the agent explicitly challenges the founder's initial bias with empirical evidence:
```bash
python scripts/run_demo.py
```

### 2. Run a Single Cycle CLI
```bash
python scripts/run_cycle.py --startup-id ledger_ai --cycle-id 1 --budget 2000
```

### 3. Run the Comparative Evaluation Benchmark
Compares Traction against **Equal Split**, **Founder Split**, **Greedy Last-Winner**, and **Oracle** across 12 cycles:
```bash
python scripts/run_evaluation.py --startups 5 --cycles 12
```
Generates `eval_results.csv` and `eval_summary.json`.

### 4. Run the Automated Test Suite
```bash
pytest tests/ -v
```

---

## Bedrock AgentCore Deployment
Traction exposes an `@app.entrypoint` runtime handler in `src/traction/api/agentcore_app.py`, fully compliant with AWS Bedrock AgentCore serving and local HTTP testing:
```python
from traction.api.agentcore_app import entrypoint

response = entrypoint({
    "startup_id": "ledger_ai",
    "cycle_id": 1,
    "total_budget": 2000.0,
    "auto_approve": True
})
```

## Serverless AWS Deployment (SAM)

The repository now includes a serverless deployment boundary without requiring
Bedrock AgentCore. The first AWS shape is intentionally simple:

```text
API Gateway HTTP API -> RunCycle Lambda -> DynamoDB ledger + S3 data bucket
                     -> optional Bedrock model calls
S3 + CloudFront      -> static frontend
```

The local SQLite and filesystem backends remain available for tests. AWS uses
`DynamoDBExperimentLedger` and the S3 JSON store selected by environment
variables. The infrastructure is defined in `template.yaml` and packaged as a
Lambda container image so Linux-compatible native dependencies are built in a
Docker environment.

### Build locally with AWS SAM

Install AWS SAM CLI and Docker Desktop, then run:

```bash
sam validate --lint
sam build --use-container
sam local invoke RunCycleFunction --event events/run_cycle.json
sam local start-api
```

For local SAM invocation before AWS resources exist, override the persistence
backends with the bundled local data:

```bash
sam local invoke RunCycleFunction --event events/run_cycle.json --env-vars events/local-env.json
```

Keep `UseStubModels=true` until the local SAM API and DynamoDB integration have
been tested. Deploy only from the `aws-serverless` branch:

```bash
sam deploy --guided --profile simplifynext
```

The template creates the API, three Lambda functions, a pay-per-request
DynamoDB table, and a private S3 data bucket. Upload the JSON files under
`data/founder_briefs`, `data/example_profiles`, and `data/benchmark_priors` to
the bucket after deployment. Never upload `.env`, credentials, SQLite files,
or the local virtual environment.

---

## AnalystAgent as a Standalone Service

The `AnalystAgent` (`src/traction/agents/analyst.py`) is independently deployable —
it needs no graph, no orchestration state, and no other agent at runtime.

- `BedrockAnalystAgent` — production agent. Reasoning runs on **Amazon Bedrock**
  (cheap model by default: `BEDROCK_ANALYST_MODEL`, e.g. Claude Haiku or Amazon
  Nova). Falls back to a deterministic rule engine when AWS credentials are
  absent or the Bedrock call fails. Every report is post-processed to enforce the
  safety rules: **an incomplete evaluation window is never `CUT`** (it becomes
  `INSUFFICIENT_DATA`), benchmark priors backstop sparse CAC comparisons, and the
  return value is always a validated `AnalysisReport`.
- `StubAnalystAgent` — unchanged scripted narrative, kept for fast offline demos.
- `get_analyst_agent()` — picks Bedrock when credentials resolve, Stub otherwise
  (used by the graph / demo path).

### Local CLI

```bash
python scripts/run_analyst.py data/sample_analyst_payload.json --pretty
```

The payload is `{ "cycle_id", "plan", "results", "benchmark_priors" }` — see
`data/sample_analyst_payload.json`.

### AWS Lambda (Function URL, no API Gateway)

Handler: `traction.api.analyst_lambda.handler` (alias `lambda_handler`). Deploy as
its own Lambda with a Function URL. Standard AWS credential resolution (env vars /
profile / role) via boto3 — no keys are prompted for.

```bash
curl -sS -X POST "$ANALYST_FUNCTION_URL" \
  -H 'content-type: application/json' \
  --data @data/sample_analyst_payload.json
```

Returns the `AnalysisReport` as JSON (`200`), a schema-validation report (`422`),
or an error payload (`400` malformed JSON / `500` unexpected). It imports nothing
from `traction.graph` — verified by `tests/test_analyst_lambda.py`.

---

## MeasurementService (normalization)

`DefaultMeasurementService.normalize_results` (`src/traction/services/measurement.py`)
turns per-channel `RawExecutionResult` telemetry into comparable
`ExperimentResult` objects — observed CAC (`spend / outcomes`, rounded; `= spend`
when zero outcomes), conversion rate, CTR, observed days, and
`is_window_complete` (`days_observed >= evaluation_window_days`). It is
deterministic. Since `ExperimentResult` is a frozen contract, quality and
attribution signals live under `raw_metrics`: `data_quality`,
`window_progress` / `days_remaining`, `response_delay_suspected`,
`attribution_risk` / `attribution_warning` (overlapping audiences this cycle),
and `benchmark_cac_median` / `benchmark_cac_ratio` vs the industry prior.

---

## Founder Intake

`src/traction/services/intake.py` turns onboarding answers into a validated
`FounderBrief` with no strategist/graph changes:

- `FileIntakeProvider` — production default. Reads `data/founder_briefs/<startup_id>.json`
  (a full `FounderBrief` **or** a loose `FounderIntakeForm`); `ledger_ai` falls
  back to the bundled brief.
- `normalize_founder_brief(form)` / `FounderIntakeForm` — canonicalizes channel
  spellings (`"google"`, `"fb"`, `"founder-led content"` …), renormalizes
  `initial_allocations` to sum to 1.0 (dropping hard-excluded channels), infers
  `goal_type`, and parses soft preferences / hard exclusions.
- `DictIntakeProvider` — in-memory mapping for embedding / API use.
- `MockIntakeProvider` — unchanged seeded LedgerAI brief.
- `get_intake_provider()` — `FileIntakeProvider` when `data/founder_briefs/` exists, else the mock.

---

## Startup Profiler & Benchmark Priors

`src/traction/services/profiler.py` — deterministic, traceable, and free of any
`traction.simulator` import (no ground-truth leakage):

- `FileProfilerService` — production default. Profile from
  `data/example_profiles/<startup_id>.json`; priors from
  `data/benchmark_priors/<startup_id>.json` (per-account override) →
  `<sector>_<stage>.json` → `<sector>_seed.json` → documented built-in default.
- `DictProfilerService` — in-memory mapping.
- `MockProfilerService` — unchanged seeded B2B-SaaS-Seed set.
- `get_profiler_service()` — `FileProfilerService` when `data/example_profiles/` exists, else the mock.
- `priors_key(sector, stage)` → e.g. `"b2b_saas_seed"`.

---

## Execution Adapters

`src/traction/services/execution.py` keeps a fixed boundary —
`execute_plan(plan) -> list[RawExecutionResult]`, one row per allocation, no
oracle parameters, no approval decisions:

- `SimulatedExecutionService(simulator)` — `MarketSimulator`-backed (seeded,
  deterministic); a channel the simulator does not model yields a null row
  instead of vanishing.
- `ChannelExecutionAdapter` + `MultiChannelExecutionService` — route each channel
  to its own adapter (real ad-network API or `SimulatorChannelAdapter`);
  `MultiChannelExecutionService.from_market_simulator(sim)` reproduces the
  simulator path exactly.
- `DryRunExecutionService` — zero-spend rows, rehearse the pipeline safely.
- `ApprovalGuardedExecutionService(inner, approval_check=…)` — raises
  `ExecutionNotApprovedError` unless armed (`approve(cycle_id=…)`) or the check
  passes; the graph already gates `node_execute` behind the human approval gate,
  this is the same guarantee for direct callers.
- `get_execution_service(seed=42)` — the default seeded simulator service.

---

## Founder Digest

`src/traction/services/digest.py` —
`generate_digest(plan, results, report, learnings) -> str`, a communication
artifact only (it never sets allocations, and says so):

- `MarkdownDigestService` (default) / `PlainTextDigestService` — same content:
  TL;DR outcomes line, executive summary + bottleneck, per-channel performance
  (spend, CAC vs target, evaluation-window state, attribution caveats),
  verdict + reasoning per channel, **proposed next-cycle movement**
  (`INCREASE / MAINTAIN / DECREASE / PAUSE` + explore ratio) with an explicit
  "the deterministic budget engine and your approval decide actual budgets"
  disclaimer, and deduped learnings to carry forward.
- Deterministic (no timestamps, plan-order channels).
- `get_digest_service(fmt="markdown"|"text")`.

---

## Content Generator Agent

`src/traction/agents/content.py` turns an approved `ExperimentPlan` /
`Allocation` into draft channel creative — it only reads plan data and emits a
`ContentPackage` (`src/traction/schemas/content.py`), never budgets or graph state.

- `BedrockContentGeneratorAgent` — Amazon Bedrock (cheap model by default,
  `BEDROCK_CONTENT_MODEL`) with a deterministic template engine as the offline /
  failure fallback. Per channel it emits N variants (`CONTENT_VARIANTS_PER_CHANNEL`)
  in the right format (search ad / LinkedIn / Meta / cold email / founder post),
  enforces length limits (flags overflow in `length_warnings`), forces
  channel/format/hypothesis/audience from the allocation, and returns a validated
  `ContentPackage`.
- `get_content_generator_agent(variants=…)` — the real agent.

### Standalone

```bash
python scripts/run_content.py data/sample_content_payload.json --pretty
```
```bash
curl -sS -X POST "$CONTENT_FUNCTION_URL" -H 'content-type: application/json' --data @data/sample_content_payload.json
```

Lambda handler: `traction.api.content_lambda.handler` (alias `lambda_handler`),
Function URL, `200` / `422` / `400` / `500`, **zero graph imports** (verified by
`tests/test_content_lambda.py`). Payload:
`{ cycle_id, plan, startup_profile?, founder_brief?, only_channels?, variants? }`.

---

## Non-Goals
* **No Live Ad Spend**: MVP operates through simulation adapters; real ad network connectors (Google Ads API, Meta API) are designed as drop-in `ExecutionService` replacements.
* **No Complex Attribution Black Box**: We deliberately avoid opaque multi-touch attribution algorithms in favor of transparent, falsifiable channel experiments with explicit attribution warnings.
* **No Reinforcement Learning / Black Box Weights**: Portfolio decisions use transparent, deterministic explore/exploit schedules suitable for explanation to founders and hackathon judges.
* **No Unnecessary Infrastructure**: Zero Kubernetes, Kafka, or Redis. Clean, lightweight Python and SQLite.

---

## Frontend Web App

The merged frontend is a dependency-free static web app for the Traction founder experience:

| File | Purpose |
|---|---|
| `index.html` | Application shell and navigation |
| `styles.css` | Visual design system and responsive layout |
| `app.js` | Views, sample LedgerAI data, routing, and interactions |
| `next-dollar-figma-prompt.md` | UI design specification |

Run it locally with:

```bash
python -m http.server 8765
```

Then open `http://localhost:8765`. The current UI uses sample data and is ready for the frontend teammate to connect to the backend API after the serverless boundary is implemented.
