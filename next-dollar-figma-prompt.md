# The Next Dollar — Figma UI Design Prompt

Design a web application UI for "The Next Dollar" — an AI agent that manages a small business founder's marketing budget as a portfolio of experiments. The user is a solo founder with no marketing background and a S$2,000/month budget. Every plan must be approved by the founder before any money is spent.

## Visual direction

Clean, calm, data-driven, trustworthy. Generous white space. Card-based layout on a white (#FFFFFF) canvas with subtle card borders (#C3CEDA, 1px) and very light shadows. No gradients, no decorative illustration. Numbers are the hero: use large, tabular-lining figures for money and percentages. Think a modern fintech dashboard, not a marketing tool.

## Colour system (use exactly)

- Primary text: #384655
- Secondary text / labels: #5F6E7E
- Headings / dark surfaces: #1F2A38
- Primary accent (buttons, active states, links): #0097A7
- Secondary accent (charts, highlights): #68DAF8
- Tint backgrounds (selected rows, info panels): #9FCBFD at 15–20% opacity
- Borders / dividers: #C3CEDA
- Human-action accent: #E8875B — reserve this ONLY for founder approval actions and "awaiting your approval" states, so the human-in-the-loop moments are visually distinct from everything the AI does.
- Verdict badges: SCALE = #0097A7, HOLD = #5F6E7E, CUT = #E8875B, INSUFFICIENT DATA = #C3CEDA with dark text.

## Typography

Arial (or Inter as a close web substitute). Clear hierarchy: page title 28px semibold, card title 16px semibold, body 14px, labels 12px uppercase tracked in #5F6E7E. Monetary values 24–32px medium.

## Layout

Left sidebar navigation (collapsed icons + labels), 240px, background #1F2A38 with white text, active item in #68DAF8. Main content area max-width 1200px with a 24px grid gap. Cards have 24px internal padding and 12px corner radius.

## Pages to design (6 screens, desktop 1440px)

### 1. Dashboard

- Top: a 5-step cycle status strip — Brief → Plan → Approve → Launch & Measure → Reflect — with the current step highlighted. Show "Cycle 4 of 12".
- Card: Budget overview — total budget S$2,000, a horizontal stacked bar of allocation by channel (Google Search, Founder Content, LinkedIn), and an explore/exploit split (e.g. 70% proven / 30% exploring).
- Card: Latest verdicts — one row per channel with verdict badge, confidence %, observed cost per signup vs target.
- Prominent card in #E8875B accent: "Plan for Cycle 5 is awaiting your approval" with a Review button.
- Small footer indicator: "Loop iteration 4 / 12".

### 2. Founder brief (onboarding form)

Multi-section form on a single scrolling page, each section a card: Product & buyer, Monthly budget, Goal & target cost per outcome, Starting allocation (optional), Hard exclusions (channels never to use — style these as red/locked chips), Soft preferences (channels the founder believes in — style as teal chips with a tooltip: "Protected for 2 cycles, then must earn its budget"). Primary button "Save brief".

### 3. Approval screen (the most important page)

- Header: "Cycle 5 plan — proposed by the agent". Strategy summary in one paragraph, and a "Major uncertainties" note.
- Main card: a comparison table with columns Channel | Current spend | Proposed spend | Change (S$) | Change (%) | Reason. Positive changes in #0097A7, negative in #E8875B. Reasons are short plain-language sentences from the agent, e.g. "Search delivered signups at S$45 vs S$120 target — scaling."
- Each row expands to show the hypothesis, audience, message angle, success threshold, and evaluation window (days).
- Edit mode: proposed spend cells become inputs. A helper line shows "Your edits total S$2,000.00 ✓" or a warning if not. Note in small text: "Edits are re-checked against your budget rules before anything runs."
- Bottom action bar, sticky: three buttons only — Reject (ghost), Edit (secondary), Approve (solid #E8875B). Approve is disabled while an edit is unsaved.
- Include a variant state showing a validation error returned after an edit: "Allocation to TikTok violates a hard exclusion" in an inline alert.

### 4. Content drafts

One card per channel showing the messaging the agent proposes: Hypothesis, Audience, Message angle — each editable inline. A banner clarifies these belong to "Cycle 5 plan (awaiting approval)". Save returns the user to the approval screen. Keep this page visually subordinate to the approval screen (a tab within it).

### 5. Analytics

- Card: Results table per cycle — channel, spend, outcomes, observed CAC, conversion rate, CTR, days observed, window complete (yes/no). Rows with incomplete windows are greyed with an "Evaluation window incomplete" badge.
- Card: Verdict history — a grid of channels (rows) × cycles (columns) filled with small verdict badges, showing e.g. Founder Content going HOLD → HOLD → CUT.
- Card: Cost per signup over time — line chart per channel in #0097A7 / #68DAF8 / #9FCBFD, with a dashed target line and a shaded benchmark band.
- Card: Learnings — a plain list of one-line lessons from past cycles.
- Card: Attribution note — a quiet info panel stating "Last-click attribution only" with any warnings.
- Card: Founder digest — rendered markdown of the weekly summary.

### 6. Agent activity (live event stream)

A read-only, timeline-style log. Each entry: timestamp, node name as a small mono-font chip (load_context, strategist, approval_gate, execute, measure, analyst, ledger, digest), and a one-line summary. A side panel shows the strategist's reasoning as it arrives. When the stream reaches the approval gate, the timeline pauses with an #E8875B marker "Waiting for founder approval" and a link to the approval screen. Show a "Self-repair attempt 1 of 3" chip on one entry to illustrate bounded retries. No controls on this page.

## Components to include

Verdict badge (4 variants), channel chip (normal / preferred / excluded), stat card, comparison table row (default / expanded / editing), inline alert (info / warning / error), sticky action bar, timeline entry, sidebar nav item.

## Sample data

Populate all screens with realistic sample data for a startup called "LedgerAI" (B2B accounting SaaS) running Google Search, Founder Content, and LinkedIn Ads.

---

## Tips for iterating in Figma Make

- Generate the approval screen first and get it right — the other five follow its table and badge styles.
- If the output looks too "AI-generic", add a line like: "no rounded-blob illustrations, no purple, no emoji."
