# The Next Dollar — "Augury" UI

A web UI for **The Next Dollar**: an AI agent that manages a small business founder's marketing budget as a portfolio of experiments. The founder sets a brief and a monthly budget (S$2,000), the agent proposes a channel allocation each cycle, and **nothing runs until the founder approves it**.

All screens are populated with sample data for **LedgerAI**, a B2B accounting SaaS running Google Search, Founder Content, and LinkedIn Ads.

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

## Finding your way around

Everything lives behind the **dark sidebar on the left**. Click any of the five items — Founder Brief, Dashboard, Approval, Analytics, Agent Activity — to switch pages. A few things to know before you start:

- The **orange number badge** next to *Approval* means a plan is waiting for your decision. Orange always means "this needs a human" — anything the agent does on its own is shown in teal or grey.
- At the **bottom of the sidebar** you'll find a light/dark mode switch and a progress bar showing how far through the 12 cycles you are. The **arrows next to the logo** shrink the sidebar down to icons if you want more room.
- The **? button** in the bottom-right corner opens a short explainer of how the whole loop works (Brief → Plan → Approve → Launch & Measure → Reflect) and what the verdict badges mean.

## A tour of the five pages

### 1. Founder Brief — tell the agent about your business
This is where you set the ground rules; the agent consults them for every plan it writes.

- Fill in your **startup name, stage and one-line pitch** — the agent writes its ad audiences and hypotheses from this.
- Set the **budget per cycle** (every plan must add up to exactly this amount) and your **goal**: what outcome you're buying, what you're willing to pay for each one, and the minimum number you expect per cycle.
- **Hard Exclusions** (🔒): channels the agent is *never* allowed to spend on. Pick a channel, give a reason, hit **Add**. Remove one with the ✕.
- **Soft Preferences** (★): channels you personally believe in. Choose a belief strength and say why — the agent gives them the benefit of the doubt for the first two cycles, after which they have to earn their budget like everything else.
- Press **Save Brief** when you're done.

### 2. Dashboard — your at-a-glance home page
The top banner shows which cycle you're in, the budget under management, and a small trend chart of your blended cost per signup since Cycle 1. Below that:

- A **progress strip** showing where the current cycle is in the loop (the highlighted step is where things are right now).
- **Budget overview** — how this month's money is split across channels, plus how much is going to proven channels vs. experiments.
- **Latest verdicts** — one tile per channel with the agent's confidence and what each signup actually cost versus your target.
- If a plan is waiting for you, an **orange banner** appears at the bottom — click **Review Plan** to jump straight to it.

### 3. Approval — where you decide (the most important page)
Nothing spends a dollar until you act here. The page opens on the **Proposed Plan** tab:

- Read the **strategy summary** and the highlighted **major uncertainties** — the agent's honest caveats.
- The **before/after bars** and the **allocation table** show what the agent wants to change for each channel, by how much, and its one-line reason. Click **Show details** on any row to see the full thinking: the hypothesis, target audience, message angle, what success looks like, and how long it will be measured.
- **Want to change the numbers?** Click **Edit** — the proposed amounts become typeable. A running total tells you when your edits add up to the budget; the Approve button stays locked until they do. **Save edits** re-checks them against your budget rules.
- **Don't like the plan?** Click **Reject** — you'll be asked to leave a short note explaining why, and the agent uses your feedback to draft a new plan.
- **Happy with it?** Click the orange **Approve Cycle 5** button and the channels launch.

The second tab, **Content Drafts**, shows the actual creative the agent wants to run — search ads, LinkedIn posts, emails and more, one card per channel. Flip between **variants** with the tabs on each card, check the character counters (they warn you if something is too long for its platform), and read the targeting and compliance notes. Use **Generate / Regenerate** if you want fresh alternatives. These drafts belong to the pending plan — none of them go live until you approve.

### 4. Analytics — how it's all going
Your results, cycle by cycle:

- **Results by cycle** — every channel's spend, signups, cost per signup and clickthrough rates. Rows that are still mid-measurement are greyed out and labelled so you don't judge them early. A small ⓘ flag warns you where two channels' audiences overlapped and may blur the numbers.
- **Verdict history** — a simple grid showing how each channel's verdict (SCALE / HOLD / CUT / INSUFFICIENT DATA) has evolved over the cycles.
- **Cost per signup over time** — a chart of each channel against the dashed target line. Hover over any point for the exact numbers.
- **Learnings** — one-line lessons the agent has banked from past cycles.
- **Weekly digest** — a plain-English summary of the cycle: the TL;DR, each channel's verdict and why, and the agent's recommendations for next cycle (which, as always, only take effect after you approve them).

### 5. Agent Activity — watch the agent work
A read-only play-by-play of the planning run. Each timestamped entry shows what the agent did — loading your history, drafting the plan, checking it against your budget rules. You can even see it **catch and fix its own mistake** (a plan that didn't add up gets flagged and repaired, with a retry counter). The stream always ends at an orange **"Waiting for Founder Approval"** entry with a shortcut to the Approval page — a reminder that the agent proposes, but you decide. The panel on the right shows the actual context the agent reasoned over.

