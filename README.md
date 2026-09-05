# The Next Dollar — "Traction" UI

A web UI for **The Next Dollar**: an AI agent that manages a small business founder's marketing budget as a portfolio of experiments. The founder sets a brief and a monthly budget (S$2,000), the agent proposes a channel allocation each cycle, and **nothing runs until the founder approves it**.

All screens are populated with sample data for **LedgerAI**, a B2B accounting SaaS running Google Search, Founder Content, and LinkedIn Ads.

The design follows [next-dollar-figma-prompt.md](next-dollar-figma-prompt.md) — see that file for the full colour system, typography, and screen specs.

## Tech stack

Plain HTML + CSS + vanilla JavaScript. No framework, no dependencies, no build step.

| File | Purpose |
|---|---|
| `index.html` | App shell — sidebar navigation, main content container |
| `styles.css` | Design system: colour tokens, cards, tables, badges, chips, buttons |
| `app.js` | All five views rendered as JS templates, hash routing, and interactions |

## Running it

Open `index.html` directly in a browser, or serve the folder:

```bash
python3 -m http.server 8765
# then visit http://localhost:8765
```

## Screens

Navigation is hash-based (`#brief`, `#dashboard`, `#approval`, `#analytics`, `#activity`).

### 1. Founder Brief (`#brief`)
Onboarding form that guides every agent decision: product & buyer, monthly budget, goal & target cost per signup, **hard exclusions** (🔒 channels the agent may never propose) and **soft preferences** (★ channels protected for 2 cycles). Chips can be added and removed.

### 2. Dashboard (`#dashboard`)
Cycle status stepper (Brief → Plan → Approve → Launch & Measure → Reflect), budget overview with allocation bar and explore/exploit split, latest verdicts per channel, and an orange banner when a plan is awaiting approval.

### 3. Approval (`#approval`)
The most important page. The agent's proposed Cycle 5 plan: strategy summary, major uncertainties, and an allocation-changes table (current vs proposed spend, change, plain-language reason). Rows expand to show the hypothesis, audience, message angle, success threshold, and evaluation window.

- **Edit mode** — proposed spend cells become inputs; the total is recalculated live and must equal S$2,000 before Approve enables.
- **Content Drafts tab** — the per-channel messaging the agent proposes, editable while the plan is pending.
- Sticky action bar: Reject / Edit / **Approve Cycle 5** (orange is reserved for founder actions).

### 4. Analytics (`#analytics`)
Results table per cycle (incomplete evaluation windows greyed out), verdict history grid (SCALE / HOLD / CUT / INSUFFICIENT DATA per channel per cycle), an SVG cost-per-signup chart with the S$120 target line, learnings, an attribution note, and the founder digest.

### 5. Agent Activity (`#activity`)
Read-only event stream for the planning run: timestamped timeline with node chips (`load_context`, `strategist`, `ledger`, `approval_gate`), a self-repair attempt marker, an orange pause at the approval gate linking to the approval screen, and a side panel with the strategist's reasoning.

## Design notes

- Colour accents are semantic: **teal** (`#0097A7`) for agent/positive states, **orange** (`#E8875B`) reserved exclusively for human-in-the-loop moments (approval buttons, awaiting-approval states).
- Cards on an off-white canvas, 12px radius, tabular figures for money.
- Font: Inter (Google Fonts) with Arial fallback.
