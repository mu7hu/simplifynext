# Traction testing guide

This guide tests the strategy/orchestration side from a clean checkout through the complete offline workflow. It uses deterministic stubs and does not require AWS credentials.

## 1. Prepare a clean local environment

From PowerShell:

```powershell
cd C:\Users\Muthu\Desktop\NTU\simplifynext
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
```

If PowerShell blocks activation, run the commands in Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

Ensure offline mode is enabled. Copy `.env.example` to `.env` if needed and keep:

```text
USE_STUB_MODELS=true
AWS_DEFAULT_REGION=ap-southeast-1
```

## 2. Run all automated tests first

```powershell
python -m pytest -q
```

Expected baseline: `19 passed`.

For detailed output:

```powershell
python -m pytest -v
```

Run each area independently:

```powershell
python -m pytest tests/test_schemas.py -v       # Pydantic contracts
python -m pytest tests/test_constraints.py -v   # budget and exclusions
python -m pytest tests/test_strategist.py -v    # planning and cycle-4 challenge
python -m pytest tests/test_ledger.py -v        # SQLite persistence
python -m pytest tests/test_simulator.py -v     # seeded market behavior
python -m pytest tests/test_analyst.py -v       # teammate stub interface
python -m pytest tests/test_graph.py -v         # end-to-end graph cycle
python -m pytest tests/test_loop_bounds.py -v   # retry and iteration caps
python -m pytest tests/test_evaluation.py -v    # benchmark metrics
```

## 3. Test the schemas directly

The shared contract files are in `src/traction/schemas/`:

```powershell
python -c "from traction.schemas.experiment import *; p=ExperimentPlan(cycle_id=1,total_budget=100,primary_goal='Demos',allocations=[],exploration_budget_pct=0,exploitation_budget_pct=0,strategy_summary='test'); print(p.model_dump())"
```

Expected: a printed validated `ExperimentPlan`.

Negative values should fail validation:

```powershell
python -c "from traction.schemas.experiment import Allocation,Channel; Allocation(channel=Channel.META,experiment_id='x',current_budget=0,proposed_budget=-1,proposed_share=0,hypothesis='x',audience='x',message_angle='x',success_threshold=1,reason='x',evidence_used='x')"
```

Expected: a Pydantic `ValidationError`.

## 4. Test the deterministic constraint engine

The implementation is in `src/traction/constraints/budget.py`.

```powershell
python -c "from traction.services.intake import MockIntakeProvider; from traction.services.profiler import MockProfilerService; from traction.agents.strategist import StrategistAgent; from traction.schemas.ledger import HistoricalSummary; from traction.constraints.budget import validate_plan_constraints; b=MockIntakeProvider().get_founder_brief('ledger_ai'); p=MockProfilerService(); plan=StrategistAgent().plan_cycle(1,b,p.get_startup_profile('ledger_ai'),p.get_benchmark_priors('ledger_ai'),HistoricalSummary(startup_id='ledger_ai',total_cycles_completed=0,total_spend=0,total_outcomes=0,lifetime_cac=0),[]); print(validate_plan_constraints(plan,b))"
```

Expected: `(True, [])`.

The automated constraint tests also cover:

- exact budget totals
- excluded channels
- negative spend
- minimum active-channel spend
- maximum channel concentration
- exploration floor

## 5. Test the Strategist Agent

The Strategist is in `src/traction/agents/strategist.py`. Its local model is deterministic.

```powershell
python -m pytest tests/test_strategist.py -v
```

What to check manually:

```powershell
python -c "from traction.agents.strategist import StrategistAgent; from traction.services.intake import MockIntakeProvider; from traction.services.profiler import MockProfilerService; from traction.schemas.ledger import HistoricalSummary; b=MockIntakeProvider().get_founder_brief('ledger_ai'); pr=MockProfilerService(); a=StrategistAgent(); h=HistoricalSummary(startup_id='ledger_ai',total_cycles_completed=0,total_spend=0,total_outcomes=0,lifetime_cac=0); x=a.plan_cycle(1,b,pr.get_startup_profile('ledger_ai'),pr.get_benchmark_priors('ledger_ai'),h,[]); print([(z.channel.value,z.proposed_budget,z.proposed_share) for z in x.allocations]); print(x.strategy_summary)"
```

Expected Cycle 1 behavior: Founder Content receives a meaningful allocation and the total is exactly S$2,000.

Cycle 4 behavior:

```powershell
python -m pytest tests/test_strategist.py::test_strategist_challenges_founder_in_cycle_4 -v
```

Expected: Founder Content is reduced to 10% and the reason mentions approximately `3x` higher cost.

## 6. Test the policy and baselines

```powershell
python -m pytest tests/test_constraints.py tests/test_evaluation.py -v
```

The baseline implementations are in `src/traction/baselines/allocators.py`:

- `EqualSplitAllocator`
- `FounderSplitAllocator`
- `GreedyLastWinnerAllocator`
- `OracleAllocator`

Oracle is evaluation-only. Its ground truth must never be passed into the normal graph or Strategist prompt.

## 7. Test the ledger

```powershell
python -m pytest tests/test_ledger.py -v
```

The SQLite implementation is in `src/traction/ledger/sqlite.py`. The tests verify that plans, results, analyses, historical summaries, learnings, and failed hypotheses can be persisted and retrieved.

For manual inspection after a demo:

```powershell
python scripts/run_demo.py
python -c "import sqlite3; c=sqlite3.connect('data/demo_traction.db'); print(c.execute(\"select startup_id,cycle_id,channel,planned_budget,verdict from ledger_entries order by cycle_id\").fetchall())"
```

## 8. Test the approval gate

Headless approval is used by the demo:

```powershell
python -m pytest tests/test_graph.py -v
```

The approval interfaces are in `src/traction/approval/`. `AutoApprovalGate` approves test runs. `CLIApprovalGate` displays current spend, proposed spend, dollar movement, percentage movement, and rationale.

To test the interactive gate:

```powershell
python -c "from traction.approval.cli import CLIApprovalGate; print('CLIApprovalGate loaded:', CLIApprovalGate)"
```

Execution must occur only after approval. The graph node revalidates edited allocations before marking them approved.

## 9. Test every graph step

The graph is built in `src/traction/graph/build.py`; nodes are in `src/traction/graph/nodes.py`.

```text
START
  ↓
load_context
  ↓
strategist
  ↓
validate_plan ── invalid ──► strategist_repair ──► validate_plan
  ↓ valid
approval_gate ── reject/edit-invalid ──► founder_revision ──► strategist
  ↓ approved
execute
  ↓
measure
  ↓
analyst
  ↓
validate_analysis
  ↓
persist_ledger
  ↓
generate_digest
  ↓
END or next cycle
```

Run the graph test:

```powershell
python -m pytest tests/test_graph.py -v
```

Check graph events interactively:

```powershell
python -c "from traction.api.agentcore_app import entrypoint; r=entrypoint({'startup_id':'ledger_ai','cycle_id':1,'total_budget':2000,'auto_approve':True}); print(r['approval_status'],r['events_count'],len(r['verdicts']))"
```

Expected: `APPROVED`, a positive event count, and 5 channel verdicts.

## 10. Test loop bounds

```powershell
python -m pytest tests/test_loop_bounds.py -v
```

The safety limits are controlled by `.env`:

```text
MAX_AGENT_RETRIES=2
MAX_GRAPH_ITERATIONS=20
```

The system must terminate when either limit is reached. It must never create an autonomous infinite cycle.

## 11. Run the complete local demo

```powershell
python scripts/run_demo.py
```

Expected story:

```text
Cycle 1: founder preference respected
Cycle 2: Google Search begins gaining budget
Cycle 3: evidence accumulates
Cycle 4: Founder Content reduced and Google scaled
Cycle 5: informed portfolio continues
```

The demo writes `data/demo_traction.db` and proves the full offline workflow.

## 12. Run one cycle through the AgentCore-compatible entrypoint

```powershell
python scripts/run_cycle.py --startup-id ledger_ai --cycle-id 1 --budget 2000
```

Also test budget normalization:

```powershell
python scripts/run_cycle.py --startup-id ledger_ai --cycle-id 4 --budget 1000
```

Expected: the plan completes and total proposed spend is S$1,000.

## 13. Run the evaluation harness

```powershell
python scripts/run_evaluation.py --startups 5 --cycles 6
```

Expected outputs:

- `eval_results.csv`
- `eval_summary.json`

The report compares Oracle, Equal Split, Founder Split, Greedy Winner, and Traction. It reports outcomes, CAC, regret, cycles to best channel, allocation distance, and agent quality metrics.

## 14. Live Bedrock testing, only when credentials are available

Do not start here. First make all offline tests pass. Then configure `.env`:

```text
USE_STUB_MODELS=false
AWS_PROFILE=your-profile
AWS_DEFAULT_REGION=ap-southeast-1
```

Confirm credentials separately:

```powershell
aws sts get-caller-identity --profile your-profile
```

Then run a single cycle. Do not use live mode for the default test suite; tests should remain offline and deterministic.

## 15. Before merging your friend's branch

Run this sequence on the integration branch:

```powershell
python -m pytest -q
python scripts/run_demo.py
python scripts/run_cycle.py --startup-id ledger_ai --cycle-id 1 --budget 2000
python scripts/run_evaluation.py --startups 5 --cycles 6
python -m compileall -q src scripts
```

Only merge when all commands succeed. If a teammate component changes a shared schema, add/update contract tests before resolving the merge.
