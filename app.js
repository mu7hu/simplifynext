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

// Inline SVG icons (Lucide-style, 24px grid, stroke-based). Decorative by default.
const ICON_PATHS = {
  lock: '<rect width="18" height="11" x="3" y="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
  star: '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  chevronDown: '<path d="m6 9 6 6 6-6"/>',
  arrowRight: '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
  alert: '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  info: '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  trendUp: '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
  pause: '<rect x="14" y="4" width="4" height="16" rx="1"/><rect x="6" y="4" width="4" height="16" rx="1"/>',
  fileText: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/>',
  trendDown: '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  target: '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
  wallet: '<path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/>',
  rocket: '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
};

// Animated count-up for any element carrying data-count. The final formatted value is
// already in the markup, so the number is correct before JS runs and for reduced-motion users.
function animateCounters(root) {
  const els = root.querySelectorAll('[data-count]');
  if (!els.length) return;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  els.forEach((el, idx) => {
    const target = Number(el.dataset.count);
    if (!Number.isFinite(target)) return;
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const format = (v) => prefix + Math.round(v).toLocaleString('en-US') + suffix;
    if (reduce || target === 0) { el.textContent = format(target); return; }
    const dur = Number(el.dataset.duration || 1200);
    const start = performance.now() + Math.min(idx * 45, 500);
    el.textContent = format(0);
    const tick = (now) => {
      const t = Math.min(1, Math.max(0, (now - start) / dur));
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = format(target * eased);
      if (t < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

// Markup helpers shared by the page renderers
function pageEyebrow(text, tone = '') {
  return `<div class="page-eyebrow"><span class="dot ${tone}"></span>${text}</div>`;
}

function cardTitle(text, iconName, tone = '') {
  return `<div class="card-title-row">
    <span class="title-icon ${tone}" aria-hidden="true">${icon(iconName)}</span>
    <h2 class="card-title">${text}</h2>
  </div>`;
}

// Markup helper: a number that counts up on view entry
function countUp(value, prefix = '', suffix = '') {
  return `<span class="count" data-count="${value}" data-prefix="${prefix}" data-suffix="${suffix}">${prefix}${Number(value).toLocaleString('en-US')}${suffix}</span>`;
}

function icon(name, cls = '') {
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON_PATHS[name]}</svg>`;
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
      ${icon(kind === 'excluded' ? 'lock' : 'star', 'chip-icon')} ${esc(name)}
      <button class="chip-x" type="button" data-remove-chip="${kind}" data-name="${esc(name)}" aria-label="Remove ${esc(name)}">${icon('x')}</button>
    </span>`;

  return `
  <div class="content-wrap">
    <header class="page-head">
      ${pageEyebrow('Step 1 · Brief')}
      <h1 class="page-title">Founder Brief</h1>
      <p class="page-sub">This brief guides every decision the agent makes. Update it anytime.</p>
    </header>

    <section class="card card-accent">
      ${cardTitle('Product &amp; Buyer', 'fileText')}
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
      ${cardTitle('Monthly Budget', 'wallet', 'navy')}
      <div class="budget-panel">
        <div class="budget-row">
          <span class="budget-currency">S$</span>
          <input type="number" id="budget" value="2000" />
          <span class="budget-hint">/ month. The agent will not exceed this total.</span>
        </div>
      </div>
    </section>

    <section class="card section-gap">
      ${cardTitle('Goal &amp; Target', 'target', 'blue')}
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
      ${cardTitle('Hard Exclusions', 'lock', 'orange')}
      <p class="card-desc">The agent will never propose budget for these channels.</p>
      <div class="chip-row">${state.exclusions.map((n) => chip(n, 'excluded')).join('')}</div>
      <div class="chip-add-row">
        <input type="text" id="addExclusion" placeholder="Add channel..." />
        <button class="btn btn-ghost btn-add" type="button" data-add-chip="excluded">${icon('plus')}Add</button>
      </div>
    </section>

    <section class="card section-gap">
      ${cardTitle('Soft Preferences', 'star', 'light')}
      <p class="card-desc">Protected for 2 cycles, then must earn its budget on results.</p>
      <div class="chip-row">${state.preferences.map((n) => chip(n, 'preferred')).join('')}</div>
      <div class="chip-add-row">
        <input type="text" id="addPreference" placeholder="Add preferred channel..." />
        <button class="btn btn-ghost btn-add" type="button" data-add-chip="preferred">${icon('plus')}Add</button>
      </div>
    </section>

    <div class="brief-actions">
      <button class="btn btn-primary" data-action="save-brief">Save Brief</button>
    </div>
  </div>`;
}

// Compact area chart in the hero band: blended CAC per completed cycle
function renderHeroChart() {
  const vals = [182, 105, 71, 71];
  const W = 320, H = 118, padL = 14, padR = 14, padT = 18, padB = 24;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const maxY = 220;
  const baseY = padT + plotH;
  const x = (i) => padL + (plotW / (vals.length - 1)) * i;
  const y = (v) => padT + plotH - (v / maxY) * plotH;
  const line = vals.map((v, i) => `${i ? 'L' : 'M'}${x(i)},${y(v)}`).join(' ');
  const area = `${line} L${x(vals.length - 1)},${baseY} L${x(0)},${baseY} Z`;
  const last = vals.length - 1;

  return `
  <svg class="hero-spark" viewBox="0 0 ${W} ${H}" width="100%" role="img"
       aria-label="Blended cost per signup fell from S$182 in Cycle 1 to S$71 in Cycle 4">
    <defs>
      <linearGradient id="heroArea" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#68DAF8" stop-opacity="0.5"/>
        <stop offset="1" stop-color="#68DAF8" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <line x1="${padL}" x2="${W - padR}" y1="${y(120)}" y2="${y(120)}" stroke="rgba(255,255,255,0.28)" stroke-width="1" stroke-dasharray="4 5"/>
    <text x="${W - padR}" y="${y(120) - 6}" text-anchor="end" font-size="10" font-weight="600" fill="rgba(255,255,255,0.5)">S$120 TARGET</text>
    <path class="chart-area" d="${area}" fill="url(#heroArea)"/>
    <path class="chart-line" pathLength="1" d="${line}" fill="none" stroke="#68DAF8" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    ${vals.map((v, i) => `
      ${i === last ? `<circle class="chart-pt" style="--i:${i}" cx="${x(i)}" cy="${y(v)}" r="11" fill="rgba(104,218,248,0.18)"/>` : ''}
      <circle class="chart-pt" style="--i:${i}" cx="${x(i)}" cy="${y(v)}" r="${i === last ? 5 : 3.5}" fill="#1F2A38" stroke="#68DAF8" stroke-width="2"/>
      <text x="${x(i)}" y="${H - 6}" text-anchor="middle" font-size="10.5" font-weight="600" fill="rgba(255,255,255,0.45)">C${i + 1}</text>`).join('')}
  </svg>`;
}

function renderDashboard() {
  const status = state.planStatus;
  const pending = status === 'pending';

  // The stepper follows the plan's status so the page stays truthful after approve / reject
  const stepCls = {
    pending:  ['done', 'done', 'current', '', ''],
    approved: ['done', 'done', 'done', 'current', ''],
    rejected: ['done', 'current', '', '', ''],
  }[status];
  const steps = ['Brief', 'Plan', 'Approve', 'Launch & Measure', 'Reflect']
    .map((name, i) => ({ n: i + 1, name, cls: stepCls[i] }));

  const pill = {
    pending:  { cls: 'orange', icon: 'clock',  text: 'Step 3 · Approve — waiting on you' },
    approved: { cls: 'teal',   icon: 'rocket', text: 'Cycle 5 approved — launching channels' },
    rejected: { cls: 'grey',   icon: 'pause',  text: 'Plan rejected — agent drafting a revision' },
  }[status];

  const alloc = [
    { name: 'Google Search', amount: 900, color: '#4B98A7' },
    { name: 'Founder Content', amount: 600, color: '#8DDCF0' },
    { name: 'LinkedIn Ads', amount: 500, color: '#A9C8F2' },
  ];

  const kpis = [
    { cls: 'kpi-teal',   icon: 'users',  label: 'Signups this cycle', value: 28,   delta: '+7 vs Cycle 3', up: true },
    { cls: 'kpi-blue',   icon: 'target', label: 'Blended CAC',        value: 71,   prefix: 'S$', delta: '41% under the S$120 target', up: true },
    { cls: 'kpi-navy',   icon: 'wallet', label: 'Spent so far',       value: 1467, prefix: 'S$', delta: '73% of budget · day 22 of 30' },
    { cls: 'kpi-orange', icon: 'clock',  label: 'Waiting on you',     value: pending ? 1 : 0,
      delta: pending ? 'Cycle 5 plan · S$2,000 proposed' : 'Nothing needs your decision', link: pending },
  ];

  const verdicts = [
    { channel: 'Google Search',   verdict: 'SCALE',             confidence: 87, observed: 45,  obsTone: 'teal',   target: 120, note: 'Beating target by 2.6× — scaling up next cycle' },
    { channel: 'Founder Content', verdict: 'HOLD',              confidence: 54, observed: 100, obsTone: 'teal',   target: 120, note: 'CAC halved since Cycle 1 — protected one more cycle' },
    { channel: 'LinkedIn Ads',    verdict: 'INSUFFICIENT DATA', confidence: 31, observed: 250, obsTone: 'orange', target: 120, note: 'Only 8 of 30 days observed — verdict pending' },
  ];

  return `
  <div class="content-wrap">
    <section class="hero" aria-labelledby="dashTitle">
      <div class="hero-top">
        <div>
          <div class="hero-eyebrow"><span class="dot"></span>Cycle 4 of 12 · Budget month 4</div>
          <h1 class="page-title hero-title" id="dashTitle">Dashboard</h1>
          <p class="hero-sub">Where the budget sits, what each channel earned, and what needs you next.</p>
        </div>
        <span class="hero-pill ${pill.cls}">${icon(pill.icon)}${pill.text}</span>
      </div>

      <div class="hero-body">
        <div class="hero-money">
          <div class="hero-money-label">Monthly budget under management</div>
          <div class="hero-money-value">
            <span class="cur">S$</span>${countUp(2000)}<span class="per">/ month</span>
          </div>
          <div class="hero-money-meta">
            <span>Allocated across <strong>3 channels</strong></span>
            <span class="sep"></span>
            <span><strong>100%</strong> deployed this cycle</span>
            <span class="sep"></span>
            <span>Cycle 5 proposal <strong>${pending ? 'awaiting approval' : status}</strong></span>
          </div>
        </div>

        <div class="hero-chart">
          <div class="hero-chart-head">
            <div>
              <div class="hero-chart-label">Blended CAC</div>
              <div class="hero-chart-value">${countUp(71, 'S$')}</div>
            </div>
            <span class="hero-chart-delta">${icon('trendDown')}61% since Cycle 1</span>
          </div>
          ${renderHeroChart()}
        </div>
      </div>
    </section>

    <div class="kpi-row">
      ${kpis.map((k, i) => `
        <div class="kpi ${k.cls}" style="--i:${i}">
          <div class="kpi-head">
            <div class="kpi-label">${k.label}</div>
            <div class="kpi-icon" aria-hidden="true">${icon(k.icon)}</div>
          </div>
          <div class="kpi-value">${countUp(k.value, k.prefix || '')}</div>
          <div class="kpi-delta ${k.up ? 'up' : ''}">${k.up ? icon('trendUp') : ''}${k.delta}</div>
          ${k.link ? `<button class="kpi-link" type="button" data-goto="approval">Review plan ${icon('arrowRight')}</button>` : ''}
        </div>`).join('')}
    </div>

    <section class="card cycle-card">
      <div class="cycle-head">
        <div class="cycle-title">Cycle 4 of 12</div>
        <div class="card-label">Current Status</div>
      </div>
      <div class="stepper" aria-label="Cycle progress">
        ${steps.map((s, i) => `
          ${i > 0 ? `<div class="step-connector ${s.cls === 'done' || s.cls === 'current' ? 'done' : ''}"></div>` : ''}
          <div class="step ${s.cls}" ${s.cls === 'current' ? 'aria-current="step"' : ''}>
            <div class="step-num">${s.cls === 'done' ? icon('check') : s.n}</div>
            <div class="step-name">${s.name}</div>
          </div>`).join('')}
      </div>
    </section>

    <div class="dash-grid">
      <section class="card">
        <div class="cycle-head alloc-head-row">
          <div class="card-label">Allocation — Cycle 4</div>
          <div class="alloc-deployed">${fmt(2000)} deployed</div>
        </div>
        <div class="alloc-bar" role="img" aria-label="Budget split: Google Search S$900, Founder Content S$600, LinkedIn Ads S$500">
          ${alloc.map((a, i) => `<span style="--i:${i};width:${(a.amount / 2000) * 100}%;background:${a.color}"></span>`).join('')}
        </div>
        ${alloc.map((a) => `
          <div class="legend-row">
            <div class="legend-left"><span class="legend-swatch" style="background:${a.color}"></span>${a.name}</div>
            <div class="legend-amount">${countUp(a.amount, 'S$')}</div>
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

      <section class="card verdict-card">
        <span class="orb orb-1" aria-hidden="true"></span>
        <span class="orb orb-2" aria-hidden="true"></span>
        <span class="orb orb-3" aria-hidden="true"></span>
        <div class="cycle-head verdict-head">
          <div class="card-label">Latest Verdicts — Cycle 4</div>
          <div class="verdict-meta">3 channels · day 22 of 30</div>
        </div>
        ${verdicts.map((v, i) => `
          <div class="verdict-tile" style="--i:${i}">
            <div class="verdict-tile-head">
              <div class="verdict-channel">${v.channel}</div>
              ${badge(v.verdict)}
            </div>
            <div class="verdict-stats">
              <div class="stat">
                <div class="stat-label">Confidence</div>
                <div class="stat-value">${countUp(v.confidence, '', '%')}</div>
              </div>
              <div class="stat">
                <div class="stat-label">Observed CAC</div>
                <div class="stat-value ${v.obsTone}">${countUp(v.observed, 'S$')}</div>
              </div>
              <div class="stat">
                <div class="stat-label">Target CAC</div>
                <div class="stat-value">${fmt(v.target)}</div>
              </div>
            </div>
            <div class="verdict-conf ${v.obsTone === 'orange' ? 'orange' : ''}" role="progressbar"
                 aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v.confidence}" aria-label="Confidence ${v.confidence}%">
              <span style="width:${v.confidence}%"></span>
            </div>
            <div class="verdict-note">${v.note}</div>
          </div>`).join('')}
      </section>
    </div>

    ${pending ? `
    <section class="approval-banner">
      <div class="banner-icon">${icon('clock')}</div>
      <div class="banner-body">
        <div class="banner-title">Plan for Cycle 5 is awaiting your approval</div>
        <div class="banner-sub">The agent has proposed a new allocation. Review before anything runs.</div>
      </div>
      <button class="btn btn-human" type="button" data-goto="approval">Review Plan ${icon('arrowRight')}</button>
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
          <button class="expand-toggle" type="button" data-expand="${row.channel}" aria-expanded="${expanded}">
            ${icon('chevronDown')} ${expanded ? 'Hide details' : 'Show details'}
          </button>
        </td>
        <td class="num">${fmt(current)}</td>
        <td>${spendCell}</td>
        <td class="cell-change"><span class="change-pill ${changeCls}">${changeText}</span></td>
        <td class="cell-reason">${row.reason}</td>
      </tr>
      ${detailRow}`;
  }).join('');

  const totalIndicator = state.editMode
    ? `<div class="alloc-total ${totalOk ? 'ok' : 'bad'}">
         Total: ${fmt(total)} ${totalOk ? '✓' : `— must equal ${fmt(BUDGET)}`}
       </div>`
    : '';

  // Plan-at-a-glance tiles and a current-vs-proposed allocation comparison
  const biggest = PLAN_ROWS
    .map((r) => ({ channel: r.channel, delta: (Number(state.spends[r.channel]) || 0) - CURRENT_SPEND[r.channel] }))
    .sort((a, b) => Math.abs(b.delta) - Math.abs(a.delta))[0];
  const scaling = PLAN_ROWS.filter((r) => (Number(state.spends[r.channel]) || 0) > CURRENT_SPEND[r.channel]).length;
  const planStrip = `
    <div class="kpi-strip plan-strip">
      <div class="kpi ${totalOk ? 'kpi-teal' : 'kpi-orange'}" style="--i:0">
        <div class="kpi-head"><div class="kpi-label">Proposed total</div><div class="kpi-icon" aria-hidden="true">${icon('wallet')}</div></div>
        <div class="kpi-value" data-plan-total>${countUp(total, 'S$')}</div>
        <div class="kpi-delta ${totalOk ? 'up' : ''}" data-plan-total-note>${totalOk ? icon('check') + 'Matches the ' + fmt(BUDGET) + ' budget' : 'Must equal ' + fmt(BUDGET)}</div>
      </div>
      <div class="kpi kpi-blue" style="--i:1">
        <div class="kpi-head"><div class="kpi-label">Biggest move</div><div class="kpi-icon" aria-hidden="true">${icon(biggest.delta >= 0 ? 'trendUp' : 'trendDown')}</div></div>
        <div class="kpi-value">${countUp(Math.abs(biggest.delta), biggest.delta >= 0 ? '+S$' : '−S$')}</div>
        <div class="kpi-delta">${biggest.channel}</div>
      </div>
      <div class="kpi kpi-navy" style="--i:2">
        <div class="kpi-head"><div class="kpi-label">Channels scaling</div><div class="kpi-icon" aria-hidden="true">${icon('rocket')}</div></div>
        <div class="kpi-value">${countUp(scaling)}<span class="kpi-of"> of ${PLAN_ROWS.length}</span></div>
        <div class="kpi-delta">${PLAN_ROWS.length - scaling} held or reduced</div>
      </div>
    </div>`;

  const allocColors = { 'Google Search': '#4B98A7', 'Founder Content': '#8DDCF0', 'LinkedIn Ads': '#A9C8F2' };
  const compareBar = (label, source, key) => `
    <div class="compare-row">
      <div class="compare-label">${label}</div>
      <div class="compare-bar" data-compare="${key}">
        ${PLAN_ROWS.map((r) => {
          const amt = Number(source[r.channel]) || 0;
          return `<span data-bar-channel="${r.channel}" style="width:${(amt / BUDGET) * 100}%;background:${allocColors[r.channel]}" title="${r.channel} · ${fmt(amt)}"></span>`;
        }).join('')}
      </div>
    </div>`;
  const compareBars = `
    <div class="compare-bars" role="img" aria-label="Current versus proposed allocation across channels">
      ${compareBar('Current', CURRENT_SPEND, 'current')}
      ${compareBar('Proposed', state.spends, 'proposed')}
      <div class="compare-legend">
        ${PLAN_ROWS.map((r) => `<span class="key"><span class="legend-swatch" style="background:${allocColors[r.channel]}"></span>${r.channel}</span>`).join('')}
      </div>
    </div>`;

  const planTab = `
    ${planStrip}
    <section class="card card-tinted">
      <div class="card-label">Strategy Summary</div>
      <p class="strategy-text">
        Google Search has delivered signups consistently below the S$120 CAC target and is the primary
        scaling opportunity for Cycle 5. Founder Content is showing gradual improvement and is protected
        for one more cycle. LinkedIn Ads has insufficient data and will be maintained at a reduced
        exploratory budget while the evaluation window completes.
      </p>
      <div class="alert alert-warning">
        ${icon('alert', 'alert-icon')}
        <div><strong>Major uncertainties:</strong> LinkedIn Ads has only 8 days
        of observation. The proposed CPC on Google Search assumes continued Quality Score above 7 — a drop
        could raise CAC materially.</div>
      </div>
    </section>

    <section class="card section-gap">
      <div class="alloc-head">
        <h2 class="card-title">Allocation changes</h2>
        ${totalIndicator}
      </div>
      ${state.validationError ? `<div class="alert alert-error" role="alert">${icon('alert', 'alert-icon')}<div>${state.validationError}</div></div>` : ''}
      ${compareBars}
      <div class="table-scroll">
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
      </div>
      ${state.editMode ? '<div class="table-footnote">Edits are re-checked against your budget rules before anything runs.</div>' : ''}
    </section>

    <div class="action-bar">
      <span class="action-note">Nothing runs until you approve. You can edit individual line items before approving.</span>
      <div class="action-buttons">
        <button class="btn btn-ghost" type="button" data-action="reject">Reject</button>
        ${state.editMode
          ? '<button class="btn btn-secondary" type="button" data-action="save-edits">Save edits</button>'
          : '<button class="btn btn-secondary" type="button" data-action="edit">Edit</button>'}
        <button class="btn btn-human" type="button" data-action="approve" ${state.editMode && !totalOk ? 'disabled' : ''}>Approve Cycle 5 ${icon('arrowRight')}</button>
      </div>
    </div>`;

  const draftTones = ['', 'blue', 'light'];
  const draftsTab = `
    <div class="drafts-banner">
      <span class="title-icon blue" aria-hidden="true">${icon('fileText')}</span>
      <div>These drafts belong to <strong>Cycle 5 plan (awaiting approval)</strong>. Nothing is published until the plan is approved.</div>
      <span class="drafts-count">${DRAFTS.length} drafts · Cycle 5</span>
    </div>
    ${DRAFTS.map((d, i) => {
      const id = d.channel.replace(/\s+/g, '-').toLowerCase();
      const spend = Number(state.spends[d.channel]) || 0;
      return `
      <section class="card card-accent section-gap draft-card">
        <div class="draft-head">
          <div class="card-title-row">
            <span class="title-icon num ${draftTones[i] || ''}" aria-hidden="true">${i + 1}</span>
            <h2 class="card-title">${d.channel}</h2>
          </div>
          <div class="draft-meta">
            <span class="draft-spend">${fmt(spend)} proposed</span>
            <span class="badge badge-awaiting">Draft</span>
          </div>
        </div>
        <div class="draft-field">
          <label class="field-label" for="hyp-${id}">Hypothesis</label>
          <textarea id="hyp-${id}">${d.hypothesis}</textarea>
        </div>
        <div class="draft-field">
          <label class="field-label" for="aud-${id}">Audience</label>
          <textarea id="aud-${id}">${d.audience}</textarea>
        </div>
        <div class="draft-field">
          <label class="field-label" for="angle-${id}">Message angle</label>
          <input type="text" id="angle-${id}" value="${esc(d.angle)}" data-angle-input="${id}" />
        </div>
        <div class="draft-preview" aria-live="polite">
          <span class="quote-mark" aria-hidden="true">“</span>
          <div>
            <div class="draft-preview-label">How it reads</div>
            <div class="draft-preview-text" data-angle-preview="${id}">${esc(d.angle)}</div>
          </div>
        </div>
      </section>`;
    }).join('')}
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
    <header class="approval-header page-head">
      ${pageEyebrow('Step 3 · Approve', 'orange')}
      <h1 class="page-title">Cycle 5 plan</h1>
      ${statusBadge}
      <p class="approval-meta">Proposed by the agent · Generated 09:07 today</p>
    </header>

    <div class="tabs" role="tablist">
      <button class="tab ${state.approvalTab === 'plan' ? 'active' : ''}" type="button" role="tab" aria-selected="${state.approvalTab === 'plan'}" data-tab="plan">Proposed Plan</button>
      <button class="tab ${state.approvalTab === 'drafts' ? 'active' : ''}" type="button" role="tab" aria-selected="${state.approvalTab === 'drafts'}" data-tab="drafts">Content Drafts</button>
    </div>

    ${state.approvalTab === 'plan' ? planTab : draftsTab}
  </div>`;
}

function renderChart() {
  // Values are direct-labelled once at the end of each line (never per point) so
  // labels can't pile up where the series converge; exact values live in hover tooltips.
  const W = 1080, H = 400;
  const padL = 80, padR = 236, padT = 28, padB = 52;
  const plotW = W - padL - padR, plotH = H - padT - padB;
  const maxY = 500;
  const cycles = ['Cycle 1', 'Cycle 2', 'Cycle 3', 'Cycle 4'];
  const inset = 36;
  const x = (i) => padL + inset + ((plotW - inset * 2) / (cycles.length - 1)) * i;
  const y = (v) => padT + plotH - (v / maxY) * plotH;
  const TARGET = 120;
  const lineEndX = W - padR + 12;

  const baseY = padT + plotH;

  const gridVals = [100, 200, 300, 400, 500];
  // Colours for grid, axis and labels come from CSS classes so the chart follows the theme
  const grid = gridVals.map((v) => `
    <line class="chart-grid" x1="${padL}" y1="${y(v)}" x2="${lineEndX}" y2="${y(v)}" stroke-width="1"/>
    <text class="chart-label" x="${padL - 12}" y="${y(v) + 4}" text-anchor="end" font-size="13">S$${v}</text>`).join('');
  // Faint vertical guides at each cycle
  const vGrid = cycles.map((_, i) => `<line class="chart-vgrid" x1="${x(i)}" y1="${padT}" x2="${x(i)}" y2="${baseY}" stroke-width="1" stroke-dasharray="3 5"/>`).join('');

  // One vertical gradient per series for the area fill under its line
  const defs = `<defs>${CHART_SERIES.map((s, si) => `
    <linearGradient id="area-${si}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${s.color}" stop-opacity="0.30"/>
      <stop offset="1" stop-color="${s.color}" stop-opacity="0.02"/>
    </linearGradient>`).join('')}</defs>`;

  const band = `<rect x="${padL}" y="${y(132)}" width="${lineEndX - padL}" height="${y(108) - y(132)}" fill="rgba(0,151,167,0.08)" rx="2"/>`;
  const targetLine = `<line x1="${padL}" y1="${y(TARGET)}" x2="${lineEndX}" y2="${y(TARGET)}" stroke="#0097A7" stroke-width="2" stroke-dasharray="7 6" stroke-linecap="round"/>`;

  // End-of-line labels (one per series) plus the target label, spread apart vertically
  const endLabels = CHART_SERIES.map((s) => {
    let last = -1;
    s.values.forEach((v, i) => { if (v != null) last = i; });
    return { y: y(s.values[last]), anchorY: y(s.values[last]), text: `${s.name} · S$${s.values[last]}`, color: s.color, weight: 600 };
  });
  endLabels.push({ y: y(TARGET), anchorY: y(TARGET), text: `S$${TARGET} target`, color: '#0097A7', weight: 500 });
  endLabels.sort((a, b) => a.y - b.y);
  const GAP = 22;
  for (let i = 1; i < endLabels.length; i++) {
    if (endLabels[i].y - endLabels[i - 1].y < GAP) endLabels[i].y = endLabels[i - 1].y + GAP;
  }
  // Keep the stack inside the plot: if it overflowed the bottom, shift everything up
  const overflow = endLabels[endLabels.length - 1].y - (padT + plotH - 4);
  if (overflow > 0) endLabels.forEach((l) => { l.y -= overflow; });

  const labelX = lineEndX + 14;
  const endLabelSvg = endLabels.map((l) => `
    <path d="M${lineEndX},${l.anchorY} L${labelX - 6},${l.y}" stroke="${l.color}" stroke-width="1" stroke-opacity="0.45" fill="none"/>
    <text x="${labelX}" y="${l.y + 4}" font-size="13" font-weight="${l.weight}" fill="${l.color}">${l.text}</text>`).join('');

  // Lines and area fills per series; dots are drawn afterwards so they always sit on top
  const series = CHART_SERIES.map((s, si) => {
    // A null value (no signups → CAC undefined) breaks the line and gets no dot
    const path = s.values.map((v, i) => {
      if (v == null) return '';
      const prevMissing = i === 0 || s.values[i - 1] == null;
      return `${prevMissing ? 'M' : 'L'}${x(i)},${y(v)}`;
    }).join(' ');

    // Area fill under each contiguous run of at least two points
    const runs = [];
    let run = [];
    s.values.forEach((v, i) => {
      if (v == null) { if (run.length) runs.push(run); run = []; } else run.push(i);
    });
    if (run.length) runs.push(run);
    const areas = runs.filter((r) => r.length > 1).map((r) => {
      const top = r.map((i, k) => `${k ? 'L' : 'M'}${x(i)},${y(s.values[i])}`).join(' ');
      return `<path class="chart-area" style="--s:${si}" d="${top} L${x(r[r.length - 1])},${baseY} L${x(r[0])},${baseY} Z" fill="url(#area-${si})"/>`;
    }).join('');

    return `${areas}<path class="chart-line" style="--s:${si}" pathLength="1" d="${path}" fill="none" stroke="${s.color}" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>`;
  }).join('');

  // One hover target per unique point. Series that share a point are merged into a single
  // dot (filled + ring) with a combined tooltip, so neither series becomes unreachable.
  const points = new Map();
  CHART_SERIES.forEach((s, si) => s.values.forEach((v, i) => {
    if (v == null) return;
    const key = `${i}:${v}`;
    if (!points.has(key)) points.set(key, { i, v, list: [] });
    points.get(key).list.push({ name: s.name, color: s.color, si });
  }));
  const dots = [...points.values()].map(({ i, v, list }) => {
    const [first, ...rest] = list;
    const marks = [
      `<circle class="chart-dot-mark chart-dot-fill" cx="${x(i)}" cy="${y(v)}" r="6.5" stroke="${first.color}" stroke-width="3"/>`,
      ...rest.map((s, k) => `<circle class="chart-dot-mark" cx="${x(i)}" cy="${y(v)}" r="${11 + k * 4}" fill="none" stroke="${s.color}" stroke-width="2.5"/>`),
    ].join('');
    const rows = list.map((s) => ({ name: s.name, color: s.color, value: v }));
    const label = `${cycles[i]}: ${list.map((s) => `${s.name} S$${v} per signup`).join('; ')}`;
    return `
      <g class="chart-dot" style="--i:${i};--s:${first.si}" tabindex="0" role="img"
         aria-label="${label}" data-tip-title="${cycles[i]}" data-tip-rows='${JSON.stringify(rows)}'>
        <circle cx="${x(i)}" cy="${y(v)}" r="${rest.length ? 17 : 14}" fill="transparent"/>
        ${marks}
      </g>`;
  }).join('');

  const xLabels = cycles.map((c, i) => {
    const hasData = CHART_SERIES.some((s) => s.values[i] != null);
    return `<text class="chart-xlabel ${hasData ? '' : 'dim'}" x="${x(i)}" y="${H - 18}" text-anchor="middle" font-size="14">${c}${hasData ? '' : ' · in progress'}</text>`;
  }).join('');

  return `
  <svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Cost per signup over time">
    ${defs}${grid}${vGrid}${band}
    <line class="chart-axis" x1="${padL}" y1="${baseY}" x2="${lineEndX}" y2="${baseY}" stroke-width="1"/>
    ${targetLine}${series}${endLabelSvg}${dots}${xLabels}
  </svg>
  <div class="chart-tooltip" id="chartTooltip" role="tooltip" hidden></div>`;
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
      <td>${r.complete ? `<span class="days-done num">${r.days.replace(' ✓', '')}${icon('check')}</span>` : `<span class="days-chip">${r.days}</span>`}</td>
      <td>${badge(r.verdict)}</td>
    </tr>`).join('');

  const historyRows = VERDICT_HISTORY.map((h) => `
    <tr>
      <td class="cell-channel">${h.channel}</td>
      ${h.cycles.map((v) => `<td>${badge(v)}</td>`).join('')}
    </tr>`).join('');

  return `
  <div class="content-wrap">
    <header class="page-head">
      ${pageEyebrow('Results · Cycles 1–4')}
      <h1 class="page-title">Analytics</h1>
      <p class="page-sub">Results, verdicts and cost per signup across every cycle so far.</p>
    </header>

    <div class="kpi-strip">
      ${[
        { cls: 'kpi-teal', icon: 'users',  label: 'Total signups',    value: 86, delta: '+28 this cycle', up: true },
        { cls: 'kpi-blue', icon: 'target', label: 'Best CAC to date', value: 45, prefix: 'S$', delta: 'Google Search · Cycle 4', up: true },
        { cls: 'kpi-navy', icon: 'check',  label: 'Cycles completed', value: 3,  delta: 'of 12 · Cycle 4 in progress' },
      ].map((k, i) => `
        <div class="kpi ${k.cls}" style="--i:${i}">
          <div class="kpi-head">
            <div class="kpi-label">${k.label}</div>
            <div class="kpi-icon" aria-hidden="true">${icon(k.icon)}</div>
          </div>
          <div class="kpi-value">${countUp(k.value, k.prefix || '')}</div>
          <div class="kpi-delta ${k.up ? 'up' : ''}">${k.up ? icon('trendUp') : ''}${k.delta}</div>
        </div>`).join('')}
    </div>

    <section class="card card-accent">
      <h2 class="card-title">Results by cycle</h2>
      <div class="table-scroll">
        <table class="table results-table">
          <thead>
            <tr>
              <th>Cycle</th><th>Channel</th><th>Spend</th><th>Signups</th><th>CAC</th>
              <th>CVR</th><th>CTR</th><th>Days</th><th>Verdict</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>

    <section class="card section-gap">
      <h2 class="card-title">Verdict history</h2>
      <div class="table-scroll">
        <table class="table verdict-grid-table">
          <thead>
            <tr><th>Channel</th><th>Cycle 1</th><th>Cycle 2</th><th>Cycle 3</th><th>Cycle 4</th></tr>
          </thead>
          <tbody>${historyRows}</tbody>
        </table>
      </div>
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
          ${[
            'Google Search branded terms convert 3× better than category terms for LedgerAI.',
            'Founder Content performs best when published Tuesday–Thursday mornings.',
            'LinkedIn Ads require ≥30 days to reach statistical significance at current budget.',
            'Signup-to-trial conversion drops when CAC exceeds S$120 — tighten audience segments.',
            'Re-targeting previous website visitors on Search cuts CAC by ~40%.',
          ].map((t) => `<li><span class="arrow">${icon('trendUp')}</span><span>${t}</span></li>`).join('')}
        </ul>
      </section>

      <div>
        <div class="info-panel">
          ${icon('info', 'info-icon')}
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
      chips: `<span class="node-chip">approval_gate</span><span class="gate-chip">${icon('pause')}Waiting for Founder Approval</span>`,
      summary: 'Plan submitted. Waiting for founder approval.',
      link: `<a href="#approval" class="tl-link">Go to approval screen ${icon('arrowRight')}</a>`,
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
    <header class="page-head">
      ${pageEyebrow('Live · Cycle 5 planning run', 'live')}
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
  const main = document.getElementById('main');
  main.innerHTML = VIEWS[state.view]();
  // Play the enter animation only when switching views, not on every state change
  if (render._lastView !== state.view) {
    const wrap = main.querySelector('.content-wrap');
    if (wrap) wrap.classList.add('is-entering');
    animateCounters(main);
  }
  render._lastView = state.view;
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
  // On narrow screens the expanded sidebar is an overlay — close it after picking a page
  if (narrowScreen.matches && !isNavCollapsed()) setNav(true, false);
}

// ---------- Collapsible sidebar ----------
const NAV_KEY = 'traction.navCollapsed';
const narrowScreen = window.matchMedia('(max-width: 900px)');

function isNavCollapsed() {
  return document.querySelector('.app').classList.contains('nav-collapsed');
}

function setNav(collapsed, persist = true) {
  document.querySelector('.app').classList.toggle('nav-collapsed', collapsed);
  const btn = document.querySelector('.sidebar-toggle');
  btn.setAttribute('aria-expanded', String(!collapsed));
  btn.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
  if (persist) {
    try { localStorage.setItem(NAV_KEY, collapsed ? '1' : '0'); } catch (_) { /* storage unavailable */ }
  }
}

function savedNavPref() {
  try { return localStorage.getItem(NAV_KEY) === '1'; } catch (_) { return false; }
}

function initNav() {
  // Hover labels for the collapsed rail come from the visible nav text
  document.querySelectorAll('.nav-item').forEach((el) => {
    el.dataset.label = el.querySelector('.nav-label').textContent.trim();
  });
  setNav(narrowScreen.matches ? true : savedNavPref(), false);
  narrowScreen.addEventListener('change', (e) => setNav(e.matches ? true : savedNavPref(), false));
  // Enable the width transition only after the initial state is applied
  requestAnimationFrame(() => document.querySelector('.app').classList.add('nav-ready'));
}

window.addEventListener('hashchange', () => navigate(location.hash.slice(1)));

// ---------- Event delegation ----------
document.addEventListener('click', (e) => {
  if (e.target.closest('.sidebar-toggle')) { setNav(!isNavCollapsed()); return; }
  if (e.target.closest('.theme-toggle')) {
    applyTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark', true, true);
    return;
  }
  if (e.target.closest('.nav-backdrop')) { setNav(true, false); return; }
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
  // Message-angle preview on the Content Drafts tab
  const angleInput = e.target.closest('[data-angle-input]');
  if (angleInput) {
    const preview = document.querySelector(`[data-angle-preview="${angleInput.dataset.angleInput}"]`);
    if (preview) preview.textContent = angleInput.value.trim() || 'Your message angle will appear here.';
    return;
  }

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
  const pill = row && row.querySelector('.change-pill');
  if (pill) {
    const current = CURRENT_SPEND[spendInput.dataset.spendInput];
    const proposed = Number(spendInput.value) || 0;
    pill.className = 'change-pill ' + (proposed >= current ? 'change-up' : 'change-down');
    pill.textContent = fmtDelta(proposed, current);
  }

  // Keep the proposed allocation bar and the total tile in step with the edits
  const scaleTo = Math.max(BUDGET, total);
  document.querySelectorAll('[data-compare="proposed"] [data-bar-channel]').forEach((seg) => {
    const amt = Number(state.spends[seg.dataset.barChannel]) || 0;
    seg.style.width = `${(amt / scaleTo) * 100}%`;
    seg.title = `${seg.dataset.barChannel} · ${fmt(amt)}`;
  });
  const totalTile = document.querySelector('[data-plan-total]');
  if (totalTile) {
    const ok = total === BUDGET;
    totalTile.textContent = fmt(total);
    const tile = totalTile.closest('.kpi');
    tile.classList.toggle('kpi-teal', ok);
    tile.classList.toggle('kpi-orange', !ok);
    const note = tile.querySelector('[data-plan-total-note]');
    note.className = 'kpi-delta ' + (ok ? 'up' : '');
    note.innerHTML = ok ? icon('check') + 'Matches the ' + fmt(BUDGET) + ' budget' : 'Must equal ' + fmt(BUDGET);
  }
});

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    toggleHelp(false);
    if (narrowScreen.matches && !isNavCollapsed()) setNav(true, false);
  }
});

// ---------- Chart tooltips ----------
function showChartTip(dot) {
  const tip = document.getElementById('chartTooltip');
  const wrap = dot.closest('.chart-wrap');
  if (!tip || !wrap) return;
  let rows = [];
  try { rows = JSON.parse(dot.dataset.tipRows || '[]'); } catch (_) { rows = []; }
  tip.innerHTML = `<div class="tip-title">${dot.dataset.tipTitle}</div>` + rows.map((r) => `
    <div class="tip-row"><span class="tip-swatch" style="background:${r.color}"></span><strong>${r.name}</strong><span>S$${r.value} per signup</span></div>`).join('');
  tip.hidden = false;
  const mark = dot.querySelector('.chart-dot-mark').getBoundingClientRect();
  const box = wrap.getBoundingClientRect();
  const left = mark.left - box.left + mark.width / 2 + wrap.scrollLeft;
  // The chart container clips overflow, so flip the bubble below points near the top
  const spaceAbove = mark.top - box.top;
  const below = spaceAbove < tip.offsetHeight + 16;
  tip.classList.toggle('below', below);
  tip.style.left = `${left}px`;
  tip.style.top = below ? `${mark.bottom - box.top + 12}px` : `${spaceAbove - 12}px`;
  // Keep the tooltip inside the chart horizontally
  const half = tip.offsetWidth / 2;
  const shift = Math.max(0, half - left) - Math.max(0, left + half - wrap.clientWidth);
  tip.style.transform = `translate(calc(-50% + ${shift}px), ${below ? '0' : '-100%'})`;
  tip.style.setProperty('--arrow-shift', `${-shift}px`);
}

function hideChartTip() {
  const tip = document.getElementById('chartTooltip');
  if (tip) tip.hidden = true;
}

document.addEventListener('mouseover', (e) => {
  const dot = e.target.closest('.chart-dot');
  if (dot) showChartTip(dot);
});
document.addEventListener('mouseout', (e) => {
  const dot = e.target.closest('.chart-dot');
  if (dot && !dot.contains(e.relatedTarget)) hideChartTip();
});
document.addEventListener('focusin', (e) => {
  const dot = e.target.closest('.chart-dot');
  if (dot) showChartTip(dot);
});
document.addEventListener('focusout', (e) => {
  if (e.target.closest('.chart-dot')) hideChartTip();
});

// ---------- Light / dark theme ----------
const THEME_KEY = 'traction.theme';
const darkScheme = window.matchMedia('(prefers-color-scheme: dark)');

function savedTheme() {
  try { return localStorage.getItem(THEME_KEY); } catch (_) { return null; }
}

function applyTheme(theme, persist = true, animate = false) {
  const root = document.documentElement;
  const dark = theme === 'dark';

  const commit = () => {
    root.dataset.theme = theme;
    const btn = document.querySelector('.theme-toggle');
    if (btn) {
      btn.setAttribute('aria-pressed', String(dark));
      btn.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
      btn.querySelector('.theme-label').textContent = dark ? 'Dark mode' : 'Light mode';
    }
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', dark ? '#0B121A' : '#1F2A38');
  };

  if (persist) {
    try { localStorage.setItem(THEME_KEY, theme); } catch (_) { /* storage unavailable */ }
  }

  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!animate || reduceMotion || root.dataset.theme === theme) { commit(); return; }

  // Preferred: let the browser crossfade a snapshot of the whole page (handles gradients too)
  if (typeof document.startViewTransition === 'function') {
    root.classList.add('theme-switching');
    const vt = document.startViewTransition(commit);
    // The browser skips the animation when the tab is hidden; the theme still applies.
    // Each promise rejects separately on a skipped transition, so silence all three.
    vt.ready.catch(() => {});
    vt.updateCallbackDone.catch(() => {});
    vt.finished.catch(() => {}).finally(() => root.classList.remove('theme-switching'));
    return;
  }

  // Fallback: briefly transition every colour property, then remove the hook
  root.classList.add('theme-transition');
  commit();
  clearTimeout(applyTheme._timer);
  applyTheme._timer = setTimeout(() => root.classList.remove('theme-transition'), 500);
}

function initTheme() {
  // The <head> script already set data-theme before first paint; this syncs the button
  applyTheme(document.documentElement.dataset.theme || (darkScheme.matches ? 'dark' : 'light'), false);
  // Follow the OS setting until the user picks one explicitly
  darkScheme.addEventListener('change', (e) => {
    if (!savedTheme()) applyTheme(e.matches ? 'dark' : 'light', false);
  });
}

// ---------- Boot ----------
initTheme();
initNav();
navigate(location.hash.slice(1) || 'brief');
