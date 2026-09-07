/* Augury: all business data is loaded from the authenticated workspace API. */
'use strict';
const cfg = window.AUGURY_CONFIG;
const TOKEN = 'augury.idToken', REFRESH = 'augury.refreshToken';
const state = { workspace: null, run: null, view: location.hash.slice(1) || 'brief', busy: false, error: '', timer: null, authMode: 'signin' };
const channels = ['GOOGLE_SEARCH', 'LINKEDIN', 'META', 'COLD_EMAIL', 'FOUNDER_CONTENT'];
const labels = { GOOGLE_SEARCH: 'Google Search', LINKEDIN: 'LinkedIn', META: 'Meta', COLD_EMAIL: 'Cold Email', FOUNDER_CONTENT: 'Founder Content' };
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const money = (v) => v == null ? '—' : new Intl.NumberFormat('en-SG', { style:'currency', currency:'SGD' }).format(Number(v));
const when = (v) => v ? new Date(v.endsWith('Z') || /[+-]\d\d:\d\d$/.test(v) ? v : v + 'Z').toLocaleString() : '—';
const pretty = (s) => String(s || '').replaceAll('_',' ').toLowerCase();
const active = (r) => r && ['QUEUED','RUNNING','WAITING_APPROVAL'].includes(r.status);
const button = (action, text, disabled = false) => `<button type="button" class="btn btn-primary" data-action="${action}" ${disabled ? 'disabled' : ''}>${text}</button>`;
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
function field(name, label, value, type='text', extra='') { return `<label class="workspace-field">${label}<input name="${name}" type="${type}" value="${esc(value)}" required ${extra}></label>`; }
function select(name,label,values,value) { return `<label class="workspace-field">${label}<select name="${name}">${values.map(v => `<option value="${v}" ${v===value?'selected':''}>${esc(pretty(v))}</option>`).join('')}</select></label>`; }
function renderBrief() {
  const b = state.workspace.brief || {}, p = state.workspace.profile || {}, g = b.primary_goal || {};
  return header('Founder Brief','Describe the company and the outcome you want to improve. Saved inputs are used for the next cycle.') + `<form id="briefForm" class="card workspace-form"><div class="workspace-grid">
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
    </div><label class="workspace-field">Product, target audience and value proposition<textarea name="one_line_pitch" required rows="4">${esc(b.one_line_pitch || '')}</textarea></label>
    <h2>Channel boundaries and preferences</h2><p>Exclude channels you cannot use. Preferences guide the Strategist without fixing its allocation.</p>
    ${channels.map(ch => { const ex = (b.hard_exclusions || []).find(e=>e.channel===ch), pref = (b.soft_preferences || []).find(e=>e.channel===ch); return `<fieldset class="channel-input"><legend>${labels[ch]}</legend><label><input type="checkbox" name="exclude_${ch}" ${ex?'checked':''}> Exclude this channel</label><label class="workspace-field">Exclusion reason<input name="reason_${ch}" value="${esc(ex?.reason || '')}"></label><label class="workspace-field">Founder preference<input name="note_${ch}" value="${esc(pref?.founder_note || '')}" placeholder="Optional"></label><label class="workspace-field">Belief strength (0–1)<input type="number" name="strength_${ch}" min="0" max="1" step="0.1" value="${pref?.prior_belief_strength ?? 0.5}"></label></fieldset>`; }).join('')}
    <p class="workspace-notice">Agents use ${esc(state.workspace.model_mode)}. Campaign outcomes are generated by the market simulator; no ads are published or charged.</p>
    <div id="briefMessage" role="status"></div><div class="workspace-actions"><button class="btn btn-primary" type="submit" ${state.busy?'disabled':''}>Save founder brief</button>${button('start','Save and start planning',state.busy || state.workspace.runs.some(active))}</div></form>`;
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
  return `<section class="card"><h2>Strategy</h2><p>${esc(p.strategy_summary)}</p><p>Budget ${money(p.total_budget)} · ${esc(p.primary_goal)} · Exploration ${(p.exploration_budget_pct*100).toFixed(0)}%</p>${p.major_uncertainties?.length?`<h3>Assumptions to test</h3><ul>${p.major_uncertainties.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:''}</section><section class="card section-gap"><h2>Proposed experiments</h2><div class="table-scroll"><table class="table"><thead><tr><th>Channel</th><th>Previous budget</th><th>Proposed budget</th><th>Share</th><th>Experiment</th></tr></thead><tbody>${p.allocations.map(a=>`<tr><td>${esc(labels[a.channel] || a.channel)}</td><td>${money(a.current_budget)}</td><td>${money(a.proposed_budget)}</td><td>${(a.proposed_share*100).toFixed(1)}%</td><td><details><summary>${esc(a.hypothesis)}</summary><p>Audience: ${esc(a.audience)}</p><p>Message: ${esc(a.message_angle)}</p><p>Reason: ${esc(a.reason)}</p><p>Evidence: ${esc(a.evidence_used)}</p><p>Window: ${a.evaluation_window_days} days · Target: ${money(a.success_threshold)}</p></details></td></tr>`).join('')}</tbody></table></div></section>`;
}
function drafts() {
  const c = state.run?.result?.content_package;
  if (!c) return '<section class="card section-gap"><h2>Content drafts</h2><p>Drafts will appear when the Content agent completes generation.</p></section>';
  return `<section class="card section-gap"><h2>Content drafts</h2><p>${esc(c.summary)}</p><p>${esc(c.disclaimer)}</p>${c.items.map(it=>`<details class="content-draft"><summary>${esc(labels[it.channel] || it.channel)} · ${it.assets.length} variants</summary><p>${esc(it.targeting_notes)}</p>${it.assets.map(a=>`<article><h3>${esc(a.variant_label)} · ${esc(a.headline)}</h3><div class="preserve-lines">${esc(a.body)}</div>${a.secondary_headlines?.map(x=>`<p>${esc(x)}</p>`).join('') || ''}<p>${esc(a.call_to_action)}</p><p>${esc((a.hashtags || []).join(' '))}</p></article>`).join('')}<p>${esc(it.compliance_notes)}</p></details>`).join('')}</section>`;
}
function approval() {
  const r=state.run;
  return header(r ? `Cycle ${r.cycle_id} plan` : 'Approval','Review the saved plan and content. Approval executes this exact version.') + statusCard() + (r ? planCard()+drafts() : '') + (r?.status==='WAITING_APPROVAL' ? `<section class="card section-gap"><div class="workspace-actions">${button('approve','Approve and run simulation',state.busy)}</div><form id="revisionForm"><label class="workspace-field">Changes to request<textarea name="feedback" required placeholder="Explain which allocations or assumptions should change"></textarea></label><button class="btn btn-secondary" type="submit" ${state.busy?'disabled':''}>Request revised plan</button></form></section>`:'');
}
function metrics() {
  const rows=state.run?.result?.results || [];
  if (!rows.length) return '<section class="card"><p>No measured results yet. Results appear after approval and execution.</p></section>';
  const spend=rows.reduce((s,r)=>s+Number(r.spend),0), outcomes=rows.reduce((s,r)=>s+Number(r.primary_outcomes),0);
  return `<div class="workspace-grid metric-grid"><section class="card"><div class="card-label">Simulated spend</div><h2>${money(spend)}</h2></section><section class="card"><div class="card-label">Simulated outcomes</div><h2>${outcomes}</h2></section><section class="card"><div class="card-label">Cost per outcome</div><h2>${outcomes ? money(spend/outcomes) : 'Not measurable'}</h2></section></div>`;
}
function analytics() {
  const result=state.run?.result || {}, rows=result.results || [], verdicts=result.analysis_report?.verdicts || [];
  return header('Analytics','Computed from the selected cycle’s generated simulation telemetry. These are not live campaign results.') + statusCard()+metrics()+(rows.length ? `<section class="card section-gap"><h2>Channel results</h2><div class="table-scroll"><table class="table"><thead><tr><th>Channel</th><th>Spend</th><th>Outcomes</th><th>Cost per outcome</th><th>Window</th><th>Analyst verdict</th></tr></thead><tbody>${rows.map(r=>{const v=verdicts.find(v=>v.channel===r.channel);return `<tr><td>${esc(labels[r.channel])}</td><td>${money(r.spend)}</td><td>${r.primary_outcomes}</td><td>${r.primary_outcomes?money(r.observed_cac):'No outcomes'}</td><td>${r.days_observed}/${r.evaluation_window_days} simulated days</td><td>${v?`<strong>${esc(v.verdict)}</strong><p>${esc(v.reasoning_summary)}</p>`:'Analysis pending'}</td></tr>`;}).join('')}</tbody></table></div></section>`:'') + (result.digest_markdown ? `<section class="card section-gap"><h2>Founder digest</h2><div class="preserve-lines">${esc(result.digest_markdown)}</div>${button('download','Download cycle report')}</section>`:'');
}
function dashboard() {
  const w=state.workspace;
  return header('Dashboard','Your saved workflow, plans and learning history.') + statusCard()+metrics()+`<section class="card section-gap"><h2>Cycle history</h2>${w.runs.length?`<div class="table-scroll"><table class="table"><thead><tr><th>Cycle</th><th>Status</th><th>Started</th><th>Events</th></tr></thead><tbody>${w.runs.map(r=>`<tr><td><button class="btn btn-ghost" data-run="${esc(r.run_id)}">Cycle ${r.cycle_id}</button></td><td>${esc(pretty(r.status))}</td><td>${esc(when(r.created_at))}</td><td>${r.events.length}</td></tr>`).join('')}</tbody></table></div>`:'<p>Your first cycle will appear here after you start planning.</p>'}</section>${state.run?.result?.learnings?.length?`<section class="card section-gap"><h2>Learning carried forward</h2><ul>${state.run.result.learnings.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section>`:''}`;
}
function activity() {
  const r=state.run;
  return header('Agent Activity','Recorded node starts and completions from the supervisor. Refreshing reloads this history.')+statusCard()+`<section class="card section-gap"><h2>Execution timeline</h2>${r?.events.length?`<ol class="workspace-timeline">${r.events.map(e=>`<li class="event-${esc(e.status)}"><time>${esc(when(e.timestamp))}</time><div><strong>${esc(pretty(e.node))} · ${esc(e.status)}</strong><p>${esc(e.message)}</p>${e.errors?.length?`<p>${esc(e.errors.join('; '))}</p>`:''}${e.verdict_summary?`<p>${esc(e.verdict_summary.join(' · '))}</p>`:''}</div></li>`).join('')}</ol>`:'<p>No recorded events yet.</p>'}</section>`;
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
  if(auth){if(auth.dataset.auth==='resend'){try{await cognito('ResendConfirmationCode',{ClientId:cfg.cognitoClientId,Username:$('authUsername').value.trim()});toast('Confirmation code sent.');}catch(err){toast(err.message);}}else setMode(auth.dataset.auth);}
  if(run){chooseRun(run.dataset.run);location.hash='approval';}
  if(a){const action=a.dataset.action;
    if(['start','approve'].includes(action))work(action);
    if(action==='refresh')loadWorkspace();
    if(action==='signout'){localStorage.removeItem(TOKEN);localStorage.removeItem(REFRESH);state.workspace=null;state.run=null;authGate();}
    if(action==='download' && state.run){const blob=new Blob([JSON.stringify(state.run,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=`augury-cycle-${state.run.cycle_id}.json`;link.click();URL.revokeObjectURL(url);}
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
