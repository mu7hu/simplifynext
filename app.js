/* ============================================================
   The Next Dollar — "Traction" single-page app (vanilla JS)
   ============================================================ */

// ---------- App state ----------
const state = {
  view: 'brief',
  approvalTab: 'plan',       // 'plan' | 'drafts'
  editMode: false,
  expandedRows: {},          // channel -> bool
  spends: { 'Google Search': 1200, 'Founder Content': 500, 'LinkedIn Ads': 300 },
  validationError: null,
  planStatus: 'pending',     // 'pending' | 'approved' | 'rejected'
  exclusions: ['TikTok', 'Influencer Marketing'],
  preferences: ['LinkedIn Ads', 'Founder Content'],
};

const BUDGET = 2000;
const CURRENT_SPEND = { 'Google Search': 900, 'Founder Content': 600, 'LinkedIn Ads': 500 };

const PLAN_ROWS = [
  {
    channel: 'Google Search',
    reason: 'Delivered signups at S$45 vs S$120 target — scaling up.',
    detail: {
      hypothesis: 'Branded and high-intent category keywords will keep delivering trial signups below S$60 CAC at higher spend.',
      audience: 'Singapore small business owners and accountants searching for bookkeeping and reconciliation software.',
      angle: '“Close your books in 3 hours, not 3 days.”',
      threshold: 'CAC ≤ S$120 per free trial signup.',
      window: '30 days',
    },
  },
  {
    channel: 'Founder Content',
    reason: 'CAC improving but still above target. Hold and observe.',
    detail: {
      hypothesis: 'Founder-authored posts build trust with SMB owners and convert at a steadily declining CAC.',
      audience: 'Accountants and SMB founders in Singapore following finance and operations topics.',
      angle: 'Behind-the-scenes of automating month-end close at a real small business.',
      threshold: 'CAC ≤ S$120 per free trial signup.',
      window: '30 days',
    },
  },
  {
    channel: 'LinkedIn Ads',
    reason: 'Only 8 days observed. Reducing to minimum while window completes.',
    detail: {
      hypothesis: 'Sponsored posts targeting finance roles can reach the ICP directly at acceptable CAC.',
      audience: 'Finance managers and accountants at companies with 1–20 employees in Singapore.',
      angle: '“Stop reconciling by hand.”',
      threshold: 'CAC ≤ S$120 per free trial signup.',
      window: '30 days (8 observed)',
    },
  },
];

const DRAFTS = [
  {
    channel: 'Google Search',
    hypothesis: 'Branded and high-intent category keywords will keep delivering trial signups below S$60 CAC at higher spend.',
    audience: 'Singapore small business owners and accountants searching for bookkeeping and reconciliation software.',
    angle: 'Close your books in 3 hours, not 3 days.',
  },
  {
    channel: 'Founder Content',
    hypothesis: 'Founder-authored posts build trust with SMB owners and convert at a steadily declining CAC.',
    audience: 'Accountants and SMB founders in Singapore following finance and operations topics.',
    angle: 'Behind-the-scenes of automating month-end close at a real small business.',
  },
  {
    channel: 'LinkedIn Ads',
    hypothesis: 'Sponsored posts targeting finance roles can reach the ICP directly at acceptable CAC.',
    audience: 'Finance managers and accountants at companies with 1–20 employees in Singapore.',
    angle: 'Stop reconciling by hand.',
  },
];

const RESULTS = [
  { cycle: 'C1', channel: 'Google Search',   spend: 'S$900',   signups: '7',  cac: 'S$128', cacTone: 'bad',  cvr: '2.1%', ctr: '4.2%', days: '30d ✓', complete: true,  verdict: 'HOLD' },
  { cycle: 'C1', channel: 'Founder Content', spend: 'S$600',   signups: '3',  cac: 'S$200', cacTone: 'bad',  cvr: '1.1%', ctr: '3.8%', days: '30d ✓', complete: true,  verdict: 'HOLD' },
  { cycle: 'C1', channel: 'LinkedIn Ads',    spend: 'S$500',   signups: '1',  cac: 'S$500', cacTone: 'bad',  cvr: '0.4%', ctr: '1.1%', days: '30d ✓', complete: true,  verdict: 'CUT' },
  { cycle: 'C2', channel: 'Google Search',   spend: 'S$1,100', signups: '14', cac: 'S$78',  cacTone: 'good', cvr: '3.2%', ctr: '5.1%', days: '30d ✓', complete: true,  verdict: 'SCALE' },
  { cycle: 'C2', channel: 'Founder Content', spend: 'S$600',   signups: '5',  cac: 'S$120', cacTone: 'good', cvr: '1.8%', ctr: '4%',   days: '30d ✓', complete: true,  verdict: 'HOLD' },
  { cycle: 'C2', channel: 'LinkedIn Ads',    spend: 'S$300',   signups: '—',  cac: '—',     cacTone: 'none', cvr: '—',    ctr: '0.6%', days: '30d ✓', complete: true,  verdict: 'CUT' },
  { cycle: 'C3', channel: 'Google Search',   spend: 'S$1,300', signups: '21', cac: 'S$61',  cacTone: 'good', cvr: '4%',   ctr: '5.8%', days: '30d ✓', complete: true,  verdict: 'SCALE' },
  { cycle: 'C3', channel: 'Founder Content', spend: 'S$500',   signups: '5',  cac: 'S$100', cacTone: 'good', cvr: '2%',   ctr: '3.5%', days: '30d ✓', complete: true,  verdict: 'HOLD' },
  { cycle: 'C3', channel: 'LinkedIn Ads',    spend: 'S$200',   signups: '2',  cac: 'S$100', cacTone: 'good', cvr: '1%',   ctr: '1.8%', days: '30d ✓', complete: true,  verdict: 'HOLD' },
  { cycle: 'C4', channel: 'Google Search',   spend: 'S$900',   signups: '20', cac: 'S$45',  cacTone: 'good', cvr: '4.5%', ctr: '6.1%', days: '22D / INCOMPLETE', complete: false, verdict: 'SCALE' },
  { cycle: 'C4', channel: 'Founder Content', spend: 'S$600',   signups: '6',  cac: 'S$100', cacTone: 'good', cvr: '2.1%', ctr: '3.9%', days: '22D / INCOMPLETE', complete: false, verdict: 'HOLD' },
  { cycle: 'C4', channel: 'LinkedIn Ads',    spend: 'S$500',   signups: '2',  cac: 'S$250', cacTone: 'bad',  cvr: '0.8%', ctr: '1.4%', days: '8D / INCOMPLETE',  complete: false, verdict: 'INSUFFICIENT DATA' },
];

const VERDICT_HISTORY = [
  { channel: 'Google Search',   cycles: ['HOLD', 'SCALE', 'SCALE', 'SCALE'] },
  { channel: 'Founder Content', cycles: ['HOLD', 'HOLD', 'HOLD', 'HOLD'] },
  { channel: 'LinkedIn Ads',    cycles: ['CUT', 'CUT', 'HOLD', 'INSUFFICIENT DATA'] },
];

const CHART_SERIES = [
  { name: 'Google Search',   color: '#0097A7', values: [128, 78, 61] },
  { name: 'Founder Content', color: '#68DAF8', values: [200, 120, 100] },
  { name: 'LinkedIn Ads',    color: '#9FCBFD', values: [500, null, 100] }, // null = no signups, CAC undefined
];

// ---------- Helpers ----------
const fmt = (n) => 'S$' + n.toLocaleString('en-US');

// "+S$300 (+33%)" / "−S$200 (−40%)"
function fmtDelta(proposed, current) {
  const delta = proposed - current;
  const pct = Math.round((delta / current) * 100);
  const sign = delta >= 0 ? '+' : '−';
  return `${sign}${fmt(Math.abs(delta))} (${sign}${Math.abs(pct)}%)`;
}

// Escape user-supplied text before interpolating into innerHTML
function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function badge(verdict) {
  const cls = {
    'SCALE': 'badge-scale',
    'HOLD': 'badge-hold',
    'CUT': 'badge-cut',
    'INSUFFICIENT DATA': 'badge-insufficient',
  }[verdict];
  return `<span class="badge ${cls}">${verdict}</span>`;
}

function showToast(msg) {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => t.classList.remove('show'), 2600);
}

function proposedTotal() {
  return Object.values(state.spends).reduce((a, b) => a + (Number(b) || 0), 0);
}

// ---------- Views ----------
function renderBrief() {
  const chip = (name, kind) => `
    <span class="chip ${kind === 'excluded' ? 'chip-excluded' : 'chip-preferred'}">
      <span>${kind === 'excluded' ? '🔒' : '★'}</span> ${esc(name)}
      <button class="chip-x" data-remove-chip="${kind}" data-name="${esc(name)}" aria-label="Remove ${esc(name)}">✕</button>
    </span>`;

  return `
  <div class="content-wrap">
    <header class="brief-header">
      <h1 class="page-title">Founder Brief</h1>
      <p class="page-sub">This brief guides every decision the agent makes. Update it anytime.</p>
    </header>

    <section class="card">
      <h2 class="card-title">Product &amp; Buyer</h2>
      <div class="form-field">
        <div class="form-grid-2">
          <div>
            <label class="field-label" for="productName">Product Name</label>
            <input type="text" id="productName" value="LedgerAI" />
          </div>
          <div>
            <label class="field-label" for="stage">Stage</label>
            <select id="stage">
              <option>Idea / pre-launch</option>
              <option selected>Early traction (0–100 customers)</option>
              <option>Growth (100+ customers)</option>
            </select>
          </div>
        </div>
      </div>
      <div class="form-field">
        <label class="field-label" for="icp">Ideal Customer Profile</label>
        <textarea id="icp">Small business owners and accountants at companies with 1–20 employees in Singapore who manage bookkeeping manually or with legacy software.</textarea>
      </div>
      <div class="form-field">
        <label class="field-label" for="cvp">Core Value Proposition</label>
        <textarea id="cvp">LedgerAI automates bank reconciliation and month-end close for small businesses — cutting close time from 3 days to 3 hours.</textarea>
      </div>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Monthly Budget</h2>
      <div class="budget-row" style="margin-top: 18px;">
        <span class="budget-currency">S$</span>
        <input type="number" id="budget" value="2000" />
        <span class="budget-hint">/ month. The agent will not exceed this total.</span>
      </div>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Goal &amp; Target</h2>
      <div class="goal-grid" style="margin-top: 18px;">
        <div class="goal-outcome">
          <label class="field-label" for="outcome">Primary Outcome</label>
          <select id="outcome">
            <option selected>Free trial signups</option>
            <option>Demo bookings</option>
            <option>Paid conversions</option>
          </select>
        </div>
        <div>
          <label class="field-label" for="targetCac">Target Cost Per Signup</label>
          <div class="goal-cac">
            <span class="budget-currency">S$</span>
            <input type="number" id="targetCac" value="120" />
          </div>
        </div>
      </div>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Hard Exclusions</h2>
      <p class="card-desc">The agent will never propose budget for these channels.</p>
      <div class="chip-row">${state.exclusions.map((n) => chip(n, 'excluded')).join('')}</div>
      <div class="chip-add-row">
        <input type="text" id="addExclusion" placeholder="Add channel..." />
        <button class="btn btn-ghost btn-add" data-add-chip="excluded">Add</button>
      </div>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Soft Preferences</h2>
      <p class="card-desc">Protected for 2 cycles, then must earn its budget on results.</p>
      <div class="chip-row">${state.preferences.map((n) => chip(n, 'preferred')).join('')}</div>
      <div class="chip-add-row">
        <input type="text" id="addPreference" placeholder="Add preferred channel..." />
        <button class="btn btn-ghost btn-add" data-add-chip="preferred">Add</button>
      </div>
    </section>

    <div class="brief-actions">
      <button class="btn btn-primary" data-action="save-brief">Save Brief</button>
    </div>
  </div>`;
}

function renderDashboard() {
  const steps = [
    { n: 1, name: 'Brief', cls: 'done' },
    { n: 2, name: 'Plan', cls: 'done' },
    { n: 3, name: 'Approve', cls: 'current' },
    { n: 4, name: 'Launch & Measure', cls: '' },
    { n: 5, name: 'Reflect', cls: '' },
  ];

  const alloc = [
    { name: 'Google Search', amount: 900, color: '#4B98A7' },
    { name: 'Founder Content', amount: 600, color: '#8DDCF0' },
    { name: 'LinkedIn Ads', amount: 500, color: '#A9C8F2' },
  ];

  const verdicts = [
    { channel: 'Google Search', verdict: 'SCALE', confidence: '87%', observed: 'S$45', obsTone: 'teal', target: 'S$120' },
    { channel: 'Founder Content', verdict: 'HOLD', confidence: '54%', observed: 'S$100', obsTone: 'teal', target: 'S$120' },
    { channel: 'LinkedIn Ads', verdict: 'INSUFFICIENT DATA', confidence: '31%', observed: 'S$250', obsTone: 'orange', target: 'S$120' },
  ];

  return `
  <div class="content-wrap">
    <section class="card cycle-card">
      <div class="cycle-head">
        <div class="cycle-title">Cycle 4 of 12</div>
        <div class="card-label">Current Status</div>
      </div>
      <div class="stepper">
        ${steps.map((s, i) => `
          ${i > 0 ? '<div class="step-connector"></div>' : ''}
          <div class="step ${s.cls}">
            <div class="step-num">${s.n}</div>
            <div class="step-name">${s.name}</div>
          </div>`).join('')}
      </div>
    </section>

    <div class="dash-grid">
      <section class="card">
        <div class="card-label">Budget Overview — Cycle 4</div>
        <div class="money-big">S$2,000<span class="money-per">/ month</span></div>
        <div class="alloc-bar">
          ${alloc.map((a) => `<span style="width:${(a.amount / 2000) * 100}%;background:${a.color}"></span>`).join('')}
        </div>
        ${alloc.map((a) => `
          <div class="legend-row">
            <div class="legend-left"><span class="legend-swatch" style="background:${a.color}"></span>${a.name}</div>
            <div class="legend-amount">${fmt(a.amount)}</div>
          </div>`).join('')}
        <hr class="dash-divider" />
        <div class="card-label">Explore / Exploit Split</div>
        <div class="split-bar">
          <span style="width:70%;background:#4B98A7"></span>
          <span style="width:30%;background:#8DDCF0"></span>
        </div>
        <div class="split-caption">
          <span class="proven">70% proven channels</span>
          <span class="exploring">30% exploring</span>
        </div>
      </section>

      <section class="card">
        <div class="card-label">Latest Verdicts — Cycle 4</div>
        ${verdicts.map((v) => `
          <div class="verdict-tile">
            <div class="verdict-tile-head">
              <div class="verdict-channel">${v.channel}</div>
              ${badge(v.verdict)}
            </div>
            <div class="verdict-stats">
              <div class="stat">
                <div class="stat-label">Confidence</div>
                <div class="stat-value">${v.confidence}</div>
              </div>
              <div class="stat">
                <div class="stat-label">Observed CAC</div>
                <div class="stat-value ${v.obsTone}">${v.observed}</div>
              </div>
              <div class="stat">
                <div class="stat-label">Target CAC</div>
                <div class="stat-value">${v.target}</div>
              </div>
            </div>
          </div>`).join('')}
      </section>
    </div>

    ${state.planStatus === 'pending' ? `
    <section class="approval-banner">
      <div class="banner-icon">◉</div>
      <div>
        <div class="banner-title">Plan for Cycle 5 is awaiting your approval</div>
        <div class="banner-sub">The agent has proposed a new allocation. Review before anything runs.</div>
      </div>
      <button class="btn btn-human" data-goto="approval">Review Plan →</button>
    </section>` : ''}
  </div>`;
}

function renderApproval() {
  const total = proposedTotal();
  const totalOk = total === BUDGET;

  const planRows = PLAN_ROWS.map((row) => {
    const current = CURRENT_SPEND[row.channel];
    const proposed = Number(state.spends[row.channel]) || 0;
    const changeCls = proposed >= current ? 'change-up' : 'change-down';
    const changeText = fmtDelta(proposed, current);
    const expanded = !!state.expandedRows[row.channel];

    const spendCell = state.editMode
      ? `<div class="spend-input-wrap">
           <span class="cur">S$</span>
           <input type="number" step="50" value="${proposed}" data-spend-input="${row.channel}" />
         </div>`
      : `<span class="cell-proposed">${fmt(proposed)}</span>`;

    const detailRow = expanded
      ? `<tr class="row-expanded"><td colspan="5">
           <dl class="expand-detail">
             <dt>Hypothesis</dt><dd>${row.detail.hypothesis}</dd>
             <dt>Audience</dt><dd>${row.detail.audience}</dd>
             <dt>Message angle</dt><dd>${row.detail.angle}</dd>
             <dt>Success threshold</dt><dd>${row.detail.threshold}</dd>
             <dt>Evaluation window</dt><dd>${row.detail.window}</dd>
           </dl>
         </td></tr>`
      : '';

    return `
      <tr>
        <td>
          <div class="cell-channel">${row.channel}</div>
          <button class="expand-toggle" data-expand="${row.channel}">
            <span class="tri">${expanded ? '▲' : '▼'}</span> ${expanded ? 'collapse' : 'expand'}
          </button>
        </td>
        <td class="num">${fmt(current)}</td>
        <td>${spendCell}</td>
        <td class="cell-change ${changeCls}">${changeText}</td>
        <td class="cell-reason">${row.reason}</td>
      </tr>
      ${detailRow}`;
  }).join('');

  const totalIndicator = state.editMode
    ? `<div class="alloc-total ${totalOk ? 'ok' : 'bad'}">
         Total: ${fmt(total)} ${totalOk ? '✓' : `— must equal ${fmt(BUDGET)}`}
       </div>`
    : '';

  const planTab = `
    <section class="card">
      <div class="card-label">Strategy Summary</div>
      <p class="strategy-text">
        Google Search has delivered signups consistently below the S$120 CAC target and is the primary
        scaling opportunity for Cycle 5. Founder Content is showing gradual improvement and is protected
        for one more cycle. LinkedIn Ads has insufficient data and will be maintained at a reduced
        exploratory budget while the evaluation window completes.
      </p>
      <div class="alert alert-warning">
        <span class="alert-icon">⚠</span><strong>Major uncertainties:</strong> LinkedIn Ads has only 8 days
        of observation. The proposed CPC on Google Search assumes continued Quality Score above 7 — a drop
        could raise CAC materially.
      </div>
    </section>

    <section class="card section-gap">
      <div class="alloc-head">
        <h2 class="card-title">Allocation changes</h2>
        ${totalIndicator}
      </div>
      ${state.validationError ? `<div class="alert alert-error"><span class="alert-icon">⚠</span>${state.validationError}</div>` : ''}
      <table class="table">
        <thead>
          <tr>
            <th>Channel</th>
            <th>Current Spend</th>
            <th>Proposed Spend</th>
            <th>Change</th>
            <th>Reason</th>
          </tr>
        </thead>
        <tbody>${planRows}</tbody>
      </table>
      ${state.editMode ? '<div class="table-footnote">Edits are re-checked against your budget rules before anything runs.</div>' : ''}
    </section>

    <div class="action-bar">
      <span class="action-note">Nothing runs until you approve. You can edit individual line items before approving.</span>
      <button class="btn btn-ghost" data-action="reject">Reject</button>
      ${state.editMode
        ? '<button class="btn btn-secondary" data-action="save-edits">Save edits</button>'
        : '<button class="btn btn-secondary" data-action="edit">Edit</button>'}
      <button class="btn btn-human" data-action="approve" ${state.editMode && !totalOk ? 'disabled' : ''}>Approve Cycle 5 →</button>
    </div>`;

  const draftsTab = `
    <div class="drafts-banner">These drafts belong to <strong>Cycle 5 plan (awaiting approval)</strong>. Nothing is published until the plan is approved.</div>
    ${DRAFTS.map((d) => `
      <section class="card section-gap">
        <h2 class="card-title">${d.channel}</h2>
        <div class="draft-field">
          <label class="field-label">Hypothesis</label>
          <textarea>${d.hypothesis}</textarea>
        </div>
        <div class="draft-field">
          <label class="field-label">Audience</label>
          <textarea>${d.audience}</textarea>
        </div>
        <div class="draft-field">
          <label class="field-label">Message angle</label>
          <input type="text" value="${d.angle}" />
        </div>
      </section>`).join('')}
    <div class="brief-actions">
      <button class="btn btn-primary" data-action="save-drafts">Save drafts</button>
    </div>`;

  const statusBadge = {
    pending: '<span class="badge badge-awaiting">Awaiting Your Approval</span>',
    approved: '<span class="badge badge-approved">Approved</span>',
    rejected: '<span class="badge badge-rejected">Rejected</span>',
  }[state.planStatus];

  return `
  <div class="content-wrap">
    <header class="approval-header">
      <h1 class="page-title">Cycle 5 plan</h1>
      ${statusBadge}
      <p class="approval-meta">Proposed by the agent · Generated 09:07 today</p>
    </header>

    <div class="tabs">
      <button class="tab ${state.approvalTab === 'plan' ? 'active' : ''}" data-tab="plan">Proposed Plan</button>
      <button class="tab ${state.approvalTab === 'drafts' ? 'active' : ''}" data-tab="drafts">Content Drafts</button>
    </div>

    ${state.approvalTab === 'plan' ? planTab : draftsTab}
  </div>`;
}

function renderChart() {
  const W = 1080, H = 420;
  const padL = 90, padR = 90, padT = 46, padB = 56;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const maxY = 500;
  const cycles = ['Cycle 1', 'Cycle 2', 'Cycle 3', 'Cycle 4'];
  const x = (i) => padL + (plotW / (cycles.length - 1)) * i;
  const y = (v) => padT + plotH - (v / maxY) * plotH;

  const gridVals = [100, 200, 300, 400, 500];
  const grid = gridVals.map((v) => `
    <line x1="${padL}" y1="${y(v)}" x2="${W - padR}" y2="${y(v)}" stroke="#EDF1F4" stroke-width="1"/>
    <text x="${padL - 14}" y="${y(v) + 5}" text-anchor="end" font-size="15" fill="#5F6E7E">S$${v}</text>`).join('');

  const band = `<rect x="${padL}" y="${y(132)}" width="${plotW + padR - 20}" height="${y(108) - y(132)}" fill="rgba(0,151,167,0.06)"/>`;
  const target = `
    <line x1="${padL}" y1="${y(120)}" x2="${W - 20}" y2="${y(120)}" stroke="#0097A7" stroke-width="2" stroke-dasharray="7 6"/>
    <text x="${W - 16}" y="${y(120) + 5}" font-size="14" fill="#5F6E7E">S$120</text>`;

  const series = CHART_SERIES.map((s) => {
    // A null value (no signups → CAC undefined) breaks the line and gets no dot
    const path = s.values.map((v, i) => {
      if (v == null) return '';
      const prevMissing = i === 0 || s.values[i - 1] == null;
      return `${prevMissing ? 'M' : 'L'}${x(i)},${y(v)}`;
    }).join(' ');
    const dots = s.values.map((v, i) => v == null ? '' : `
      <circle cx="${x(i)}" cy="${y(v)}" r="8" fill="#FFFFFF" stroke="${s.color}" stroke-width="3.5"/>
      <text x="${x(i)}" y="${y(v) - 16}" text-anchor="middle" font-size="15" font-weight="600" fill="${s.color}">S$${v}</text>`).join('');
    return `<path d="${path}" fill="none" stroke="${s.color}" stroke-width="3"/>${dots}`;
  }).join('');

  const xLabels = cycles.map((c, i) => `<text x="${x(i)}" y="${H - 16}" text-anchor="middle" font-size="16" fill="#5F6E7E">${c}</text>`).join('');

  return `
  <svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Cost per signup over time">
    ${grid}${band}
    <line x1="${padL}" y1="${padT + plotH}" x2="${W - padR}" y2="${padT + plotH}" stroke="#C3CEDA" stroke-width="1"/>
    ${target}${series}${xLabels}
  </svg>`;
}

function renderAnalytics() {
  const rows = RESULTS.map((r, idx) => `
    <tr class="${!r.complete ? 'row-incomplete' : ''} ${idx === 0 ? 'row-tint' : ''}">
      <td class="cell-cycle">${r.cycle}</td>
      <td class="cell-channel">${r.channel}</td>
      <td class="num">${r.spend}</td>
      <td class="num">${r.signups}</td>
      <td class="num ${r.cacTone === 'good' ? 'cac-good' : r.cacTone === 'bad' ? 'cac-bad' : ''}">${r.cac}</td>
      <td class="num">${r.cvr}</td>
      <td class="num">${r.ctr}</td>
      <td>${r.complete ? `<span class="num">${r.days}</span>` : `<span class="days-chip">${r.days}</span>`}</td>
      <td>${badge(r.verdict)}</td>
    </tr>`).join('');

  const historyRows = VERDICT_HISTORY.map((h) => `
    <tr>
      <td class="cell-channel">${h.channel}</td>
      ${h.cycles.map((v) => `<td>${badge(v)}</td>`).join('')}
    </tr>`).join('');

  return `
  <div class="content-wrap">
    <section class="card">
      <h2 class="card-title">Results by cycle</h2>
      <table class="table results-table">
        <thead>
          <tr>
            <th>Cycle</th><th>Channel</th><th>Spend</th><th>Signups</th><th>CAC</th>
            <th>CVR</th><th>CTR</th><th>Days</th><th>Verdict</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Verdict history</h2>
      <table class="table verdict-grid-table">
        <thead>
          <tr><th>Channel</th><th>Cycle 1</th><th>Cycle 2</th><th>Cycle 3</th><th>Cycle 4</th></tr>
        </thead>
        <tbody>${historyRows}</tbody>
      </table>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Cost per signup over time</h2>
      <p class="chart-sub">Completed cycles only · Dashed line = S$120 target · Gaps = no signups recorded</p>
      <div class="chart-wrap">${renderChart()}</div>
      <div class="chart-legend">
        ${CHART_SERIES.map((s) => `<span class="key"><span class="line" style="background:${s.color}"></span>${s.name}</span>`).join('')}
        <span class="key"><span class="line dashed"></span>S$120 target</span>
      </div>
    </section>

    <div class="analytics-bottom">
      <section class="card">
        <h2 class="card-title">Learnings</h2>
        <ul class="learnings-list">
          <li><span class="arrow">↗</span>Google Search branded terms convert 3× better than category terms for LedgerAI.</li>
          <li><span class="arrow">↗</span>Founder Content performs best when published Tuesday–Thursday mornings.</li>
          <li><span class="arrow">↗</span>LinkedIn Ads require ≥30 days to reach statistical significance at current budget.</li>
          <li><span class="arrow">↗</span>Signup-to-trial conversion drops when CAC exceeds S$120 — tighten audience segments.</li>
          <li><span class="arrow">↗</span>Re-targeting previous website visitors on Search cuts CAC by ~40%.</li>
        </ul>
      </section>

      <div>
        <div class="info-panel">
          <span class="info-icon">i</span>
          <span><strong>Attribution: Last-click only.</strong> Revenue from users who visited multiple times is attributed to the final channel. Multi-touch attribution is on the roadmap.</span>
        </div>

        <section class="card digest-card">
          <h2 class="digest-title">Founder digest — Cycle 4</h2>
          <div class="digest-week"><strong>Week ending Oct 4, 2025</strong></div>
          <p>Google Search is your engine right now. At S$45 CAC, it's beating the target by 2.6×. We're scaling it up.</p>
          <p>Founder Content continues to improve but slowly. CAC dropped from S$200 (Cycle 1) to S$100 this cycle. It's earning its keep — just not leading yet.</p>
          <p>LinkedIn Ads is inconclusive. We've reduced the budget to the minimum needed to complete the evaluation window. One more cycle will tell us whether to cut it.</p>
        </section>
      </div>
    </div>
  </div>`;
}

function renderActivity() {
  const entries = [
    {
      time: '09:02', dot: '', cardCls: '',
      chips: '<span class="node-chip">load_context</span>',
      summary: 'Loaded Cycle 3 results, founder brief, and budget ledger.',
    },
    {
      time: '09:02', dot: 'teal', cardCls: 'tl-active',
      chips: '<span class="node-chip">strategist</span>',
      summary: 'Analysing performance data for 3 channels across 22-day window.',
    },
    {
      time: '09:04', dot: '', cardCls: '',
      chips: '<span class="node-chip">strategist</span>',
      summary: 'Generating Cycle 5 allocation proposal. Confidence: 87% on Google Search.',
    },
    {
      time: '09:06', dot: '', cardCls: '',
      chips: '<span class="node-chip">ledger</span><span class="repair-chip">Self-repair attempt 1 of 3</span>',
      summary: 'Budget validation passed. Total proposed: S$2,000.00.',
    },
    {
      time: '09:07', dot: 'orange', cardCls: 'tl-gate',
      chips: '<span class="node-chip">approval_gate</span><span class="gate-chip">⏸ Waiting for Founder Approval</span>',
      summary: 'Plan submitted. Waiting for founder approval.',
      link: '<a href="#approval" class="tl-link">→ Go to approval screen</a>',
    },
  ];

  const reasoning = [
    'Loading Cycle 3 data...',
    '',
    'Google Search',
    '  CAC: S$61 (target S$120)',
    '  Confidence: 87%',
    '  → SCALE eligible',
    '',
    'Founder Content',
    '  CAC: S$100 (target S$120)',
    '  Confidence: 54%',
    '  → HOLD — improving',
    '',
    'LinkedIn Ads',
    '  Days observed: 8',
    '  → INSUFFICIENT DATA',
    '  → Maintain minimum budget',
    '',
    'Proposing: GS +S$300, FC −S$100, LI −S$200...',
  ].join('\n');

  return `
  <div class="content-wrap">
    <header>
      <h1 class="page-title">Agent Activity</h1>
      <p class="page-sub">Read-only event stream for Cycle 5 planning run.</p>
    </header>

    <div class="activity-layout">
      <div class="timeline">
        ${entries.map((e) => `
          <div class="timeline-entry">
            <div class="tl-time">${e.time}</div>
            <div class="tl-rail">
              <span class="tl-dot ${e.dot}"></span>
              <span class="tl-line"></span>
            </div>
            <div class="tl-card ${e.cardCls}">
              <div class="tl-chips">${e.chips}</div>
              <div class="tl-summary">${e.summary}</div>
              ${e.link || ''}
            </div>
          </div>`).join('')}
      </div>

      <aside class="card reasoning-panel">
        <div class="card-label">Strategist Reasoning</div>
        <div class="reasoning-body">${reasoning}</div>
      </aside>
    </div>
  </div>`;
}

// ---------- Router / renderer ----------
const VIEWS = {
  brief: renderBrief,
  dashboard: renderDashboard,
  approval: renderApproval,
  analytics: renderAnalytics,
  activity: renderActivity,
};

function render() {
  document.getElementById('main').innerHTML = VIEWS[state.view]();
  document.querySelectorAll('.nav-item').forEach((el) => {
    el.classList.toggle('active', el.dataset.view === state.view);
  });
  // Sidebar badge = number of plans waiting on the founder
  const pending = state.planStatus === 'pending' ? 1 : 0;
  const navBadge = document.getElementById('navBadge');
  navBadge.textContent = pending;
  navBadge.hidden = pending === 0;
  window.scrollTo(0, 0);
}

function toggleHelp(open) {
  const panel = document.getElementById('helpPanel');
  const fab = document.querySelector('.help-fab');
  const show = open == null ? panel.hidden : open;
  panel.hidden = !show;
  fab.setAttribute('aria-expanded', String(show));
}

function navigate(view) {
  if (!VIEWS[view]) view = 'brief';
  state.view = view;
  if (location.hash !== '#' + view) history.replaceState(null, '', '#' + view);
  render();
}

window.addEventListener('hashchange', () => navigate(location.hash.slice(1)));

// ---------- Event delegation ----------
document.addEventListener('click', (e) => {
  if (e.target.closest('.help-fab')) { toggleHelp(); return; }
  if (e.target.closest('[data-close-help]')) { toggleHelp(false); return; }
  if (!e.target.closest('#helpPanel')) toggleHelp(false);

  const navItem = e.target.closest('.nav-item');
  if (navItem) {
    e.preventDefault();
    navigate(navItem.dataset.view);
    return;
  }

  const goto = e.target.closest('[data-goto]');
  if (goto) { navigate(goto.dataset.goto); return; }

  const tlLink = e.target.closest('.tl-link');
  if (tlLink) { e.preventDefault(); navigate('approval'); return; }

  const tab = e.target.closest('[data-tab]');
  if (tab) { state.approvalTab = tab.dataset.tab; render(); return; }

  const expand = e.target.closest('[data-expand]');
  if (expand) {
    const ch = expand.dataset.expand;
    state.expandedRows[ch] = !state.expandedRows[ch];
    render();
    return;
  }

  const removeChip = e.target.closest('[data-remove-chip]');
  if (removeChip) {
    const list = removeChip.dataset.removeChip === 'excluded' ? state.exclusions : state.preferences;
    const i = list.indexOf(removeChip.dataset.name);
    if (i > -1) list.splice(i, 1);
    render();
    return;
  }

  const addChip = e.target.closest('[data-add-chip]');
  if (addChip) {
    const kind = addChip.dataset.addChip;
    const input = document.getElementById(kind === 'excluded' ? 'addExclusion' : 'addPreference');
    const name = input.value.trim();
    if (!name) return;
    (kind === 'excluded' ? state.exclusions : state.preferences).push(name);
    render();
    return;
  }

  const action = e.target.closest('[data-action]');
  if (!action) return;

  switch (action.dataset.action) {
    case 'save-brief':
      showToast('Brief saved. The agent will use it from the next planning run.');
      break;
    case 'edit':
      state.editMode = true;
      state.validationError = null;
      render();
      break;
    case 'save-edits': {
      const total = proposedTotal();
      if (total !== BUDGET) {
        state.validationError = `Your edits total ${fmt(total)} — the plan must equal ${fmt(BUDGET)}.`;
      } else {
        state.editMode = false;
        state.validationError = null;
        showToast('Edits saved and re-checked against your budget rules.');
      }
      render();
      break;
    }
    case 'reject':
      state.planStatus = 'rejected';
      state.editMode = false;
      showToast('Plan rejected. The agent will draft a revised proposal.');
      render();
      break;
    case 'approve':
      if (action.disabled) return;
      state.planStatus = 'approved';
      state.editMode = false;
      showToast('Cycle 5 plan approved. Launching channels…');
      render();
      break;
    case 'save-drafts':
      state.approvalTab = 'plan';
      showToast('Drafts saved to Cycle 5 plan.');
      render();
      break;
  }
});

// Live-update proposed spend totals while editing
document.addEventListener('input', (e) => {
  const spendInput = e.target.closest('[data-spend-input]');
  if (!spendInput) return;
  state.spends[spendInput.dataset.spendInput] = Number(spendInput.value) || 0;

  // Update the total indicator + change cells in place (avoid full re-render to keep focus)
  const total = proposedTotal();
  const indicator = document.querySelector('.alloc-total');
  if (indicator) {
    const ok = total === BUDGET;
    indicator.className = 'alloc-total ' + (ok ? 'ok' : 'bad');
    indicator.textContent = ok ? `Total: ${fmt(total)} ✓` : `Total: ${fmt(total)} — must equal ${fmt(BUDGET)}`;
  }
  const approveBtn = document.querySelector('[data-action="approve"]');
  if (approveBtn) approveBtn.disabled = total !== BUDGET;

  const row = spendInput.closest('tr');
  const changeCell = row && row.querySelector('.cell-change');
  if (changeCell) {
    const current = CURRENT_SPEND[spendInput.dataset.spendInput];
    const proposed = Number(spendInput.value) || 0;
    changeCell.className = 'cell-change ' + (proposed >= current ? 'change-up' : 'change-down');
    changeCell.textContent = fmtDelta(proposed, current);
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') toggleHelp(false);
});

// ---------- Boot ----------
navigate(location.hash.slice(1) || 'brief');
