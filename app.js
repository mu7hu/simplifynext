/* Augury: all business data is loaded from the authenticated workspace API. */
'use strict';
const cfg = window.AUGURY_CONFIG;
const TOKEN = 'augury.idToken', REFRESH = 'augury.refreshToken';
const state = { workspace: null, run: null, view: location.hash.slice(1) || 'brief', approvalTab: 'plan', busy: false, error: '', timer: null, authMode: 'signin' };
const channels = ['GOOGLE_SEARCH', 'LINKEDIN', 'META', 'COLD_EMAIL', 'FOUNDER_CONTENT'];
const labels = { GOOGLE_SEARCH: 'Google Search', LINKEDIN: 'LinkedIn', META: 'Meta', COLD_EMAIL: 'Cold Email', FOUNDER_CONTENT: 'Founder Content' };
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const money = (v) => v == null ? '—' : new Intl.NumberFormat('en-SG', { style:'currency', currency:'SGD' }).format(Number(v));
const when = (v) => v ? new Date(v.endsWith('Z') || /[+-]\d\d:\d\d$/.test(v) ? v : v + 'Z').toLocaleString() : '—';
const pretty = (s) => String(s || '').replaceAll('_',' ').toLowerCase();
const active = (r) => r && ['QUEUED','RUNNING','WAITING_APPROVAL'].includes(r.status);
const button = (action, text, disabled = false) => `<button type="button" class="btn btn-primary" data-action="${action}" ${disabled ? 'disabled' : ''}>${text}</button>`;
const ICONS = { check:'<path d="m5 12 4 4L19 6"/>', trendUp:'<path d="m3 17 6-6 4 4 8-9"/>', trendDown:'<path d="m3 7 6 6 4-4 8 9"/>', wallet:'<path d="M4 7h16v12H4z"/><path d="M4 7V5h14"/><circle cx="16" cy="13" r="1"/>', users:'<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 2-5 6-5s6 2 6 5"/><path d="M16 11c3 0 5 2 5 5"/>', target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/>', clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>' };
function icon(name, cls='') { return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name] || ''}</svg>`; }
function countUp(value, prefix='', suffix='') { return `<span class="count" data-count="${Number(value)||0}" data-prefix="${esc(prefix)}" data-suffix="${esc(suffix)}">${esc(prefix)}${Number(value||0).toLocaleString('en-SG')}${esc(suffix)}</span>`; }
function verdictBadge(v) { const value=String(v||'PENDING').replaceAll('_',' '); return `<span class="badge badge-${value.toLowerCase().replaceAll(' ','-')}">${esc(value)}</span>`; }
function toast(text) { $('toast').textContent = text; $('toast').classList.add('show'); setTimeout(() => $('toast').classList.remove('show'), 4500); }
function owner() { try { return JSON.parse(atob(localStorage.getItem(TOKEN).split('.')[1].replaceAll('-','+').replaceAll('_','/'))).sub; } catch { return ''; } }
function selectionKey() { return 'augury.selectedRun.' + owner(); }
function authGate(message = '') { clearTimeout(state.timer); $('appShell').hidden = true; $('authGate').hidden = false; $('authError').textContent = message; $('authError').hidden = !message; }
async function cognito(target, body) {
  const res = await fetch(`https://cognito-idp.${cfg.cognitoRegion}.amazonaws.com/`, { method:'POST', headers:{'content-type':'application/x-amz-json-1.1','x-amz-target':'AWSCognitoIdentityProviderService.' + target}, body:JSON.stringify(body) });
  const data = await res.json(); if (!res.ok) throw new Error(data.message || data.__type || 'Authentication failed'); return data;
}
function saveTokens(result) { localStorage.setItem(TOKEN, result.IdToken); if (result.RefreshToken) localStorage.setItem(REFRESH,result.RefreshToken); }
let refreshing;
async function refreshAuth() {
  if (!refreshing) refreshing = cognito('InitiateAuth',{AuthFlow:'REFRESH_TOKEN_AUTH',ClientId:cfg.cognitoClientId,AuthParameters:{REFRESH_TOKEN:localStorage.getItem(REFRESH) || ''}}).then(d => saveTokens(d.AuthenticationResult)).finally(() => { refreshing = null; });
  return refreshing;
}
async function api(path, method = 'GET', body, retry = true) {
  const res = await fetch(cfg.apiBaseUrl + path, {method, cache:'no-store', headers:{Authorization:'Bearer ' + localStorage.getItem(TOKEN),'content-type':'application/json'}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  if (res.status === 401 && retry) {
    try { await refreshAuth(); } catch { authGate('Session expired. Please sign in again.'); throw new Error('Session expired'); }
    return api(path,method,body,false);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) { if (res.status === 401) authGate('Please sign in again.'); throw new Error(data.error || data.message || `Request failed (${res.status})`); }
  return data;
}
function setMode(mode) {
  state.authMode = mode;
  const confirm = mode === 'confirm', signup = mode === 'signup';
  $('authTitle').textContent = confirm ? 'Confirm your email' : signup ? 'Create your account' : 'Sign in to your workspace';
  $('authCopy').textContent = confirm ? 'Enter the code sent to your email.' : 'Your saved briefs, plans and agent activity will be available after sign-in.';
  $('authPassword').hidden = confirm; $('authPassword').required = !confirm;
  document.querySelector('label[for="authPassword"]').hidden = confirm;
  $('authCodeWrap').hidden = !confirm; $('authCode').required = confirm;
  document.querySelector('.auth-submit').textContent = confirm ? 'Confirm email' : signup ? 'Create account' : 'Sign in';
  $('authSwitch').innerHTML = confirm ? '<button type="button" data-auth="resend">Resend code</button> · <button type="button" data-auth="signin">Back to sign in</button>' : `<button type="button" data-auth="${signup ? 'signin' : 'signup'}">${signup ? 'Already registered? Sign in' : 'Create an account'}</button> · <button type="button" data-auth="confirm">Confirm an existing account</button>`;
  $('authError').hidden = true;
}
$('authForm').addEventListener('submit', async e => {
  e.preventDefault(); const submit = document.querySelector('.auth-submit'); submit.disabled = true;
  const username = $('authUsername').value.trim(), password = $('authPassword').value;
  try {
    if (state.authMode === 'signup') {
      const data = await cognito('SignUp',{ClientId:cfg.cognitoClientId,Username:username,Password:password,UserAttributes:[{Name:'email',Value:username}]});
      setMode(data.UserConfirmed ? 'signin' : 'confirm'); toast(data.UserConfirmed ? 'Account created. Sign in.' : 'Check your email for the confirmation code.');
    } else if (state.authMode === 'confirm') {
      await cognito('ConfirmSignUp',{ClientId:cfg.cognitoClientId,Username:username,ConfirmationCode:$('authCode').value.trim()}); setMode('signin'); toast('Email confirmed. You can sign in.');
    } else {
      const data = await cognito('InitiateAuth',{ClientId:cfg.cognitoClientId,AuthFlow:'USER_PASSWORD_AUTH',AuthParameters:{USERNAME:username,PASSWORD:password}});
      if (!data.AuthenticationResult) throw new Error('Account requires an additional sign-in challenge: ' + data.ChallengeName);
      saveTokens(data.AuthenticationResult); $('authPassword').value = ''; await loadWorkspace();
    }
  } catch (err) { $('authError').textContent = err.message; $('authError').hidden = false; }
  finally { submit.disabled = false; }
});
async function loadWorkspace() {
  $('authGate').hidden = true; $('appShell').hidden = false;
  if (!state.workspace) $('main').innerHTML = '<div class="content-wrap"><p role="status">Loading your saved workspace…</p></div>';
  try {
    state.workspace = await api('/workspace'); state.error = '';
    // The workspace endpoint intentionally returns lightweight run rows. Load the
    // persisted run details as well so dashboard history and charts reflect every
    // completed cycle in this account, not just the selected one.
    const details = await Promise.all(state.workspace.runs.map(r => api('/runs/' + encodeURIComponent(r.run_id)).catch(() => r)));
    state.workspace.runs = details;
    const selected = localStorage.getItem(selectionKey());
    state.run = state.workspace.runs.find(r => r.run_id === selected) || state.workspace.runs[0] || null;
    render(); schedule();
  } catch (err) { state.error = err.message; render(); }
}
function schedule() {
  clearTimeout(state.timer);
  if (state.workspace?.runs.some(active)) state.timer = setTimeout(poll, 2000);
}
async function poll() {
  try {
    const running = state.workspace.runs.filter(active);
    let changed = Boolean(state.error);
    for (const old of running) {
      const fresh = await api('/runs/' + encodeURIComponent(old.run_id));
      changed = changed || old.updated_at !== fresh.updated_at || old.status !== fresh.status;
      state.workspace.runs = state.workspace.runs.map(r => r.run_id === fresh.run_id ? fresh : r);
      if (state.run?.run_id === fresh.run_id) state.run = fresh;
    }
    state.error = '';
    // Updating run telemetry must never erase an in-progress founder brief or rejection note.
    if (changed && state.view !== 'brief' && !state.busy && !document.querySelector('#revisionForm:focus-within')) render();
    else sidebar();
    schedule();
  } catch (err) {
    state.error = 'Updates interrupted: ' + err.message;
    const banner = $('syncError'); if (banner) { banner.textContent = state.error; banner.hidden = false; }
    if (!$('appShell').hidden) state.timer = setTimeout(poll,5000);
  }
}
function sidebar() {
  const w = state.workspace, run = state.run;
  document.querySelector('.brand-sub').textContent = w?.brief?.startup_name || 'Your workspace';
  const awaiting = w?.runs.filter(r => r.status === 'WAITING_APPROVAL').length || 0;
  $('navBadge').textContent = awaiting; $('navBadge').hidden = !awaiting; $('navBadge').setAttribute('aria-label',`${awaiting} plans awaiting approval`);
  document.querySelector('.footer-loop-val').textContent = run ? String(run.cycle_id) : '—';
  document.querySelector('.footer-progress').hidden = true;
  document.querySelector('.footer-cycle').textContent = run ? pretty(run.status) : 'No cycles yet';
  document.querySelectorAll('[data-view]').forEach(a => { a.classList.toggle('active',a.dataset.view === state.view); a.setAttribute('aria-current',a.dataset.view === state.view ? 'page' : 'false'); });
}
function header(title, copy) {
  return `<header class="page-head"><div class="card-label">${esc(state.workspace?.brief?.startup_name || 'Your workspace')}</div><h1 class="page-title">${esc(title)}</h1><p>${esc(copy)}</p></header>`;
}
function runPicker() {
  const runs = state.workspace?.runs || [];
  return runs.length ? `<div class="workspace-toolbar"><label for="runPicker">Cycle history</label><select id="runPicker">${runs.map(r => `<option value="${esc(r.run_id)}" ${state.run?.run_id === r.run_id ? 'selected' : ''}>Cycle ${r.cycle_id} · ${esc(pretty(r.status))} · ${esc(when(r.created_at))}</option>`).join('')}</select></div>` : '';
}
function statusCard() {
  const r = state.run; if (!r) return '<section class="card"><h2>No cycles yet</h2><p>Save your founder brief and start your first planning cycle.</p><a href="#brief">Open Founder Brief</a></section>';
  return `<section class="card live-status" aria-live="polite"><div><span class="badge">Cycle ${r.cycle_id} · ${esc(pretty(r.status))}</span><p>${r.current_node ? esc(pretty(r.current_node)) + ' is working…' : r.status === 'WAITING_APPROVAL' ? 'Review the generated plan and content before approving.' : r.status === 'COMPLETE' ? 'Results and learnings are saved.' : 'Latest saved workflow state'}</p></div><div><span>${r.events.length} events</span><small>Updated ${esc(when(r.updated_at))}</small></div>${r.error ? `<p class="workspace-error" role="alert">${esc(r.error)}</p>` : ''}</section>`;
}
function field(name, label, value, type='text', extra='') { return `<label class="workspace-field">${label}<input name="${name}" type="${type}" value="${esc(value)}" required spellcheck="false" ${extra}></label>`; }
function select(name,label,values,value) { return `<label class="workspace-field">${label}<select name="${name}">${values.map(v => `<option value="${v}" ${v===value?'selected':''}>${esc(pretty(v))}</option>`).join('')}</select></label>`; }
function renderBrief() {
  const b = state.workspace.brief || {}, p = state.workspace.profile || {}, g = b.primary_goal || {};
  return `<div class="content-wrap"><header class="page-head"><div class="page-eyebrow"><span class="dot"></span>Step 1 · Brief</div><h1 class="page-title">Founder Brief</h1><p class="page-sub">This brief guides every decision the agents make. Update it before starting a new cycle.</p></header><form id="briefForm" class="workspace-form"><section class="card card-accent"><div class="card-title-row"><span class="title-icon">${icon('users')}</span><h2 class="card-title">Startup</h2></div><div class="workspace-grid">
    ${field('startup_name','Company name',b.startup_name || '')}
    ${select('stage','Stage',['PRE_SEED','SEED','SERIES_A'],p.stage)}
    ${select('sector','Sector',['B2B_SAAS','B2C_SUBSCRIPTION','MARKETPLACE','DEVTOOLS'],p.sector)}
    ${field('target_acv','Annual customer value (S$)',p.target_acv || '', 'number','min="0.01" step="0.01"')}
    ${field('sales_cycle_days','Typical sales cycle (days)',p.sales_cycle_days || '', 'number','min="1" step="1"')}
    ${field('total_budget','Budget per simulation cycle (S$)',b.total_budget || '', 'number','min="100" step="0.01"')}
    ${select('goal_type','Outcome type',['DEMO_BOOKINGS','PAID_CONVERSIONS','LEAD_SIGNUPS','WAITLIST_SIGNUPS'],g.goal_type)}
    ${field('metric_name','Outcome name',g.metric_name || '')}
    ${field('target_cac','Target cost per outcome (S$)',g.target_cac || '', 'number','min="0.01" step="0.01"')}
    ${field('minimum_acceptable_volume','Minimum outcomes per cycle',g.minimum_acceptable_volume || '', 'number','min="1" step="1"')}
    </div><label class="workspace-field">Product, target audience and value proposition<textarea name="one_line_pitch" required spellcheck="false" rows="4">${esc(b.one_line_pitch || '')}</textarea></label></section><section class="card section-gap"><div class="card-title-row"><span class="title-icon navy">${icon('wallet')}</span><h2 class="card-title">Budget and goal</h2></div><p class="card-desc">Every proposed plan must respect this budget and target before it reaches the human approval gate.</p><div class="budget-panel"><strong>${money(b.total_budget || 0)}</strong><span>available per simulation cycle</span></div></section><section class="card section-gap"><div class="card-title-row"><span class="title-icon orange">${icon('target')}</span><h2 class="card-title">Channel boundaries and preferences</h2></div><p class="card-desc">Exclusions are hard rules. Preferences are beliefs the Strategist tests against evidence.</p><div class="brief-channel-grid">
    ${channels.map(ch => { const ex = (b.hard_exclusions || []).find(e=>e.channel===ch), pref = (b.soft_preferences || []).find(e=>e.channel===ch); return `<fieldset class="channel-input"><legend>${labels[ch]}</legend><label><input type="checkbox" name="exclude_${ch}" ${ex?'checked':''}> Exclude this channel</label><label class="workspace-field">Exclusion reason<input name="reason_${ch}" value="${esc(ex?.reason || '')}" spellcheck="false"></label><label class="workspace-field">Founder preference<input name="note_${ch}" value="${esc(pref?.founder_note || '')}" spellcheck="false" placeholder="Optional"></label><label class="workspace-field">Belief strength (0–1)<input type="number" name="strength_${ch}" min="0" max="1" step="0.1" value="${pref?.prior_belief_strength ?? 0.5}"></label></fieldset>`; }).join('')}</div><p class="workspace-notice">Agents use ${esc(state.workspace.model_mode)}. Campaign outcomes are generated by the market simulator; no ads are published or charged.</p></section><div id="briefMessage" role="status"></div><div class="brief-actions workspace-actions"><button class="btn btn-primary" type="submit" ${state.busy?'disabled':''}>Save founder brief</button>${button('start','Save and start planning',state.busy || state.workspace.runs.some(active))}</div></form></div>`;
}
function readBrief() {
  const f = $('briefForm'); if (!f.reportValidity()) throw new Error('Complete the required founder brief fields.');
  const d = new FormData(f), n = k => Number(d.get(k)), s = k => String(d.get(k) || '').trim();
  const brief = {startup_name:s('startup_name'),stage:s('stage'),one_line_pitch:s('one_line_pitch'),total_budget:n('total_budget'),primary_goal:{goal_type:s('goal_type'),target_cac:n('target_cac'),minimum_acceptable_volume:n('minimum_acceptable_volume'),metric_name:s('metric_name')},initial_allocations:{},hard_exclusions:[],soft_preferences:[]};
  for (const ch of channels) {
    if (d.has('exclude_'+ch)) { if (!s('reason_'+ch)) throw new Error('Add an exclusion reason for '+labels[ch]); brief.hard_exclusions.push({channel:ch,reason:s('reason_'+ch),is_permanent:true}); }
    if (s('note_'+ch)) brief.soft_preferences.push({channel:ch,prior_belief_strength:n('strength_'+ch),founder_note:s('note_'+ch)});
  }
  if (brief.hard_exclusions.length > 3) throw new Error('Keep at least two channels available to satisfy the concentration limit.');
  return {brief,profile:{stage:s('stage'),sector:s('sector'),target_acv:n('target_acv'),sales_cycle_days:n('sales_cycle_days')}};
}
async function saveBrief(payload) {
  const data = await api('/briefs/current','PUT',payload); state.workspace.brief=data.brief; state.workspace.profile=data.profile;
  if ($('briefMessage')) $('briefMessage').textContent = 'Saved to your workspace at ' + new Date().toLocaleTimeString(); sidebar();
}
function planCard() {
  const p = state.run?.result?.plan; if (!p) return '<section class="card"><p>No generated plan is available yet. Agent Activity shows current progress.</p></section>';
  const allocations=p.allocations||[], total=allocations.reduce((s,a)=>s+Number(a.proposed_budget||0),0), scaling=allocations.filter(a=>Number(a.proposed_budget)>Number(a.current_budget)).length;
  return `<div class="kpi-strip plan-strip"><div class="kpi kpi-teal"><div class="kpi-head"><div class="kpi-label">Proposed total</div><div class="kpi-icon">${icon('wallet')}</div></div><div class="kpi-value">${money(total)}</div><div class="kpi-delta">Matches ${money(p.total_budget)} budget</div></div><div class="kpi kpi-blue"><div class="kpi-head"><div class="kpi-label">Explore budget</div><div class="kpi-icon">${icon('trendUp')}</div></div><div class="kpi-value">${Math.round(Number(p.exploration_budget_pct||0)*100)}%</div><div class="kpi-delta">Portfolio exploration policy</div></div><div class="kpi kpi-navy"><div class="kpi-head"><div class="kpi-label">Channels scaling</div><div class="kpi-icon">${icon('check')}</div></div><div class="kpi-value">${scaling}<span class="kpi-of"> of ${allocations.length}</span></div><div class="kpi-delta">Based on prior cycle budgets</div></div></div><section class="card card-tinted"><div class="card-label">Strategy summary</div><p class="strategy-text">${esc(p.strategy_summary)}</p>${p.major_uncertainties?.length?`<div class="alert alert-warning"><div><strong>Major uncertainties:</strong> ${esc(p.major_uncertainties.join(' · '))}</div></div>`:''}</section><section class="card section-gap"><div class="alloc-head"><h2 class="card-title">Allocation changes</h2><div class="alloc-total">${money(total)} proposed</div></div><div class="table-scroll"><table class="table"><thead><tr><th>Channel</th><th>Current spend</th><th>Proposed spend</th><th>Share</th><th>Experiment</th></tr></thead><tbody>${allocations.map(a=>`<tr><td><div class="cell-channel">${esc(labels[a.channel]||a.channel)}</div><button class="expand-toggle" type="button">${esc(a.hypothesis||'Show experiment details')}</button></td><td class="num">${money(a.current_budget)}</td><td class="num cell-proposed">${money(a.proposed_budget)}</td><td class="num">${(Number(a.proposed_share||0)*100).toFixed(1)}%</td><td><details><summary>${esc(a.reason||a.message_angle||'Experiment')}</summary><p>Audience: ${esc(a.audience)}</p><p>Message: ${esc(a.message_angle)}</p><p>Evidence: ${esc(a.evidence_used)}</p><p>Window: ${a.evaluation_window_days} days · Target: ${money(a.success_threshold)}</p></details></td></tr>`).join('')}</tbody></table></div></section>`;
}
function drafts() {
  const c = state.run?.result?.content_package;
  if (!c) return '<section class="card section-gap content-empty"><h2 class="card-title">Content drafts are still being generated</h2><p>The Content agent will attach channel-specific variants here before approval.</p></section>';
  const items=c.items||[], total=items.reduce((n,it)=>n+(it.assets||[]).length,0);
  return `<div class="drafts-banner"><span class="title-icon blue">${icon('fileText')}</span><div class="drafts-banner-text"><div>Creative package for <strong>Cycle ${state.run.cycle_id}</strong></div><div class="drafts-disclaimer">${esc(c.disclaimer||'Review these drafts as proposed experiments; nothing is published automatically.')}</div></div><span class="drafts-count">${items.length} channels · ${total} variants</span></div><div class="content-summary"><div class="card-label">Creative direction</div><p>${esc(c.summary||'Channel-specific creative generated from the approved experiment hypotheses.')}</p></div>${items.map((it,i)=>`<section class="card card-accent section-gap draft-card"><div class="draft-head"><div class="card-title-row"><span class="title-icon ${['','blue','light','orange','navy'][i%5]} num">${i+1}</span><div><h2 class="card-title">${esc(labels[it.channel]||it.channel)}</h2><div class="draft-format">${esc(it.format||'Marketing creative')} · ${it.assets?.length||0} variants</div></div></div><span class="badge badge-awaiting">Draft</span></div><details class="plan-strip"><summary>From the experiment plan</summary><dl class="plan-strip-body"><dt>Targeting</dt><dd>${esc(it.targeting_notes||'')}</dd><dt>Compliance</dt><dd>${esc(it.compliance_notes||'')}</dd></dl></details>${(it.assets||[]).map(a=>`<article class="preview-card"><div class="variant-label">${esc(a.variant_label||'Variant')}</div><h3>${esc(a.headline||'')}</h3><div class="preserve-lines">${esc(a.body||'')}</div>${a.secondary_headlines?.length?`<div class="secondary-lines">${a.secondary_headlines.map(x=>`<span>${esc(x)}</span>`).join('')}</div>`:''}<div class="draft-cta">${esc(a.call_to_action||'')}</div>${a.hashtags?.length?`<div class="pv-hashtags">${a.hashtags.map(x=>`<span class="hashtag">${esc(x.startsWith('#')?x:'#'+x)}</span>`).join('')}</div>`:''}</article>`).join('')}</section>`).join('')}`;
}
function approval() {
  const r=state.run;
  if (!r) return header('Approval','Review a generated plan before it runs.')+statusCard();
  const awaiting=r.status==='WAITING_APPROVAL';
  return `<div class="content-wrap"><header class="approval-header page-head"><div class="page-eyebrow"><span class="dot orange"></span>Step 3 · Approve</div><h1 class="page-title">Cycle ${r.cycle_id} plan</h1><span class="badge ${awaiting?'badge-awaiting':'badge-approved'}">${awaiting?'Awaiting your approval':esc(pretty(r.status))}</span><p class="approval-meta">Generated by the Strategist and Content agents · ${esc(when(r.updated_at))}</p></header>${statusCard()}<div class="tabs" role="tablist"><button class="tab ${state.approvalTab==='plan'?'active':''}" data-tab="plan" type="button">Proposed Plan</button><button class="tab ${state.approvalTab==='drafts'?'active':''}" data-tab="drafts" type="button">Content Drafts</button></div>${state.approvalTab==='drafts'?drafts():planCard()}${awaiting && state.approvalTab==='plan'?`<section class="approval-banner"><div class="banner-icon">${icon('clock')}</div><div class="banner-body"><div class="banner-title">Nothing runs until you approve</div><div class="banner-sub">Review the allocation and content, or send feedback to the Strategist.</div></div><button class="btn btn-human" type="button" data-action="approve" ${state.busy?'disabled':''}>Approve simulation ${icon('trendUp')}</button></section><section class="card section-gap reject-box"><h2 class="card-title">Request a revision</h2><form id="revisionForm"><label class="workspace-field">What should change?<textarea name="feedback" required spellcheck="false" placeholder="For example: keep more budget on high-intent Search and explain the CFO audience more clearly."></textarea></label><button class="btn btn-secondary" type="submit" ${state.busy?'disabled':''}>Send feedback to Strategist</button></form></section>`:''}</div>`;
}
function metrics() {
  const rows=state.run?.result?.results || [];
  if (!rows.length) return '<section class="card"><p>No measured results yet. Results appear after approval and execution.</p></section>';
  const spend=rows.reduce((s,r)=>s+Number(r.spend),0), outcomes=rows.reduce((s,r)=>s+Number(r.primary_outcomes),0);
  return `<div class="workspace-grid metric-grid"><section class="card"><div class="card-label">Simulated spend</div><h2>${money(spend)}</h2></section><section class="card"><div class="card-label">Simulated outcomes</div><h2>${outcomes}</h2></section><section class="card"><div class="card-label">Cost per outcome</div><h2>${outcomes ? money(spend/outcomes) : 'Not measurable'}</h2></section></div>`;
}
function portfolioChart() {
  const runs = (state.workspace?.runs || []).filter(r => r.status === 'COMPLETE' && r.result?.results?.length)
    .sort((a,b) => Number(a.cycle_id) - Number(b.cycle_id));
  if (!runs.length) return `<section class="card section-gap"><h2 class="card-title">Cost per outcome over time</h2><p class="chart-sub">The live chart will appear after the first cycle completes.</p></section>`;
  const W = 1080, H = 390, left = 70, right = 210, top = 28, bottom = 54;
  const plotW = W-left-right, plotH = H-top-bottom;
  const target = Number(state.workspace?.brief?.primary_goal?.target_cac || 0);
  const series = channels.map((ch, i) => ({channel:ch, name:labels[ch], color:['#0097A7','#5574D9','#E38A3C','#8D63B8','#1F8F66'][i], values:runs.map(run => {
    const row = (run.result.results || []).find(x => x.channel === ch);
    return row && Number(row.primary_outcomes) > 0 ? Number(row.observed_cac) : null;
  })})).filter(s => s.values.some(v => v !== null));
  const numbers = series.flatMap(s => s.values.filter(v => v !== null));
  const max = Math.max(target, ...numbers, 1) * 1.18;
  const x = i => left + (runs.length === 1 ? plotW/2 : plotW*i/(runs.length-1));
  const y = value => top + plotH - (value/max)*plotH;
  const grid = [0, .25, .5, .75, 1].map(p => `<line class="chart-grid" x1="${left}" y1="${y(max*p)}" x2="${W-right}" y2="${y(max*p)}" stroke-width="1"/><text class="chart-label" x="${left-10}" y="${y(max*p)+4}" text-anchor="end" font-size="12">S$${Math.round(max*p)}</text>`).join('');
  const lines = series.map(s => {
    let path = '', dots = '';
    s.values.forEach((v,i) => { if (v == null) return; path += `${path && s.values[i-1] != null ? ' L' : 'M'}${x(i)},${y(v)}`; dots += `<circle cx="${x(i)}" cy="${y(v)}" r="5" fill="var(--surface)" stroke="${s.color}" stroke-width="3"><title>Cycle ${runs[i].cycle_id} · ${s.name}: ${money(v)} per outcome</title></circle>`; });
    return `<path class="chart-line" d="${path}" fill="none" stroke="${s.color}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>${dots}`;
  }).join('');
  const targetLine = target ? `<line x1="${left}" y1="${y(target)}" x2="${W-right}" y2="${y(target)}" stroke="#0097A7" stroke-width="2" stroke-dasharray="7 6"/><text x="${W-right+12}" y="${y(target)+4}" fill="#0097A7" font-size="12">Target ${money(target)}</text>` : '';
  const labelsSvg = runs.map((r,i) => `<line class="chart-vgrid" x1="${x(i)}" y1="${top}" x2="${x(i)}" y2="${top+plotH}" stroke-width="1" stroke-dasharray="3 5"/><text class="chart-xlabel" x="${x(i)}" y="${H-18}" text-anchor="middle" font-size="13">Cycle ${r.cycle_id}</text>`).join('');
  return `<section class="card section-gap"><h2 class="card-title">Cost per outcome over time</h2><p class="chart-sub">Completed cycles only · lower is better · gaps mean that channel recorded no outcomes.</p><div class="chart-wrap"><svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Cost per outcome by channel across completed cycles">${grid}${labelsSvg}${targetLine}${lines}</svg></div><div class="chart-legend">${series.map(s=>`<span class="key"><span class="line" style="background:${s.color}"></span>${esc(s.name)}</span>`).join('')}${target?'<span class="key"><span class="line dashed"></span>Target</span>':''}</div></section>`;
}
function analytics() {
  const result=state.run?.result||{}, rows=result.results||[], verdicts=result.analysis_report?.verdicts||[], spend=rows.reduce((s,r)=>s+Number(r.spend||0),0), outcomes=rows.reduce((s,r)=>s+Number(r.primary_outcomes||0),0), best=rows.filter(r=>Number(r.primary_outcomes)>0).sort((a,b)=>Number(a.observed_cac)-Number(b.observed_cac))[0];
  const digest= result.digest_markdown ? `<section class="card digest-card section-gap"><div class="digest-head"><div><div class="card-label">Founder-ready report</div><h2 class="digest-title">Cycle ${state.run?.cycle_id} portfolio digest</h2><p class="digest-tldr">${outcomes?`The simulation produced ${outcomes} ${esc(state.workspace.brief?.primary_goal?.metric_name||'outcomes')} from ${money(spend)} of spend.`:'The cycle is still collecting measured outcomes.'}</p></div>${button('download','Download readable report')}</div><div class="digest-section"><div class="card-label">What happened</div><p>${esc(result.digest_markdown.split(/\n\s*##/)[0].replace(/^#.*\n?/,'').trim()||'The saved digest is available for this cycle.')}</p></div>${verdicts.length?`<div class="digest-section"><div class="card-label">Agent recommendations</div>${verdicts.map(v=>`<div class="digest-verdict"><div class="digest-verdict-head"><strong>${esc(labels[v.channel]||v.channel)}</strong>${verdictBadge(v.verdict)}<span class="digest-conf">${v.confidence==null?'':Math.round(Number(v.confidence)*100)+'% confidence'}</span></div><div>${esc(v.reasoning_summary||'No explanation saved.')}</div></div>`).join('')}</div>`:''}<div class="digest-section"><div class="card-label">Learnings to carry forward</div>${result.learnings?.length?`<ol class="digest-list">${result.learnings.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`:'<p>No learning entries were saved for this cycle.</p>'}</div><details class="digest-technical"><summary>View technical detail</summary><div class="preserve-lines">${esc(result.digest_markdown)}</div></details></section>`:'';
  return `<div class="content-wrap"><header class="page-head"><div class="page-eyebrow"><span class="dot live"></span>Results · Cycle ${state.run?.cycle_id||'—'}</div><h1 class="page-title">Analytics</h1><p class="page-sub">A founder-friendly view of the selected cycle’s simulated outcomes, verdicts and next actions.</p></header>${statusCard()}<div class="kpi-row"><div class="kpi kpi-teal"><div class="kpi-head"><div class="kpi-label">Total outcomes</div><div class="kpi-icon">${icon('users')}</div></div><div class="kpi-value">${countUp(outcomes)}</div><div class="kpi-delta">This cycle</div></div><div class="kpi kpi-blue"><div class="kpi-head"><div class="kpi-label">Best cost per outcome</div><div class="kpi-icon">${icon('target')}</div></div><div class="kpi-value">${best?money(best.observed_cac):'—'}</div><div class="kpi-delta">${best?esc(labels[best.channel]||best.channel):'Awaiting data'}</div></div><div class="kpi kpi-navy"><div class="kpi-head"><div class="kpi-label">Simulated spend</div><div class="kpi-icon">${icon('wallet')}</div></div><div class="kpi-value">${money(spend)}</div><div class="kpi-delta">Across ${rows.length} channels</div></div></div>${portfolioChart()}${rows.length?`<section class="card card-accent section-gap"><h2 class="card-title">Results by channel</h2><div class="table-scroll"><table class="table results-table"><thead><tr><th>Channel</th><th>Spend</th><th>Outcomes</th><th>Cost per outcome</th><th>Window</th><th>Verdict</th></tr></thead><tbody>${rows.map(r=>{const v=verdicts.find(x=>x.channel===r.channel);return `<tr><td class="cell-channel">${esc(labels[r.channel]||r.channel)}</td><td class="num">${money(r.spend)}</td><td class="num">${r.primary_outcomes}</td><td class="num ${v?.verdict==='SCALE'?'cac-good':v?.verdict==='CUT'?'cac-bad':''}">${r.primary_outcomes?money(r.observed_cac):'No outcomes'}</td><td>${r.days_observed}/${r.evaluation_window_days} days</td><td>${v?verdictBadge(v.verdict):'<span class="badge">Pending</span>'}</td></tr>`;}).join('')}</tbody></table></div></section>`:''}${digest}</div>`;
}
function dashboard() {
  const w=state.workspace, r=state.run, result=r?.result||{}, rows=result.results||[], verdicts=result.analysis_report?.verdicts||[];
  const spend=rows.reduce((s,x)=>s+Number(x.spend||0),0), outcomes=rows.reduce((s,x)=>s+Number(x.primary_outcomes||0),0), budget=Number(w.brief?.total_budget||0);
  const plan=result.plan, allocations=plan?.allocations||[], totalPlan=allocations.reduce((s,a)=>s+Number(a.proposed_budget||0),0);
  const done = r?.status==='COMPLETE' ? 4 : r?.status==='WAITING_APPROVAL' ? 2 : r?.status==='RUNNING' ? 1 : 0;
  const steps=['Brief','Plan','Approve','Launch & Measure','Reflect'];
  const allocationColors=['#4B98A7','#8DDCF0','#A9C8F2','#B89BE5','#76B79C'];
  const allocBar=allocations.length ? `<div class="alloc-bar" role="img" aria-label="Current proposed budget allocation">${allocations.map((a,i)=>`<span style="width:${Number(a.proposed_share||0)*100}%;background:${allocationColors[i%allocationColors.length]}"></span>`).join('')}</div>${allocations.map((a,i)=>`<div class="legend-row"><div class="legend-left"><span class="legend-swatch" style="background:${allocationColors[i%allocationColors.length]}"></span>${esc(labels[a.channel]||a.channel)}</div><div class="legend-amount">${money(a.proposed_budget)}</div></div>`).join('')}`:'<p>Allocation details will appear when the Strategist completes a plan.</p>';
  const verdictCards=verdicts.length ? verdicts.map((v,i)=>`<div class="verdict-tile" style="--i:${i}"><div class="verdict-tile-head"><div class="verdict-channel">${esc(labels[v.channel]||v.channel)}</div>${verdictBadge(v.verdict)}</div><div class="verdict-stats"><div class="stat"><div class="stat-label">Confidence</div><div class="stat-value">${v.confidence == null ? '—' : countUp(Number(v.confidence)*100,'','%')}</div></div><div class="stat"><div class="stat-label">Observed CAC</div><div class="stat-value">${v.observed_cac == null ? '—' : money(v.observed_cac)}</div></div><div class="stat"><div class="stat-label">Target CAC</div><div class="stat-value">${money(v.target_cac || w.brief?.primary_goal?.target_cac)}</div></div></div><div class="verdict-conf"><span style="width:${Math.max(0,Math.min(100,Number(v.confidence||0)*100))}%"></span></div><div class="verdict-note">${esc(v.recommended_budget_direction||'')} ${esc(v.reasoning_summary||'')}</div></div>`).join('') : '<p>Analyst verdicts will appear after the cycle completes.</p>';
  return `<div class="content-wrap"><section class="hero" aria-labelledby="dashTitle"><div class="hero-top"><div><div class="hero-eyebrow"><span class="dot"></span>${r ? `Cycle ${r.cycle_id} · ${esc(pretty(r.status))}` : 'Your marketing workspace'}</div><h1 class="page-title hero-title" id="dashTitle">Dashboard</h1><p class="hero-sub">Where the budget sits, what each channel earned, and what needs you next.</p></div><span class="hero-pill ${r?.status==='WAITING_APPROVAL'?'orange':'teal'}">${icon(r?.status==='WAITING_APPROVAL'?'clock':'check')}${r?.status==='WAITING_APPROVAL'?'Waiting on your approval':r?.status==='COMPLETE'?'Cycle complete':'Workflow in progress'}</span></div><div class="hero-body"><div class="hero-money"><div class="hero-money-label">Budget under management</div><div class="hero-money-value"><span class="cur">S$</span>${countUp(budget)}<span class="per">/ cycle</span></div><div class="hero-money-meta"><span>Allocated across <strong>${allocations.length || '—'} channels</strong></span><span class="sep"></span><span><strong>${r ? esc(pretty(r.status)) : 'No cycle yet'}</strong></span></div></div><div class="hero-chart"><div class="hero-chart-head"><div><div class="hero-chart-label">Current cost per outcome</div><div class="hero-chart-value">${outcomes ? money(spend/outcomes) : '—'}</div></div><span class="hero-chart-delta">${outcomes ? `${outcomes} outcomes` : 'Awaiting results'}</span></div>${portfolioChart().replace(/^<section[^>]*>|<\/section>$/g,'')}</div></div></section><div class="kpi-row"><div class="kpi kpi-teal"><div class="kpi-head"><div class="kpi-label">Outcomes this cycle</div><div class="kpi-icon">${icon('users')}</div></div><div class="kpi-value">${countUp(outcomes)}</div><div class="kpi-delta">${r?.status==='COMPLETE'?'Measured simulation outcomes':'Results pending'}</div></div><div class="kpi kpi-blue"><div class="kpi-head"><div class="kpi-label">Cost per outcome</div><div class="kpi-icon">${icon('target')}</div></div><div class="kpi-value">${outcomes?money(spend/outcomes):'—'}</div><div class="kpi-delta">Target ${money(w.brief?.primary_goal?.target_cac)}</div></div><div class="kpi kpi-navy"><div class="kpi-head"><div class="kpi-label">Spent so far</div><div class="kpi-icon">${icon('wallet')}</div></div><div class="kpi-value">${money(spend)}</div><div class="kpi-delta">of ${money(budget)}</div></div><div class="kpi kpi-orange"><div class="kpi-head"><div class="kpi-label">Waiting on you</div><div class="kpi-icon">${icon('clock')}</div></div><div class="kpi-value">${r?.status==='WAITING_APPROVAL'?1:0}</div><div class="kpi-delta">${r?.status==='WAITING_APPROVAL'?'<button class="kpi-link" data-goto="approval">Review plan →</button>':'Nothing needs your decision'}</div></div></div><section class="card cycle-card"><div class="cycle-head"><div class="cycle-title">${r?`Cycle ${r.cycle_id}`:'First cycle'}</div><div class="card-label">Current status</div></div><div class="stepper" aria-label="Cycle progress">${steps.map((name,i)=>`${i?`<div class="step-connector ${i<=done?'done':''}"></div>`:''}<div class="step ${i<done?'done':i===done?'current':''}"><div class="step-num">${i<done?icon('check'):i+1}</div><div class="step-name">${name}</div></div>`).join('')}</div></section><div class="dash-grid"><section class="card"><div class="cycle-head alloc-head-row"><div class="card-label">Allocation ${r?`— Cycle ${r.cycle_id}`:''}</div><div class="alloc-deployed">${money(totalPlan)} proposed</div></div>${allocBar}</section><section class="card verdict-card"><div class="cycle-head verdict-head"><div class="card-label">Latest verdicts</div><div class="verdict-meta">${verdicts.length} channels</div></div>${verdictCards}</section></div>${portfolioChart()}<section class="card section-gap"><h2>Cycle history</h2>${w.runs.length?`<div class="table-scroll"><table class="table"><thead><tr><th>Cycle</th><th>Status</th><th>Started</th><th>Events</th></tr></thead><tbody>${w.runs.map(x=>`<tr><td><button class="btn btn-ghost" data-run="${esc(x.run_id)}">Cycle ${x.cycle_id}</button></td><td>${esc(pretty(x.status))}</td><td>${esc(when(x.created_at))}</td><td>${x.events.length}</td></tr>`).join('')}</tbody></table></div>`:'<p>Your first cycle will appear here after you start planning.</p>'}</section>${result.learnings?.length?`<section class="card section-gap"><h2>Learning carried forward</h2><ul>${result.learnings.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section>`:''}</div>`;
}
function activity() {
  const r=state.run;
  const events=r?.events||[];
  return `<div class="content-wrap"><header class="page-head"><div class="page-eyebrow"><span class="dot live"></span>Live · Cycle ${r?.cycle_id||'—'} workflow</div><h1 class="page-title">Agent Activity</h1><p class="page-sub">Follow the supervisor as it loads context, plans, validates, waits for approval, executes, measures and learns.</p></header>${statusCard()}<div class="activity-layout"><div class="timeline">${events.length?events.map((e,i)=>`<div class="timeline-entry"><div class="tl-time">${esc(when(e.timestamp))}</div><div class="tl-rail"><span class="tl-dot ${e.status==='FAILED'?'orange':i===events.length-1?'teal':''}"></span>${i<events.length-1?'<span class="tl-line"></span>':''}</div><div class="tl-card ${e.status==='FAILED'?'tl-gate':i===events.length-1?'tl-active':''}"><div class="tl-chips"><span class="node-chip">${esc(pretty(e.node))}</span><span class="${e.status==='FAILED'?'repair-chip':e.status==='COMPLETED'?'pass-chip':'gate-chip'}">${esc(pretty(e.status))}</span></div><div class="tl-summary">${esc(e.message||'Workflow event recorded.')}</div>${e.errors?.length?`<div class="tl-summary error-copy">${esc(e.errors.join('; '))}</div>`:''}${e.verdict_summary?.length?`<div class="tl-summary">${esc(e.verdict_summary.join(' · '))}</div>`:''}</div></div>`).join(''):'<section class="card content-empty"><h2 class="card-title">No agent events yet</h2><p>Start a planning cycle to see the live supervisor timeline.</p></section>'}</div><aside class="card reasoning-panel"><div class="card-label">Workflow context</div><div class="reasoning-body">${esc([`Cycle ${r?.cycle_id||'—'}`,`Status: ${pretty(r?.status||'NOT_STARTED')}`,`Events recorded: ${events.length}`,r?.current_node?`Current node: ${pretty(r.current_node)}`:'No node currently running',r?.error?`Error: ${r.error}`:''].filter(Boolean).join('\n'))}</div></aside></div></div>`;
}
function render() {
  sidebar();
  if (!state.workspace) { $('main').innerHTML=`<div class="content-wrap"><h1>Workspace unavailable</h1><p role="alert">${esc(state.error)}</p>${button('refresh','Retry loading')}</div>`; return; }
  const views={brief:renderBrief,dashboard,approval,analytics,activity}; if (!views[state.view]) state.view='brief';
  $('main').innerHTML=`<div class="content-wrap"><div id="syncError" class="workspace-error" role="alert" ${state.error?'':'hidden'}>${esc(state.error)}</div>${state.view==='brief'?'':runPicker()}${views[state.view]()}</div>`;
}
function chooseRun(id) { state.run=state.workspace.runs.find(r=>r.run_id===id); localStorage.setItem(selectionKey(),id); render(); }
async function work(action) {
  if (state.busy) return;
  let payload;
  try { if (action==='save' || action==='start') payload=readBrief(); }
  catch(err) { toast(err.message); return; }
  state.busy=true;
  document.querySelectorAll('#briefForm button, #revisionForm button, [data-action="approve"]').forEach(b=>b.disabled=true);
  try {
    if (action==='save' || action==='start') await saveBrief(payload);
    if (action==='start') {
      const run=await api('/runs','POST',{request_id:crypto.randomUUID()}); state.workspace.runs.unshift(run); state.run=run; localStorage.setItem(selectionKey(),run.run_id); location.hash='activity';
    }
    if (action==='approve' || action==='revise') {
      const feedback = $('revisionForm') ? new FormData($('revisionForm')).get('feedback') : '';
      const run=await api('/runs/'+state.run.run_id+(action==='approve'?'/approve':'/reject'),'POST',action==='revise'?{feedback}:{});
      state.run=run; state.workspace.runs=state.workspace.runs.map(r=>r.run_id===run.run_id?run:r); location.hash='activity';
    }
    state.error=''; if (action==='save') toast('Founder brief saved.');
  } catch(err) { state.error=err.message; toast(err.message); const message=$('briefMessage'); if(message) message.textContent=err.message; }
  finally {
    state.busy=false;
    if (state.view!=='brief') render();
    else document.querySelectorAll('#briefForm button').forEach(b=>b.disabled=b.dataset.action==='start' && state.workspace.runs.some(active));
    schedule();
  }
}
document.addEventListener('submit',e=>{if(e.target.id==='briefForm'){e.preventDefault();work('save');}if(e.target.id==='revisionForm'){e.preventDefault();work('revise');}});
document.addEventListener('change',e=>{if(e.target.id==='runPicker')chooseRun(e.target.value);});
window.addEventListener('hashchange',()=>{state.view=location.hash.slice(1)||'brief';if(state.workspace)render();});
function setSidebar(collapsed) {
  $('appShell').classList.toggle('nav-collapsed',collapsed);
  const toggle=document.querySelector('.sidebar-toggle'); toggle.setAttribute('aria-expanded',String(!collapsed)); toggle.setAttribute('aria-label',collapsed?'Expand sidebar':'Collapse sidebar');
}
document.addEventListener('click',async e=>{
  const a=e.target.closest('[data-action]'), auth=e.target.closest('[data-auth]'), run=e.target.closest('[data-run]');
  const goto=e.target.closest('[data-goto]');
  if(goto){ location.hash=goto.dataset.goto; return; }
  const tab=e.target.closest('[data-tab]');
  if(tab){ state.approvalTab=tab.dataset.tab; render(); return; }
  if(auth){if(auth.dataset.auth==='resend'){try{await cognito('ResendConfirmationCode',{ClientId:cfg.cognitoClientId,Username:$('authUsername').value.trim()});toast('Confirmation code sent.');}catch(err){toast(err.message);}}else setMode(auth.dataset.auth);}
  if(run){chooseRun(run.dataset.run);location.hash='approval';}
  if(a){const action=a.dataset.action;
    if(['start','approve'].includes(action))work(action);
    if(action==='refresh')loadWorkspace();
    if(action==='signout'){localStorage.removeItem(TOKEN);localStorage.removeItem(REFRESH);state.workspace=null;state.run=null;authGate();}
    if(action==='download' && state.run){const digest=state.run.result?.digest_markdown||'No founder digest is available yet.';const text=`Augury — Cycle ${state.run.cycle_id} Founder Report\n${'='.repeat(42)}\n\n${digest}\n`;const blob=new Blob([text],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`augury-cycle-${state.run.cycle_id}-report.txt`;link.click();URL.revokeObjectURL(url);toast('Readable report downloaded.');}
  }
  if(e.target.closest('.sidebar-toggle')){setSidebar(!$('appShell').classList.contains('nav-collapsed'));localStorage.setItem('augury.navCollapsed',$('appShell').classList.contains('nav-collapsed')?'1':'0');}
  if(e.target.closest('.nav-backdrop') || (e.target.closest('[data-view]') && matchMedia('(max-width:900px)').matches))setSidebar(true);
  if(e.target.closest('.theme-toggle')){const theme=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=theme;localStorage.setItem('augury.theme',theme);document.querySelector('.theme-label').textContent=theme==='dark'?'Dark mode':'Light mode';}
  if(e.target.closest('.help-fab'))$('helpPanel').hidden=!$('helpPanel').hidden;
  if(e.target.closest('[data-close-help]'))$('helpPanel').hidden=true;
});
setMode('signin');
setSidebar(matchMedia('(max-width:900px)').matches || localStorage.getItem('augury.navCollapsed')==='1');
matchMedia('(max-width:900px)').addEventListener('change',e=>setSidebar(e.matches));
document.querySelector('.theme-label').textContent=document.documentElement.dataset.theme==='dark'?'Dark mode':'Light mode';
if(localStorage.getItem(TOKEN))loadWorkspace();else authGate();
