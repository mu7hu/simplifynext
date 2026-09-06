/* ============================================================
   The Next Dollar — "Augury" single-page app (vanilla JS)
   ============================================================ */

// ---------- App state ----------
const state = {
  view: 'brief',
  approvalTab: 'plan',       // 'plan' | 'drafts'
  editMode: false,
  expandedRows: {},          // channel -> bool
  spends: { 'Google Search': 1200, 'Founder Content': 500, 'LinkedIn Ads': 300 },
  validationError: null,
  planStatus: 'pending',     // mirrors approval_status: 'pending' | 'approved' | 'edited' | 'rejected'
  planFeedback: null,        // founder_feedback attached to a rejection (fed to the Strategist)
  liveCycle: null,            // response from the deployed /run-cycle endpoint
  cycleLoading: false,
  rejecting: false,          // reject feedback box open
  // FounderBrief.hard_exclusions: channel + reason. Only the five backend channels are valid.
  exclusions: [
    { channel: 'Meta Ads', reason: 'Low B2B intent for demo bookings; benchmark median CAC S$750.' },
  ],
  // FounderBrief.soft_preferences: channel + prior_belief_strength + founder_note (seeded LedgerAI brief)
  preferences: [
    { channel: 'Founder Content', strength: 0.8, note: 'I strongly believe founder-led content is strategically important for building trust in B2B finance.' },
  ],
};

const AUTH_TOKEN_KEY = 'augury.idToken';
const AUTH_REFRESH_KEY = 'augury.refreshToken';
let sessionIdToken = '';
let authMode = 'signin';
let pendingSignup = { username: '', password: '' };

function runtimeConfig() { return window.AUGURY_CONFIG || {}; }

function authToken() {
  if (sessionIdToken) return sessionIdToken;
  try { return localStorage.getItem(AUTH_TOKEN_KEY) || ''; } catch (_) { return ''; }
}

function saveAuth(result) {
  sessionIdToken = result.IdToken || '';
  try {
    localStorage.setItem(AUTH_TOKEN_KEY, result.IdToken || '');
    if (result.RefreshToken) localStorage.setItem(AUTH_REFRESH_KEY, result.RefreshToken);
  } catch (_) { /* storage unavailable */ }
}

function clearAuth() {
  sessionIdToken = '';
  try { localStorage.removeItem(AUTH_TOKEN_KEY); localStorage.removeItem(AUTH_REFRESH_KEY); } catch (_) { /* ignore */ }
}

function authErrorText(data) {
  const codes = {
    NotAuthorizedException: 'Incorrect username or password.',
    UserNotFoundException: 'Incorrect username or password.',
    PasswordResetRequiredException: 'This account needs a password reset in Cognito.',
    UserNotConfirmedException: 'This account has not been confirmed in Cognito.',
    InvalidPasswordException: 'Password must be at least 8 characters.',
    UsernameExistsException: 'An account with this email already exists. Sign in instead.',
    CodeMismatchException: 'That confirmation code is incorrect.',
    ExpiredCodeException: 'That confirmation code has expired. Create the account again.',
  };
  const code = data && data.__type && data.__type.split('#').pop();
  return codes[code] || data?.message || `Request failed${data?.__type ? ` (${code})` : ''}.`;
}

async function cognitoRequest(target, body) {
  const cfg = runtimeConfig();
  const res = await fetch(`https://cognito-idp.${cfg.cognitoRegion}.amazonaws.com/`, {
    method: 'POST',
    headers: { 'content-type': 'application/x-amz-json-1.1', 'x-amz-target': `AWSCognitoIdentityProviderService.${target}` },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(authErrorText(data));
  return data;
}

async function signIn(username, password) {
  const cfg = runtimeConfig();
  const data = await cognitoRequest('InitiateAuth', { AuthFlow: 'USER_PASSWORD_AUTH', ClientId: cfg.cognitoClientId, AuthParameters: { USERNAME: username, PASSWORD: password } });
  if (!data.AuthenticationResult) throw new Error('Sign-in did not return an authentication token.');
  saveAuth(data.AuthenticationResult);
  return data.AuthenticationResult;
}

async function signUp(username, password) {
  const cfg = runtimeConfig();
  return cognitoRequest('SignUp', { ClientId: cfg.cognitoClientId, Username: username, Password: password, UserAttributes: [{ Name: 'email', Value: username }] });
}

async function confirmSignUp(username, code) {
  const cfg = runtimeConfig();
  return cognitoRequest('ConfirmSignUp', { ClientId: cfg.cognitoClientId, Username: username, ConfirmationCode: code });
}

function setAuthMode(mode) {
  authMode = mode;
  const confirm = mode === 'confirm';
  const signup = mode === 'signup';
  document.getElementById('authTitle').textContent = confirm ? 'Confirm your email' : (signup ? 'Create your workspace account' : 'Sign in to your workspace');
  document.getElementById('authCopy').textContent = confirm ? 'Enter the code Cognito sent to your email address.' : (signup ? 'Create an account to access the planning and content workflow.' : 'Use your Cognito account to access the planning, approval and content-generation workflow.');
  document.getElementById('authCodeWrap').hidden = !confirm;
  document.getElementById('authPassword').hidden = confirm;
  document.querySelector('label[for="authPassword"]').hidden = confirm;
  document.getElementById('authUsername').readOnly = confirm;
  const submit = document.querySelector('.auth-submit');
  submit.textContent = confirm ? 'Confirm email' : (signup ? 'Create account' : 'Sign in');
  const sw = document.getElementById('authSwitch');
  sw.hidden = confirm;
  sw.innerHTML = signup ? 'Already have an account? <button type="button" data-auth-mode="signin">Sign in</button>' : 'New here? <button type="button" data-auth-mode="signup">Create an account</button>';
}

async function apiFetch(path, options = {}) {
  const cfg = runtimeConfig();
  const headers = new Headers(options.headers || {});
  headers.set('Authorization', `Bearer ${authToken()}`);
  if (options.body && !headers.has('content-type')) headers.set('content-type', 'application/json');
  const res = await fetch(`${cfg.apiBaseUrl}${path}`, { ...options, headers });
  if (res.status === 401) {
    clearAuth();
    showAuthGate('Your session expired. Please sign in again.');
  }
  return res;
}

function showAuthGate(message = '') {
  document.getElementById('appShell').hidden = true;
  document.getElementById('authGate').hidden = false;
  const error = document.getElementById('authError');
  error.textContent = message;
  error.hidden = !message;
}

function showApp() {
  document.getElementById('authGate').hidden = true;
  document.getElementById('appShell').hidden = false;
}

const BUDGET = 2000;
const CURRENT_SPEND = { 'Google Search': 900, 'Founder Content': 600, 'LinkedIn Ads': 500 };
// The Strategist's proposal as generated; edits are compared against this to detect an EDITED approval
const PROPOSED_SPEND = { 'Google Search': 1200, 'Founder Content': 500, 'LinkedIn Ads': 300 };

const PLAN_ROWS = [
  {
    channel: 'Google Search',
    experimentId: 'EXP-05-GOOG',
    exploration: false,
    evidence: 'Cycle 4 verdict SCALE at 87% confidence; three consecutive cycles under target in the ledger.',
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
    experimentId: 'EXP-05-FNDR',
    exploration: false,
    evidence: 'Cycle 4 verdict HOLD; CAC fell from S$200 to S$100 across four cycles. Founder prior (belief 0.8) noted.',
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
    experimentId: 'EXP-05-LNKD',
    exploration: true,
    evidence: 'Cycle 4 verdict INSUFFICIENT_DATA; benchmark prior median CAC S$580 with a 30-day minimum window.',
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

// `attr` = the measurement service's attribution_warning: audiences of Founder Content and
// LinkedIn Ads share ≥2 significant tokens (accountants, Singapore), so both are flagged.
// A zero-outcome cycle reports observed_cac = spend (backend semantics), marked `noOutcomes`.
const RESULTS = [
  { cycle: 'C1', channel: 'Google Search',   spend: 'S$900',   signups: '7',  cac: 'S$128', cacTone: 'bad',  cvr: '2.1%', ctr: '4.2%', days: '30d ✓', complete: true,  verdict: 'HOLD' },
  { cycle: 'C1', channel: 'Founder Content', spend: 'S$600',   signups: '3',  cac: 'S$200', cacTone: 'bad',  cvr: '1.1%', ctr: '3.8%', days: '30d ✓', complete: true,  verdict: 'HOLD', attr: 'LinkedIn Ads' },
  { cycle: 'C1', channel: 'LinkedIn Ads',    spend: 'S$500',   signups: '1',  cac: 'S$500', cacTone: 'bad',  cvr: '0.4%', ctr: '1.1%', days: '30d ✓', complete: true,  verdict: 'CUT', attr: 'Founder Content' },
  { cycle: 'C2', channel: 'Google Search',   spend: 'S$1,100', signups: '14', cac: 'S$78',  cacTone: 'good', cvr: '3.2%', ctr: '5.1%', days: '30d ✓', complete: true,  verdict: 'SCALE' },
  { cycle: 'C2', channel: 'Founder Content', spend: 'S$600',   signups: '5',  cac: 'S$120', cacTone: 'good', cvr: '1.8%', ctr: '4%',   days: '30d ✓', complete: true,  verdict: 'HOLD', attr: 'LinkedIn Ads' },
  { cycle: 'C2', channel: 'LinkedIn Ads',    spend: 'S$300',   signups: '0',  cac: 'S$300', cacTone: 'none', cvr: '0%',   ctr: '0.6%', days: '30d ✓', complete: true,  verdict: 'CUT', attr: 'Founder Content', noOutcomes: true },
  { cycle: 'C3', channel: 'Google Search',   spend: 'S$1,300', signups: '21', cac: 'S$61',  cacTone: 'good', cvr: '4%',   ctr: '5.8%', days: '30d ✓', complete: true,  verdict: 'SCALE' },
  { cycle: 'C3', channel: 'Founder Content', spend: 'S$500',   signups: '5',  cac: 'S$100', cacTone: 'good', cvr: '2%',   ctr: '3.5%', days: '30d ✓', complete: true,  verdict: 'HOLD', attr: 'LinkedIn Ads' },
  { cycle: 'C3', channel: 'LinkedIn Ads',    spend: 'S$200',   signups: '2',  cac: 'S$100', cacTone: 'good', cvr: '1%',   ctr: '1.8%', days: '30d ✓', complete: true,  verdict: 'HOLD', attr: 'Founder Content' },
  { cycle: 'C4', channel: 'Google Search',   spend: 'S$900',   signups: '20', cac: 'S$45',  cacTone: 'good', cvr: '4.5%', ctr: '6.1%', days: '22D / INCOMPLETE', complete: false, verdict: 'SCALE' },
  { cycle: 'C4', channel: 'Founder Content', spend: 'S$600',   signups: '6',  cac: 'S$100', cacTone: 'good', cvr: '2.1%', ctr: '3.9%', days: '22D / INCOMPLETE', complete: false, verdict: 'HOLD', attr: 'LinkedIn Ads' },
  { cycle: 'C4', channel: 'LinkedIn Ads',    spend: 'S$500',   signups: '2',  cac: 'S$250', cacTone: 'bad',  cvr: '0.8%', ctr: '1.4%', days: '8D / INCOMPLETE',  complete: false, verdict: 'INSUFFICIENT DATA', attr: 'Founder Content' },
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
  refresh: '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 16h5v5"/>',
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
    const delay = Math.min(idx * 45, 500);
    const start = performance.now() + delay;
    el.textContent = format(0);
    let done = false;
    const finish = () => { if (!done) { done = true; el.textContent = format(target); } };
    const tick = (now) => {
      if (done) return;
      const t = Math.min(1, Math.max(0, (now - start) / dur));
      const eased = 1 - Math.pow(1 - t, 4);
      el.textContent = format(target * eased);
      if (t < 1) requestAnimationFrame(tick); else finish();
    };
    requestAnimationFrame(tick);
    // requestAnimationFrame pauses in hidden tabs; make sure the final value always lands
    setTimeout(finish, dur + delay + 400);
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

// ---------- Plan validation (mirrors validate_plan_constraints in constraints/budget.py) ----------
const BUDGET_TOLERANCE = 0.05;   // validate_budget_sum tolerance
const MIN_CHANNEL_SPEND = 50;    // min_spend_per_active_channel
const MAX_CHANNEL_SHARE = 0.85;  // max_single_channel_share

const fmt2 = (n) => 'S$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function validatePlanEdits(spends = state.spends) {
  const errors = [];
  const amounts = PLAN_ROWS.map((row) => ({ channel: row.channel, amt: Number(spends[row.channel]) || 0 }));
  const total = amounts.reduce((a, b) => a + b.amt, 0);
  const excluded = new Set(state.exclusions.map((e) => e.channel));

  // 1. Negative check
  amounts.forEach(({ channel, amt }) => {
    if (amt < 0) errors.push(`Violation: Channel ${channel} has negative budget ${fmt2(amt)}`);
  });
  // 2. Budget sum check (within tolerance; micro-cents are rebalanced deterministically)
  const diff = Math.abs(total - BUDGET);
  if (diff > BUDGET_TOLERANCE) {
    errors.push(`Allocations sum to ${fmt2(total)}, which does not match total budget ${fmt2(BUDGET)} (diff: ${fmt2(diff)})`);
  }
  // 3. Hard exclusions
  amounts.forEach(({ channel, amt }) => {
    if (excluded.has(channel) && amt > 0) errors.push(`Violation: Channel ${channel} is hard-excluded but was allocated ${fmt2(amt)}`);
  });
  // 4. Risk / concentration
  amounts.forEach(({ channel, amt }) => {
    if (amt > 0 && amt < MIN_CHANNEL_SPEND) {
      errors.push(`Channel ${channel} allocated ${fmt2(amt)}, below minimum test floor ${fmt2(MIN_CHANNEL_SPEND)}`);
    }
    if (amt / BUDGET > MAX_CHANNEL_SHARE) {
      errors.push(`Channel ${channel} allocated ${((amt / BUDGET) * 100).toFixed(1)}%, exceeding max risk cap ${(MAX_CHANNEL_SHARE * 100).toFixed(1)}%`);
    }
  });
  return errors;
}

// True when the founder changed any line item from the Strategist's proposal (approval_status EDITED)
function planEdited() {
  return PLAN_ROWS.some((r) => (Number(state.spends[r.channel]) || 0) !== PROPOSED_SPEND[r.channel]);
}

const PLAN_STATUS_TEXT = {
  pending: 'awaiting approval',
  approved: 'approved',
  edited: 'approved with edits',
  rejected: 'rejected',
};

// ---------- Views ----------
function renderBrief() {
  // Channel pickers only offer the five channels the backend knows (schemas/experiment.py)
  const channelOptions = (used) => Object.values(CHANNEL_NAMES)
    .filter((n) => !used.includes(n))
    .map((n) => `<option value="${esc(n)}">${esc(n)}</option>`).join('');
  const usedEx = state.exclusions.map((e) => e.channel);
  const usedPref = state.preferences.map((p) => p.channel).concat(usedEx); // a preference on an excluded channel is dropped by intake

  const exclusionRows = state.exclusions.map((e) => `
    <div class="rule-row">
      <span class="chip chip-excluded">${icon('lock', 'chip-icon')} ${esc(e.channel)}</span>
      <span class="rule-note">${esc(e.reason)}</span>
      <button class="rule-x" type="button" data-remove-rule="excluded" data-name="${esc(e.channel)}" aria-label="Remove ${esc(e.channel)}">${icon('x')}</button>
    </div>`).join('');

  const preferenceRows = state.preferences.map((p) => `
    <div class="rule-row">
      <span class="chip chip-preferred">${icon('star', 'chip-icon')} ${esc(p.channel)}</span>
      <span class="strength-pill" title="prior_belief_strength">belief ${Number(p.strength).toFixed(1)}</span>
      <span class="rule-note">“${esc(p.note)}”</span>
      <button class="rule-x" type="button" data-remove-rule="preferred" data-name="${esc(p.channel)}" aria-label="Remove ${esc(p.channel)}">${icon('x')}</button>
    </div>`).join('');

  return `
  <div class="content-wrap">
    <header class="page-head">
      ${pageEyebrow('Step 1 · Brief')}
      <h1 class="page-title">Founder Brief</h1>
      <p class="page-sub">This brief guides every decision the agent makes. Update it anytime.</p>
    </header>

    <section class="card card-accent">
      ${cardTitle('Startup', 'fileText')}
      <div class="form-field">
        <div class="form-grid-2">
          <div>
            <label class="field-label" for="productName">Startup name</label>
            <input type="text" id="productName" value="LedgerAI" />
          </div>
          <div>
            <label class="field-label" for="stage">Stage</label>
            <select id="stage">
              <option value="PRE_SEED">Pre-seed</option>
              <option value="SEED" selected>Seed</option>
              <option value="SERIES_A">Series A</option>
            </select>
          </div>
        </div>
      </div>
      <div class="form-field">
        <label class="field-label" for="pitch">One-line pitch</label>
        <input type="text" id="pitch" value="LedgerAI automates bank reconciliation and month-end close for small businesses — cutting close time from 3 days to 3 hours." />
        <p class="field-hint">The Strategist writes each channel's audience and hypothesis from this pitch, the goal and the ledger.</p>
      </div>
    </section>

    <section class="card section-gap">
      ${cardTitle('Budget per cycle', 'wallet', 'navy')}
      <div class="budget-panel">
        <div class="budget-row">
          <span class="budget-currency">S$</span>
          <input type="number" id="budget" value="2000" />
          <span class="budget-hint">/ cycle. Every plan must sum to this total (±S$0.05) before it can be approved.</span>
        </div>
      </div>
    </section>

    <section class="card section-gap">
      ${cardTitle('Goal &amp; Target', 'target', 'blue')}
      <div class="form-field">
        <div class="form-grid-2">
          <div>
            <label class="field-label" for="outcome">Primary outcome</label>
            <select id="outcome">
              <option value="DEMO_BOOKINGS">Demo bookings</option>
              <option value="PAID_CONVERSIONS">Paid conversions</option>
              <option value="LEAD_SIGNUPS" selected>Lead signups</option>
              <option value="WAITLIST_SIGNUPS">Waitlist signups</option>
            </select>
          </div>
          <div>
            <label class="field-label" for="metricName">Metric name</label>
            <input type="text" id="metricName" value="Free trial signups" />
          </div>
        </div>
      </div>
      <div class="goal-grid form-field">
        <div>
          <label class="field-label" for="targetCac">Target cost per outcome</label>
          <div class="goal-cac">
            <span class="budget-currency">S$</span>
            <input type="number" id="targetCac" value="120" />
          </div>
        </div>
        <div>
          <label class="field-label" for="minVolume">Minimum outcomes per cycle</label>
          <div class="goal-cac">
            <input type="number" id="minVolume" value="5" min="1" />
          </div>
        </div>
      </div>
    </section>

    <section class="card section-gap">
      ${cardTitle('Hard Exclusions', 'lock', 'orange')}
      <p class="card-desc">Excluded channels receive S$0 in every plan. The deterministic validator rejects any plan that funds them.</p>
      <div class="rule-list">${exclusionRows || '<div class="rule-empty">No hard exclusions.</div>'}</div>
      <div class="rule-add-row">
        <select id="addExclusion" aria-label="Channel to exclude">
          <option value="">Choose a channel…</option>
          ${channelOptions(usedEx)}
        </select>
        <input type="text" id="addExclusionReason" placeholder="Reason (e.g. brand safety, past domain burn)" />
        <button class="btn btn-ghost btn-add" type="button" data-add-rule="excluded">${icon('plus')}Add</button>
      </div>
    </section>

    <section class="card section-gap">
      ${cardTitle('Soft Preferences', 'star', 'light')}
      <p class="card-desc">Treated as a prior in cycles 1–2. From cycle 3 the Strategist challenges it if the channel underperforms the benchmark or other channels.</p>
      <div class="rule-list">${preferenceRows || '<div class="rule-empty">No soft preferences.</div>'}</div>
      <div class="rule-add-row rule-add-row-3">
        <select id="addPreference" aria-label="Preferred channel">
          <option value="">Choose a channel…</option>
          ${channelOptions(usedPref)}
        </select>
        <select id="addPreferenceStrength" aria-label="Belief strength">
          ${[0.4, 0.6, 0.8, 1.0].map((s) => `<option value="${s}" ${s === 0.6 ? 'selected' : ''}>belief ${s.toFixed(1)}</option>`).join('')}
        </select>
        <input type="text" id="addPreferenceNote" placeholder="Why you believe in this channel" />
        <button class="btn btn-ghost btn-add" type="button" data-add-rule="preferred">${icon('plus')}Add</button>
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
    edited:   ['done', 'done', 'done', 'current', ''],
    rejected: ['done', 'current', '', '', ''],
  }[status];
  const steps = ['Brief', 'Plan', 'Approve', 'Launch & Measure', 'Reflect']
    .map((name, i) => ({ n: i + 1, name, cls: stepCls[i] }));

  const pill = {
    pending:  { cls: 'orange', icon: 'clock',  text: 'Step 3 · Approve — waiting on you' },
    approved: { cls: 'teal',   icon: 'rocket', text: 'Cycle 5 approved — launching channels' },
    edited:   { cls: 'teal',   icon: 'rocket', text: 'Cycle 5 approved with edits — launching channels' },
    rejected: { cls: 'grey',   icon: 'pause',  text: 'Plan rejected — Strategist replanning with your feedback' },
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

  // ExperimentVerdict fields: verdict, confidence, observed/target cost per outcome,
  // recommended_budget_direction and reasoning_summary
  const verdicts = [
    { channel: 'Google Search',   verdict: 'SCALE',             confidence: 87, observed: 45,  obsTone: 'teal',   target: 120, direction: 'INCREASE',
      reason: 'Observed CAC S$45 is 62% under the S$120 target on 20 outcomes, the third consecutive cycle under target.' },
    { channel: 'Founder Content', verdict: 'HOLD',              confidence: 54, observed: 100, obsTone: 'teal',   target: 120, direction: 'MAINTAIN',
      reason: 'CAC S$100 is under target but on only 6 outcomes; founder prior noted, keep budget flat and re-evaluate.' },
    { channel: 'LinkedIn Ads',    verdict: 'INSUFFICIENT DATA', confidence: 31, observed: 250, obsTone: 'orange', target: 120, direction: 'MAINTAIN',
      reason: '8 of 30 days observed with 2 outcomes. Window incomplete, so no cut is permitted; hold a minimum test budget.' },
  ];

  return `
  <div class="content-wrap">
    <section class="hero" aria-labelledby="dashTitle">
      <div class="hero-top">
        <div>
          <div class="hero-eyebrow"><span class="dot"></span>Cycle 4 of 12 · Day 22 of the evaluation window</div>
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
            <span>Cycle 5 proposal <strong>${PLAN_STATUS_TEXT[status]}</strong></span>
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
            <div class="verdict-note"><span class="direction-tag ${v.direction.toLowerCase()}" title="recommended_budget_direction">${v.direction}</span>${v.reason}</div>
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

// ============================================================
// Content Drafts — renders the Content Generator Agent's ContentPackage
// (src/traction/schemas/content.py). Read-only with respect to the plan:
// nothing here writes budgets, allocations, or graph state, and nothing publishes.
// ============================================================

// Mirrors _LIMITS in src/traction/agents/content.py (soft per-format character limits)
const CONTENT_LIMITS = {
  SEARCH_AD: { headline: 30, body: 90, secondary_headline: 30 },
  LINKEDIN_SPONSORED: { headline: 70, body: 700 },
  META_AD: { headline: 40, body: 300 },
  COLD_EMAIL: { headline: 60, body: 900 },
  FOUNDER_POST: { headline: 120, body: 1500 },
};

const FORMAT_LABELS = {
  SEARCH_AD: 'Search ad',
  LINKEDIN_SPONSORED: 'LinkedIn sponsored',
  META_AD: 'Meta ad',
  COLD_EMAIL: 'Cold email',
  FOUNDER_POST: 'Founder post',
};

// Channel enum (schemas/experiment.py) ↔ the display names used elsewhere in this UI
const CHANNEL_NAMES = {
  GOOGLE_SEARCH: 'Google Search',
  LINKEDIN: 'LinkedIn Ads',
  META: 'Meta Ads',
  COLD_EMAIL: 'Cold Email',
  FOUNDER_CONTENT: 'Founder Content',
};
const CHANNEL_ENUM = Object.fromEntries(Object.entries(CHANNEL_NAMES).map(([k, v]) => [v, k]));

const CONTENT_FIXTURE_URL = 'fixtures/content_package.fixture.json';
const PLAN_CYCLE_ID = 5;

// Content page state (kept out of the plan state on purpose)
state.content = {
  package: null,      // ContentPackage
  loading: false,     // full generate in flight
  busy: {},           // channel -> true while "Regenerate variants" is in flight
  error: null,        // { status, message } from the last failed call
  source: null,       // 'api' | 'fixture'
  selected: {},       // channel -> selected asset index
  planOpen: {},       // channel -> "From the plan" strip expanded
};

// Where content comes from: the Function URL when configured, otherwise the fixture (dev mode).
// ?content=fixture|empty|error forces a dev preview of each state.
function contentConfig() {
  const cfg = window.AUGURY_CONFIG || {};
  const url = cfg.contentFunctionUrl || '';
  const param = new URLSearchParams(location.search).get('content');
  const mode = param || (url ? 'api' : 'fixture');
  return { url, mode };
}

// Builds an ExperimentPlan payload (schemas/experiment.py) from the plan shown on the Proposed Plan tab
function buildExperimentPlan() {
  const total = proposedTotal();
  const allocations = PLAN_ROWS.map((row) => {
    const proposed = Number(state.spends[row.channel]) || 0;
    const channel = CHANNEL_ENUM[row.channel];
    return {
      channel,
      experiment_id: row.experimentId,
      current_budget: CURRENT_SPEND[row.channel],
      proposed_budget: proposed,
      proposed_share: total ? proposed / total : 0,
      hypothesis: row.detail.hypothesis,
      audience: row.detail.audience,
      message_angle: row.detail.angle.replace(/[“”]/g, ''),
      expected_outcome_range: null,
      confidence: 0.5,
      evaluation_window_days: 30,
      success_threshold: 120,
      reason: row.reason,
      evidence_used: row.evidence,
      is_exploration: row.exploration,
    };
  });
  // ExploreExploitPolicy: 15% exploration from cycle 5 onward (30% for cycles 3–4)
  return {
    cycle_id: PLAN_CYCLE_ID,
    total_budget: BUDGET,
    primary_goal: 'Free trial signups',
    allocations,
    exploration_budget_pct: 0.15,
    exploitation_budget_pct: 0.85,
    strategy_summary: 'Scale Google Search, hold Founder Content, keep LinkedIn Ads at an exploratory minimum while its window completes.',
    major_uncertainties: ['LinkedIn Ads has only 8 days of observation.', 'Google Search CPC assumes Quality Score stays above 7.'],
  };
}

// API client for the Content Generator Function URL:
// POST { cycle_id, plan, startup_profile?, founder_brief?, only_channels?, variants? } → ContentPackage
async function postContent(payload) {
  const { url, mode } = contentConfig();
  if (mode !== 'api') return fixtureContent(payload, mode);
  const res = await apiFetch(new URL(url).pathname, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch (_) {
    // Non-JSON body (gateway page, HTML error): keep a short plain-text excerpt only
    const plain = text.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
    data = { error: 'invalid_response', detail: `Endpoint returned a non-JSON body: ${plain.slice(0, 140)}${plain.length > 140 ? '…' : ''}` };
  }
  if (!res.ok) {
    const err = new Error(`Content endpoint returned ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

async function runLiveCycle() {
  if (state.cycleLoading) return;
  state.cycleLoading = true;
  render();
  try {
    const res = await apiFetch('/run-cycle', {
      method: 'POST',
      body: JSON.stringify({
        startup_id: 'ledger_ai',
        cycle_id: PLAN_CYCLE_ID,
        total_budget: BUDGET,
        auto_approve: true,
      }),
    });
    const text = await res.text();
    let data;
    try { data = JSON.parse(text); } catch (_) { data = { detail: text }; }
    if (!res.ok) {
      const err = new Error(`Cycle endpoint returned ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    state.liveCycle = data;
    state.planStatus = data.approval_status === 'approved' ? 'approved' : state.planStatus;
    showToast('Cycle approved and executed by the deployed workflow.');
  } catch (err) {
    showToast(`Cycle failed: ${describeContentError(err)}`);
  } finally {
    state.cycleLoading = false;
    render();
  }
}

// Dev-mode stand-in for the endpoint: serves the fixture, honouring only_channels
async function fixtureContent(payload, mode) {
  await new Promise((r) => setTimeout(r, 600));
  if (mode === 'error') {
    const err = new Error('Simulated failure');
    err.status = 500;
    err.data = { error: 'content_failure', detail: 'Simulated Bedrock failure (dev preview: ?content=error)' };
    throw err;
  }
  const res = await fetch(CONTENT_FIXTURE_URL, { cache: 'no-store' });
  if (!res.ok) {
    const err = new Error('Fixture not found');
    err.status = res.status;
    err.data = { error: 'fixture_missing', detail: `Could not load ${CONTENT_FIXTURE_URL}` };
    throw err;
  }
  const pkg = await res.json();
  // Like the real endpoint, only return channels that are in the plan. ?content=all keeps every
  // fixture channel so each format's layout can be checked.
  if (mode !== 'all') {
    const planChannels = PLAN_ROWS.map((r) => CHANNEL_ENUM[r.channel]);
    pkg.items = pkg.items.filter((it) => planChannels.includes(it.channel));
  }
  if (payload.only_channels) pkg.items = pkg.items.filter((it) => payload.only_channels.includes(it.channel));
  return pkg;
}

function describeContentError(err) {
  const data = err.data || {};
  const detail = data.detail;
  let text;
  if (Array.isArray(detail)) {
    // Pydantic validation report: [{ loc: [...], msg: ... }, ...]
    text = detail.slice(0, 3).map((d) => `${(d.loc || []).join('.')}: ${d.msg}`).join(' · ');
    if (detail.length > 3) text += ` · +${detail.length - 3} more`;
  } else if (detail) {
    text = String(detail);
  } else {
    text = err.message || 'Unknown error';
  }
  return data.error ? `${data.error} — ${text}` : text;
}

// Calls the content endpoint with the full plan, or with only_channels for a single channel.
// Never touches plan state. A failure keeps the previously loaded package on screen.
async function loadContent({ onlyChannels } = {}) {
  const c = state.content;
  const payload = { cycle_id: PLAN_CYCLE_ID, plan: buildExperimentPlan(), variants: 3 };
  if (onlyChannels) {
    payload.only_channels = onlyChannels;
    onlyChannels.forEach((ch) => { c.busy[ch] = true; });
  } else {
    c.loading = true;
  }
  c.error = null;
  render();
  try {
    const pkg = await postContent(payload);
    if (onlyChannels && c.package) {
      const fresh = new Map((pkg.items || []).map((it) => [it.channel, it]));
      c.package = { ...c.package, items: c.package.items.map((it) => fresh.get(it.channel) || it) };
      onlyChannels.forEach((ch) => { c.selected[ch] = 0; });
      showToast(`Regenerated variants for ${onlyChannels.map((ch) => CHANNEL_NAMES[ch] || ch).join(', ')}.`);
    } else {
      c.package = pkg;
      c.selected = {};
    }
    c.source = contentConfig().mode === 'api' ? 'api' : 'fixture';
  } catch (err) {
    c.error = { status: err.status || 0, message: describeContentError(err) };
  } finally {
    c.loading = false;
    (onlyChannels || []).forEach((ch) => { delete c.busy[ch]; });
    render();
  }
}

// First open of the Content Drafts tab: dev modes preload their preview state; API mode waits for "Generate"
function ensureContent() {
  const c = state.content;
  if (c.package || c.loading) return;
  const { mode } = contentConfig();
  if (mode === 'fixture') loadContent();
  else if (mode === 'empty' || mode === 'error') {
    c.package = { cycle_id: PLAN_CYCLE_ID, startup_name: '', items: [], summary: '', disclaimer: '' };
    if (mode === 'error') loadContent();
  }
}

// "headline 34/30" → { field, len, limit }
function parseWarnings(list) {
  const out = { headline: null, body: null, secondary: [], other: [] };
  (list || []).forEach((w) => {
    const m = /^(headline|body|secondary_headline)\s+(\d+)\/(\d+)$/.exec(String(w).trim());
    if (!m) { out.other.push(String(w)); return; }
    if (m[1] === 'secondary_headline') out.secondary.push({ text: w, len: Number(m[2]), used: false });
    else out[m[1]] = String(w);
  });
  return out;
}

function paragraphs(text) {
  return String(text || '').split(/\n{2,}/).map((p) => `<p>${esc(p).replace(/\n/g, '<br>')}</p>`).join('');
}

function renderAssetPreview(asset, format) {
  const limits = CONTENT_LIMITS[format] || {};
  const warns = parseWarnings(asset.length_warnings);
  const counts = asset.char_counts || {};
  const count = (field, value) => (counts[field] != null ? counts[field] : String(value || '').length);

  const counter = (n, limit) => (limit
    ? `<span class="field-counter ${n > limit ? 'over' : ''}" aria-label="${n} of ${limit} characters">${n}/${limit}</span>`
    : '');
  const field = (cls, inner, warnText) => `
    <div class="pv-field ${cls} ${warnText ? 'field-warn' : ''}">
      ${inner}
      ${warnText ? `<div class="warn-text">${icon('alert')}${esc(warnText)}</div>` : ''}
    </div>`;

  const headline = (cls, label) => field('pv-headline',
    `${label ? `<span class="pv-label">${label}</span>` : ''}<span class="${cls}">${esc(asset.headline)}</span>${counter(count('headline', asset.headline), limits.headline)}`,
    warns.headline);
  const body = (multi) => field('pv-body',
    multi
      ? `<div class="pv-body-text multi">${paragraphs(asset.body)}</div>${counter(count('body', asset.body), limits.body)}`
      : `<span class="pv-body-text">${esc(asset.body)}</span>${counter(count('body', asset.body), limits.body)}`,
    warns.body);
  const secondaries = () => (asset.secondary_headlines || []).map((s) => {
    const hit = warns.secondary.find((w) => !w.used && w.len === s.length);
    if (hit) hit.used = true;
    const warnText = hit ? hit.text : (limits.secondary_headline && s.length > limits.secondary_headline
      ? `secondary_headline ${s.length}/${limits.secondary_headline}` : null);
    return field('pv-secondary', `<span class="pv-search-title secondary">${esc(s)}</span>${counter(s.length, limits.secondary_headline)}`, warnText);
  }).join('');
  const hashtags = () => ((asset.hashtags || []).length
    ? `<div class="pv-hashtags">${asset.hashtags.map((h) => `<span class="hashtag">${esc(h.startsWith('#') ? h : '#' + h)}</span>`).join('')}</div>`
    : '');
  const cta = (style) => (asset.call_to_action
    ? `<div class="pv-cta pv-cta-${style}">${style === 'link' ? icon('arrowRight') : ''}${esc(asset.call_to_action)}</div>`
    : '');
  const other = () => (warns.other.length
    ? `<div class="warn-text pv-other-warn">${icon('alert')}${warns.other.map(esc).join(' · ')}</div>`
    : '');

  switch (format) {
    case 'SEARCH_AD':
      return `<div class="preview preview-search">
        <div class="pv-adlabel">Sponsored</div>
        ${headline('pv-search-title')}
        ${secondaries()}
        ${body(false)}
        ${cta('link')}
        ${other()}
      </div>`;
    case 'LINKEDIN_SPONSORED':
    case 'FOUNDER_POST':
      return `<div class="preview preview-post">
        ${headline('pv-post-title')}
        ${body(true)}
        ${hashtags()}
        ${cta('button')}
        ${other()}
      </div>`;
    case 'META_AD':
      return `<div class="preview preview-meta">
        ${headline('pv-post-title')}
        ${body(true)}
        ${cta('button')}
        ${other()}
      </div>`;
    case 'COLD_EMAIL':
      return `<div class="preview preview-email">
        ${headline('pv-subject', 'Subject:')}
        ${body(true)}
        ${cta('closing')}
        ${other()}
      </div>`;
    default:
      return `<div class="preview">
        ${headline('pv-post-title')}
        ${body(true)}
        ${hashtags()}
        ${cta('button')}
        ${other()}
      </div>`;
  }
}

function renderChannelCard(item, i) {
  const c = state.content;
  const name = CHANNEL_NAMES[item.channel] || item.channel;
  const spend = state.spends[name];
  const assets = item.assets || [];
  const sel = Math.min(c.selected[item.channel] || 0, Math.max(0, assets.length - 1));
  const asset = assets[sel];
  const busy = !!c.busy[item.channel];
  const tones = ['', 'blue', 'light', 'orange', 'navy'];

  return `
  <section class="card card-accent section-gap draft-card" data-channel-card="${item.channel}">
    <div class="draft-head">
      <div class="card-title-row">
        <span class="title-icon num ${tones[i % tones.length]}" aria-hidden="true">${i + 1}</span>
        <div>
          <h2 class="card-title">${esc(name)}</h2>
          <div class="draft-format">${esc(FORMAT_LABELS[item.format] || item.format)} · ${esc(item.experiment_id || '')}</div>
        </div>
      </div>
      <div class="draft-meta">
        ${spend != null
          ? `<span class="draft-spend">${fmt(Number(spend) || 0)} proposed</span>`
          : '<span class="draft-spend muted">Not in current plan</span>'}
        <span class="badge badge-awaiting">Draft</span>
      </div>
    </div>

    <details class="plan-strip" data-plan-strip="${item.channel}" ${c.planOpen[item.channel] ? 'open' : ''}>
      <summary>${icon('chevronDown')}From the plan<span class="plan-strip-note">Edit these in the plan, not here.</span></summary>
      <dl class="plan-strip-body">
        <dt>Hypothesis</dt><dd>${esc(item.hypothesis || '')}</dd>
        <dt>Audience</dt><dd>${esc(item.audience || '')}</dd>
        <dt>Message angle</dt><dd>${esc(item.message_angle || '')}</dd>
      </dl>
    </details>

    ${assets.length ? `
    <div class="variant-tabs" role="tablist" aria-label="Creative variants for ${esc(name)}">
      ${assets.map((a, k) => `
        <button class="variant-tab ${k === sel ? 'active' : ''}" type="button" role="tab" aria-selected="${k === sel}"
                data-variant="${item.channel}" data-index="${k}">
          ${esc(a.variant_label || String.fromCharCode(65 + k))}
          ${(a.length_warnings || []).length
            ? `<span class="variant-badge" title="${a.length_warnings.length} length warning${a.length_warnings.length > 1 ? 's' : ''}">${a.length_warnings.length}</span>`
            : ''}
        </button>`).join('')}
    </div>
    <div class="preview-wrap" role="tabpanel">${renderAssetPreview(asset, item.format)}</div>`
    : '<div class="pv-none">No variants returned for this channel.</div>'}

    <div class="draft-footer">
      <div class="draft-notes">
        ${item.targeting_notes ? `<div class="draft-note"><span class="draft-note-label">Targeting</span><span>${esc(item.targeting_notes)}</span></div>` : ''}
        ${item.compliance_notes ? `<div class="draft-note"><span class="draft-note-label">Before publishing</span><span>${esc(item.compliance_notes)}</span></div>` : ''}
      </div>
      <button class="btn btn-ghost btn-sm" type="button" data-regenerate="${item.channel}" ${busy || c.loading ? 'disabled' : ''}>
        ${busy ? '<span class="spin" aria-hidden="true"></span>Regenerating…' : icon('refresh') + 'Regenerate variants'}
      </button>
    </div>
  </section>`;
}

function renderDrafts() {
  const c = state.content;
  const pkg = c.package;
  const items = pkg ? (pkg.items || []) : [];
  const totalAssets = items.reduce((n, it) => n + (it.assets || []).length, 0);
  const statusText = PLAN_STATUS_TEXT[state.planStatus];
  const cycleId = pkg ? pkg.cycle_id : PLAN_CYCLE_ID;
  const { mode } = contentConfig();

  const banner = `
    <div class="drafts-banner">
      <span class="title-icon blue" aria-hidden="true">${icon('fileText')}</span>
      <div class="drafts-banner-text">
        <div>These drafts belong to <strong>Cycle ${cycleId} plan (${statusText})</strong>.</div>
        ${pkg && pkg.disclaimer ? `<div class="drafts-disclaimer">${esc(pkg.disclaimer)}</div>` : ''}
      </div>
      <span class="drafts-count">${items.length} channels · ${totalAssets} variants · Cycle ${cycleId}</span>
    </div>
    ${c.error ? `
    <div class="alert alert-error content-error" role="alert">
      ${icon('alert', 'alert-icon')}
      <div>
        <strong>Content endpoint error${c.error.status ? ` · ${c.error.status}` : ''}</strong>
        <div>${esc(c.error.message)}</div>
        ${items.length ? '<div class="content-error-note">Showing the last successfully generated package.</div>' : ''}
      </div>
    </div>` : ''}
    ${c.loading ? `<div class="content-loading"><span class="spin" aria-hidden="true"></span>Generating creative for ${PLAN_ROWS.length} channels…</div>` : ''}
    ${mode !== 'api' && pkg ? `
    <div class="content-devnote">${icon('info')}
      <span>Dev preview${c.source === 'fixture' ? ` from <code>${CONTENT_FIXTURE_URL}</code>` : ''}. Set <code>AUGURY_CONFIG.contentFunctionUrl</code> in index.html to call the Content Generator.</span>
    </div>` : ''}`;

  const summary = pkg && pkg.summary
    ? `<div class="content-summary"><div class="card-label">Creative direction</div><p>${esc(pkg.summary)}</p></div>`
    : '';

  if (!items.length) {
    return `${banner}${summary}
    <section class="card content-empty">
      <div class="content-empty-icon" aria-hidden="true">${icon('fileText')}</div>
      <h2 class="card-title">No creative generated for this cycle yet</h2>
      <p>Generate draft variants for every channel in the Cycle ${PLAN_CYCLE_ID} plan. This only reads the plan; it never changes budgets or allocations.</p>
      <button class="btn btn-primary" type="button" data-action="content-generate" ${c.loading ? 'disabled' : ''}>
        ${c.loading ? '<span class="spin" aria-hidden="true"></span>Generating…' : icon('rocket') + 'Generate'}
      </button>
    </section>`;
  }

  return `${banner}${summary}${items.map(renderChannelCard).join('')}`;
}

// Re-render a single channel card in place (variant switch) without scrolling the page
function rerenderChannelCard(channel) {
  const c = state.content;
  const items = c.package ? c.package.items : [];
  const i = items.findIndex((it) => it.channel === channel);
  const el = document.querySelector(`[data-channel-card="${channel}"]`);
  if (i < 0 || !el) { render(); return; }
  el.outerHTML = renderChannelCard(items[i], i);
}

function renderApproval() {
  const total = proposedTotal();
  const editErrors = validatePlanEdits();
  const sumOk = Math.abs(total - BUDGET) <= BUDGET_TOLERANCE;
  const totalOk = editErrors.length === 0;

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
      ? `<tr class="row-expanded"><td colspan="7">
           <dl class="expand-detail">
             <dt>Experiment</dt><dd><code class="mono">${row.experimentId}</code> · ${row.exploration ? 'Exploration' : 'Exploitation'}</dd>
             <dt>Hypothesis</dt><dd>${row.detail.hypothesis}</dd>
             <dt>Audience</dt><dd>${row.detail.audience}</dd>
             <dt>Message angle</dt><dd>${row.detail.angle}</dd>
             <dt>Success threshold</dt><dd>${row.detail.threshold}</dd>
             <dt>Evaluation window</dt><dd>${row.detail.window}</dd>
             <dt>Evidence used</dt><dd>${row.evidence}</dd>
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
        <td class="num" data-share-cell="${row.channel}">${((proposed / BUDGET) * 100).toFixed(1)}%</td>
        <td><span class="type-tag ${row.exploration ? 'explore' : 'exploit'}">${row.exploration ? 'Explore' : 'Exploit'}</span></td>
        <td class="cell-reason">${row.reason}</td>
      </tr>
      ${detailRow}`;
  }).join('');

  const totalIndicator = state.editMode
    ? `<div class="alloc-total ${totalOk ? 'ok' : 'bad'}">
         Total: ${fmt(total)} ${totalOk ? '✓' : (sumOk ? `— ${editErrors.length} rule${editErrors.length > 1 ? 's' : ''} failing` : `— must equal ${fmt(BUDGET)} (±S$0.05)`)}
       </div>`
    : '';

  // Rejection: feedback is required because the Strategist replans from it (founder_feedback)
  const rejectBox = state.rejecting ? `
    <section class="card section-gap reject-box">
      <h2 class="card-title">Reject this plan</h2>
      <p class="card-desc">Tell the Strategist what to change. Your note is passed back as founder feedback and the plan is regenerated.</p>
      <textarea id="rejectFeedback" placeholder="e.g. Keep LinkedIn Ads at S$500 until its 30-day window completes."></textarea>
      <div class="reject-actions">
        <button class="btn btn-ghost" type="button" data-action="reject-cancel">Cancel</button>
        <button class="btn btn-human" type="button" data-action="reject-confirm">Send rejection ${icon('arrowRight')}</button>
      </div>
    </section>` : '';

  const feedbackNote = state.planStatus === 'rejected' && state.planFeedback
    ? `<div class="feedback-note">${icon('info')}<span><strong>Founder feedback sent to the Strategist:</strong> ${esc(state.planFeedback)}</span></div>`
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
        <div class="kpi-delta ${totalOk ? 'up' : ''}" data-plan-total-note>${totalOk ? icon('check') + 'Matches the ' + fmt(BUDGET) + ' budget' : (sumOk ? 'Fails a floor or cap rule' : 'Must equal ' + fmt(BUDGET) + ' (±S$0.05)')}</div>
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
      <div class="policy-line">
        <span class="type-tag exploit">Exploit 85%</span>
        <span class="type-tag explore">Explore 15%</span>
        <span>Policy target for cycle 5 onward (30% applied in cycles 3–4). LinkedIn Ads is the exploration slot at S$300.</span>
      </div>
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
              <th>Share</th>
              <th>Type</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>${planRows}</tbody>
        </table>
      </div>
      ${state.editMode ? `
      <div class="table-footnote">
        Saved edits are revalidated deterministically: total within S$0.05 of ${fmt(BUDGET)} · at least ${fmt(MIN_CHANNEL_SPEND)} on any active channel ·
        no channel above ${MAX_CHANNEL_SHARE * 100}% · excluded channels at S$0. A failing edit rejects the plan and the Strategist replans.
      </div>` : ''}
    </section>

    ${rejectBox}

    <div class="action-bar">
      <span class="action-note">Nothing runs until you approve. You can edit individual line items before approving.</span>
      <div class="action-buttons">
        <button class="btn btn-ghost" type="button" data-action="reject" ${state.rejecting ? 'disabled' : ''}>Reject</button>
        ${state.editMode
          ? '<button class="btn btn-secondary" type="button" data-action="save-edits">Save edits</button>'
          : '<button class="btn btn-secondary" type="button" data-action="edit">Edit</button>'}
        <button class="btn btn-human" type="button" data-action="approve" ${(state.editMode && !totalOk) || state.rejecting || state.cycleLoading ? 'disabled' : ''}>
          ${state.cycleLoading ? '<span class="spin" aria-hidden="true"></span>Running Cycle 5…' : `${planEdited() ? 'Approve edited plan' : 'Approve Cycle 5'} ${icon('arrowRight')}`}
        </button>
      </div>
    </div>`;

  const draftsTab = renderDrafts();

  const statusBadge = {
    pending: '<span class="badge badge-awaiting">Awaiting Your Approval</span>',
    approved: '<span class="badge badge-approved">Approved</span>',
    edited: '<span class="badge badge-approved">Edited &amp; approved</span>',
    rejected: '<span class="badge badge-rejected">Rejected</span>',
  }[state.planStatus];

  return `
  <div class="content-wrap">
    <header class="approval-header page-head">
      ${pageEyebrow('Step 3 · Approve', 'orange')}
      <h1 class="page-title">Cycle 5 plan</h1>
      ${statusBadge}
      <p class="approval-meta">Proposed by the Strategist · passed deterministic validation · Generated 09:07 today</p>
      ${feedbackNote}
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
      <td class="cell-channel">${r.channel}${r.attr
        ? `<span class="attr-flag" tabindex="0" role="img" aria-label="Attribution warning" title="Audience overlaps with ${r.attr} this cycle; observed CAC for ${r.channel} may be distorted by multi-touch attribution.">${icon('info')}</span>`
        : ''}</td>
      <td class="num">${r.spend}</td>
      <td class="num">${r.signups}</td>
      <td class="num ${r.cacTone === 'good' ? 'cac-good' : r.cacTone === 'bad' ? 'cac-bad' : ''}">${r.cac}${r.noOutcomes ? '<span class="cac-note">no outcomes yet</span>' : ''}</td>
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
          <span><strong>Attribution warnings.</strong> When two channels target overlapping audiences in the same cycle, the measurement service flags both (${icon('info', 'inline-icon')} in the table) and their CAC should be read as noisy. Founder Content and LinkedIn Ads overlap on Singapore accountants.</span>
        </div>

        <section class="card digest-card">
          <h2 class="digest-title">Augury Weekly Portfolio Digest — Cycle 4</h2>
          <p class="digest-tldr"><strong>TL;DR:</strong> Cycle 4: spent S$2,000 for 28 free trial signups — blended CAC S$71 (target S$120).</p>
          <div class="digest-flags"><span class="badge badge-scale">Scaling: Google Search</span></div>

          <div class="digest-section">
            <div class="card-label">Executive summary</div>
            <p>Google Search is the engine at S$45 CAC, 2.6× better than target, and earns its third SCALE. Founder Content halved its CAC since Cycle 1 but volume is thin. LinkedIn Ads is eight days into a 30-day window and cannot be judged yet.</p>
            <p><strong>Primary bottleneck:</strong> LinkedIn Ads volume — 2 outcomes in 8 days.</p>
          </div>

          <div class="digest-section">
            <div class="card-label">Verdicts &amp; why</div>
            ${[
              { ch: 'Google Search', v: 'SCALE', conf: 87, why: 'Observed CAC S$45 is 62% under target on 20 outcomes.', learning: 'Branded terms convert 3× better than category terms for LedgerAI.' },
              { ch: 'Founder Content', v: 'HOLD', conf: 54, why: 'CAC S$100 is under target on only 6 outcomes; founder prior noted.', learning: 'Posts published Tuesday–Thursday mornings outperform.' },
              { ch: 'LinkedIn Ads', v: 'INSUFFICIENT DATA', conf: 31, why: '8 of 30 days observed with 2 outcomes; window incomplete, no cut permitted.', learning: 'LinkedIn needs the full 30-day window at this budget.' },
            ].map((d) => `
              <div class="digest-verdict">
                <div class="digest-verdict-head"><strong>${d.ch}</strong> ${badge(d.v)} <span class="digest-conf">${d.conf}% confidence</span></div>
                <div>${d.why}</div>
                <div class="digest-learning">Learning: ${d.learning}</div>
              </div>`).join('')}
          </div>

          <div class="digest-section">
            <div class="card-label">Proposed movement for the next cycle</div>
            <table class="digest-table">
              <thead><tr><th>Channel</th><th>Current share</th><th>Analyst suggests</th></tr></thead>
              <tbody>
                <tr><td>Google Search</td><td>45%</td><td><span class="direction-tag increase">INCREASE</span>increase budget</td></tr>
                <tr><td>Founder Content</td><td>30%</td><td><span class="direction-tag maintain">MAINTAIN</span>keep budget flat</td></tr>
                <tr><td>LinkedIn Ads</td><td>25%</td><td><span class="direction-tag maintain">MAINTAIN</span>keep budget flat</td></tr>
              </tbody>
            </table>
            <p class="digest-meta">Recommended explore ratio next cycle: 15%.</p>
            <blockquote class="digest-disclaimer">These are the Analyst's recommendations for the next planning cycle. Actual budgets are computed by the deterministic budget engine and only take effect after you approve them at the human gate.</blockquote>
          </div>

          <div class="digest-section">
            <div class="card-label">Learnings to carry forward</div>
            <ol class="digest-list">
              <li>Google Search branded terms convert 3× better than category terms for LedgerAI.</li>
              <li>Founder Content performs best when published Tuesday–Thursday mornings.</li>
              <li>LinkedIn Ads require the full 30-day window to reach significance at current budget.</li>
            </ol>
          </div>
        </section>
      </div>
    </div>
  </div>`;
}

function renderActivity() {
  // Node names and messages follow graph/nodes.py: load_context → strategist → validate_plan
  // (→ strategist_repair → validate_plan on failure, max 2 retries) → approval_gate.
  const entries = [
    {
      time: '09:02', dot: '', cardCls: '',
      chips: '<span class="node-chip">load_context</span>',
      summary: 'Context loaded for LedgerAI. Prior cycles in ledger: 3. Loaded 4 recent learnings and Cycle 4 verdicts.',
    },
    {
      time: '09:02', dot: 'teal', cardCls: 'tl-active',
      chips: '<span class="node-chip">strategist</span>',
      summary: 'Planning Cycle 5 from the founder brief, benchmark priors, ledger history and Cycle 4 verdicts (3 channels).',
    },
    {
      time: '09:04', dot: '', cardCls: '',
      chips: '<span class="node-chip">strategist</span>',
      summary: 'Strategist formulated plan with 3 allocations.',
    },
    {
      time: '09:05', dot: 'orange', cardCls: '',
      chips: '<span class="node-chip">validate_plan</span><span class="repair-chip">Failed</span>',
      summary: 'Allocations sum to S$2,050.00, which does not match total budget S$2,000.00 (diff: S$50.00).',
    },
    {
      time: '09:05', dot: '', cardCls: '',
      chips: '<span class="node-chip">strategist_repair</span><span class="repair-chip">retry 1/2</span>',
      summary: 'Attempted repair on plan (retry 1/2). Allocations rescaled to the founder budget and micro-cents rebalanced.',
    },
    {
      time: '09:06', dot: 'teal', cardCls: '',
      chips: '<span class="node-chip">validate_plan</span><span class="pass-chip">Passed</span>',
      summary: 'Budget sum, hard exclusions, S$50 floor and 85% cap all passed. Total proposed: S$2,000.00.',
    },
    {
      time: '09:07', dot: 'orange', cardCls: 'tl-gate',
      chips: `<span class="node-chip">approval_gate</span><span class="gate-chip">${icon('pause')}Waiting for Founder Approval</span>`,
      summary: 'Plan submitted. Nothing executes until the founder approves, edits or rejects.',
      link: `<a href="#approval" class="tl-link">Go to approval screen ${icon('arrowRight')}</a>`,
    },
  ];

  // Excerpt of the Strategist's planning context (the prompt it reasons over)
  const reasoning = [
    '# Planning Context for Cycle 5',
    'Total Available Budget: S$2,000.00',
    'Primary Goal: Free trial signups (Target CAC: S$120.00)',
    'Recommended Policy: 85% Exploit / 15% Explore',
    '',
    '## Latest Analyst Verdicts:',
    '- GOOGLE_SEARCH: `SCALE` (CAC: S$45.00, conf 0.87)',
    '- FOUNDER_CONTENT: `HOLD` (CAC: S$100.00, conf 0.54)',
    '- LINKEDIN: `INSUFFICIENT_DATA` (8/30 days)',
    '',
    '## Soft Founder Preferences (Priors):',
    '- FOUNDER_CONTENT: belief strength 0.8',
    '',
    'Proposing: GS +S$300, FC −S$100, LI −S$200…',
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
  // Fail-safe: browsers pause CSS animations in hidden or throttled tabs, which can leave
  // entrance animations stranded (faded content, undrawn chart lines, invisible tiles).
  // After they should all have finished, force their end states (see .settled in styles.css).
  main.classList.remove('settled');
  clearTimeout(render._settleTimer);
  render._settleTimer = setTimeout(() => main.classList.add('settled'), 2600);
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
const NAV_KEY = 'augury.navCollapsed';
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
  const authModeButton = e.target.closest('[data-auth-mode]');
  if (authModeButton) {
    setAuthMode(authModeButton.dataset.authMode);
    document.getElementById('authError').hidden = true;
    return;
  }
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
  if (tab) {
    state.approvalTab = tab.dataset.tab;
    if (state.approvalTab === 'drafts') ensureContent();
    render();
    return;
  }

  // Content Drafts: variant tabs and the two read-only generate actions
  const variant = e.target.closest('[data-variant]');
  if (variant) {
    state.content.selected[variant.dataset.variant] = Number(variant.dataset.index) || 0;
    rerenderChannelCard(variant.dataset.variant);
    return;
  }
  const regen = e.target.closest('[data-regenerate]');
  if (regen) { if (!regen.disabled) loadContent({ onlyChannels: [regen.dataset.regenerate] }); return; }
  if (e.target.closest('[data-action="content-generate"]')) { loadContent(); return; }

  const expand = e.target.closest('[data-expand]');
  if (expand) {
    const ch = expand.dataset.expand;
    state.expandedRows[ch] = !state.expandedRows[ch];
    render();
    return;
  }

  const removeRule = e.target.closest('[data-remove-rule]');
  if (removeRule) {
    const key = removeRule.dataset.removeRule === 'excluded' ? 'exclusions' : 'preferences';
    state[key] = state[key].filter((r) => r.channel !== removeRule.dataset.name);
    render();
    return;
  }

  const addRule = e.target.closest('[data-add-rule]');
  if (addRule) {
    if (addRule.dataset.addRule === 'excluded') {
      const channel = document.getElementById('addExclusion').value;
      if (!channel) { showToast('Choose one of the five channels to exclude.'); return; }
      const reason = document.getElementById('addExclusionReason').value.trim() || 'Founder hard exclusion';
      state.exclusions.push({ channel, reason });
      // Intake drops a soft preference on an excluded channel
      state.preferences = state.preferences.filter((p) => p.channel !== channel);
    } else {
      const channel = document.getElementById('addPreference').value;
      if (!channel) { showToast('Choose a channel to prefer.'); return; }
      const strength = Number(document.getElementById('addPreferenceStrength').value) || 0.6;
      const note = document.getElementById('addPreferenceNote').value.trim() || 'Founder soft preference';
      state.preferences.push({ channel, strength, note });
    }
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
      const errors = validatePlanEdits();
      if (errors.length) {
        // node_approval_gate: an EDIT that fails deterministic validation becomes a rejection with feedback
        state.validationError = 'Edited allocation failed deterministic validation: ' + errors.join('; ');
        state.planFeedback = state.validationError;
        state.planStatus = 'rejected';
        state.editMode = false;
        showToast('Edits failed validation. The plan is rejected and the Strategist will replan.');
      } else {
        state.editMode = false;
        state.validationError = null;
        showToast('Edits saved and revalidated against the budget rules.');
      }
      render();
      break;
    }
    case 'reject':
      state.rejecting = true;
      state.editMode = false;
      render();
      // render() resets the scroll position; bring the feedback box into view and focus it.
      // Done synchronously (layout is ready) rather than on an animation frame, which
      // hidden or throttled tabs may never deliver.
      {
        const box = document.querySelector('.reject-box');
        const field = document.getElementById('rejectFeedback');
        if (box) box.scrollIntoView({ behavior: document.hidden ? 'auto' : 'smooth', block: 'center' });
        if (field) field.focus({ preventScroll: true });
      }
      break;
    case 'reject-cancel':
      state.rejecting = false;
      render();
      break;
    case 'reject-confirm': {
      const box = document.getElementById('rejectFeedback');
      const feedback = box ? box.value.trim() : '';
      if (!feedback) { showToast('Add a note for the Strategist before rejecting.'); if (box) box.focus(); return; }
      state.planFeedback = feedback;
      state.planStatus = 'rejected';
      state.rejecting = false;
      showToast('Plan rejected. The Strategist will replan using your feedback.');
      render();
      break;
    }
    case 'approve':
      if (action.disabled) return;
      state.planStatus = planEdited() ? 'edited' : 'approved';
      state.editMode = false;
      render();
      runLiveCycle();
      break;
    case 'signout':
      clearAuth();
      showAuthGate('You have been signed out.');
      break;
  }
});

// Remember whether each "From the plan" strip is open across re-renders (toggle doesn't bubble)
document.addEventListener('toggle', (e) => {
  const strip = e.target.closest && e.target.closest('[data-plan-strip]');
  if (strip) state.content.planOpen[strip.dataset.planStrip] = strip.open;
}, true);

// Live-update proposed spend totals while editing
document.addEventListener('input', (e) => {
  const spendInput = e.target.closest('[data-spend-input]');
  if (!spendInput) return;
  state.spends[spendInput.dataset.spendInput] = Number(spendInput.value) || 0;

  // Update the total indicator + change cells in place (avoid full re-render to keep focus)
  const total = proposedTotal();
  const errors = validatePlanEdits();
  const sumOk = Math.abs(total - BUDGET) <= BUDGET_TOLERANCE;
  const indicator = document.querySelector('.alloc-total');
  if (indicator) {
    indicator.className = 'alloc-total ' + (errors.length ? 'bad' : 'ok');
    indicator.textContent = errors.length
      ? `Total: ${fmt(total)} — ${sumOk ? `${errors.length} rule${errors.length > 1 ? 's' : ''} failing` : `must equal ${fmt(BUDGET)} (±S$0.05)`}`
      : `Total: ${fmt(total)} ✓`;
  }
  const approveBtn = document.querySelector('[data-action="approve"]');
  if (approveBtn) {
    approveBtn.disabled = errors.length > 0;
    approveBtn.innerHTML = `${planEdited() ? 'Approve edited plan' : 'Approve Cycle 5'} ${icon('arrowRight')}`;
  }
  document.querySelectorAll('[data-share-cell]').forEach((cell) => {
    const amt = Number(state.spends[cell.dataset.shareCell]) || 0;
    cell.textContent = `${((amt / BUDGET) * 100).toFixed(1)}%`;
  });

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
    const ok = errors.length === 0;
    totalTile.textContent = fmt(total);
    const tile = totalTile.closest('.kpi');
    tile.classList.toggle('kpi-teal', ok);
    tile.classList.toggle('kpi-orange', !ok);
    const note = tile.querySelector('[data-plan-total-note]');
    note.className = 'kpi-delta ' + (ok ? 'up' : '');
    note.innerHTML = ok
      ? icon('check') + 'Matches the ' + fmt(BUDGET) + ' budget'
      : (sumOk ? 'Fails a floor or cap rule' : 'Must equal ' + fmt(BUDGET) + ' (±S$0.05)');
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
const THEME_KEY = 'augury.theme';
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
async function boot() {
  initTheme();
  setAuthMode('signin');
  const form = document.getElementById('authForm');
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const button = form.querySelector('button');
    const error = document.getElementById('authError');
    button.disabled = true;
    button.textContent = 'Signing in…';
    error.hidden = true;
    try {
      const username = form.username.value.trim().toLowerCase();
      if (authMode === 'confirm') {
        await confirmSignUp(pendingSignup.username, form.code.value.trim());
        await signIn(pendingSignup.username, pendingSignup.password);
        pendingSignup = { username: '', password: '' };
        form.reset();
        showApp();
        initNav();
        navigate(location.hash.slice(1) || 'brief');
      } else if (authMode === 'signup') {
        pendingSignup = { username, password: form.password.value };
        await signUp(username, form.password.value);
        form.code.value = '';
        setAuthMode('confirm');
        document.getElementById('authUsername').value = username;
        document.getElementById('authUsername').readOnly = true;
        error.textContent = 'Account created. Check your email for the confirmation code.';
        error.hidden = false;
      } else {
        await signIn(username, form.password.value);
        form.reset();
        showApp();
        initNav();
        if (new URLSearchParams(location.search).has('content')) {
          state.approvalTab = 'drafts';
          ensureContent();
          navigate('approval');
        } else navigate(location.hash.slice(1) || 'brief');
      }
    } catch (err) {
      error.textContent = err.message;
      error.hidden = false;
    } finally {
      button.disabled = false;
      button.textContent = authMode === 'confirm' ? 'Confirm email' : (authMode === 'signup' ? 'Create account' : 'Sign in');
    }
  });
  if (authToken()) {
    showApp();
    initNav();
    if (new URLSearchParams(location.search).has('content')) {
      state.approvalTab = 'drafts';
      ensureContent();
      navigate('approval');
    } else navigate(location.hash.slice(1) || 'brief');
  } else showAuthGate();
}
boot();
