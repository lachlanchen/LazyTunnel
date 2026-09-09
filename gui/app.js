'use strict';
const $ = s => document.querySelector(s);
let token = sessionStorage.getItem('lazytunnel-code') || '';
let state = null, refreshing = false, toastTimer, checkTimer;
document.documentElement.dataset.theme = localStorage.getItem('lazytunnel-theme') || 'light';

function node(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}
function toast(message, error = false) {
  clearTimeout(toastTimer);
  $('#toast').textContent = message;
  $('#toast').className = error ? 'error' : '';
  $('#toast').hidden = false;
  toastTimer = setTimeout(() => { $('#toast').hidden = true; }, error ? 10000 : 4000);
}
async function copy(text) {
  try { await navigator.clipboard.writeText(text); toast('Copied. Paste into your terminal.'); }
  catch { toast('Clipboard unavailable. Command: ' + text, true); }
}
function button(text, cls, action) {
  const b = node('button', cls, text);
  b.type = 'button';
  b.addEventListener('click', async () => {
    b.disabled = true;
    try { await action(); } catch (e) { toast(e.message, true); }
    finally { b.disabled = false; }
  });
  return b;
}
function lock() {
  $('.privacy').textContent = '◉ Local access';
  token = ''; sessionStorage.removeItem('lazytunnel-code');
  state = null; clearTimeout(checkTimer);
  $('#unlock').hidden = false; $('#app').hidden = true; $('#lock').hidden = true;
  $('#device-grid').replaceChildren(); $('#viewer-grid').replaceChildren();
  $('#nav-count').textContent = '—';
  if ($('#viewer-dialog').open) $('#viewer-dialog').close();
}
async function api(path, data) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 35000);
  try {
    const response = await fetch(path, {
      method: data === undefined ? 'GET' : 'POST', signal: controller.signal,
      headers: {Authorization: 'Bearer ' + token, ...(data === undefined ? {} : {'Content-Type': 'application/json'})},
      body: data === undefined ? undefined : JSON.stringify(data), credentials: 'omit'
    });
    const result = await response.json();
    if (!response.ok) { if (response.status === 401) lock(); throw new Error(result.error || 'Request failed'); }
    return result;
  } finally { clearTimeout(timer); }
}
function showTab(name) {
  if (!['devices','viewers','guide'].includes(name)) return;
  document.querySelectorAll('.nav').forEach(n => n.classList.toggle('selected', n.dataset.tab === name));
  for (const id of ['devices','viewers','guide']) $('#' + id).hidden = id !== name;
  $('#crumb').textContent = {devices:'Computers',viewers:'Desktop & web',guide:'Quick guide'}[name];
}
function renderDevices() {
  if (!state) return;
  const query = $('#search').value.toLowerCase();
  const peers = state.devices.filter(p => [p.name, p.user, ...p.aliases].join(' ').toLowerCase().includes(query));
  $('#device-grid').replaceChildren(); $('#no-results').hidden = peers.length > 0;
  for (const p of peers) {
    const card = node('article', 'device-card');
    const head = node('div', 'card-head');
    const badge = p.probe?.status || 'unchecked';
    head.append(node('span', 'device-icon', p.local ? '⌂' : '▱'), node('span', 'status ' + badge, {reachable:'● Reachable',unreachable:'○ Unreachable',unchecked:'Not checked'}[badge]));
    const name = node('div');
    name.append(node('h3','card-name',p.name), node('p','muted', p.user + (p.local ? ' · This computer' : ' · Enrolled computer')));
    const detail = node('div','device-detail');
    detail.append(node('span','',p.probe ? new Date(p.probe.checked_at * 1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit'}) : 'On-demand checks'),
      node('span','',p.probe?.status === 'reachable' ? (p.probe.ms / 1000).toFixed(1) + 's SSH connect' : 'Pinned identity'));
    const actions = node('div','card-actions');
    actions.append(button('⌘ Copy SSH','secondary copy',() => copy('ssh-lazy-' + p.name)),button('↻','quiet',() => check(p.name)));
    actions.lastChild.title = 'Check SSH for ' + p.name;
    actions.lastChild.setAttribute('aria-label','Check SSH for ' + p.name);
    card.append(head,name,detail,actions); $('#device-grid').append(card);
  }
}
function renderViewers() {
  $('#viewer-grid').replaceChildren(); $('#empty-viewers').hidden = state.viewers.length > 0;
  for (const v of state.viewers) {
    const card = node('article','viewer-card');
    const art = node('div','viewer-art');
    art.append(node('span','','↗'),node('small','','On demand · no background video'));
    const head = node('div','card-head');
    const label = v.mode === 'local' ? 'Existing viewer' : ({active:'Forward active',activating:'Reconnecting',failed:'Failed',inactive:'Stopped'}[v.status] || v.status);
    head.append(node('h3','card-name',v.name),node('span','status ' + v.status,label));
    const address = node('p','viewer-address',v.device + ' · :' + v.remote_port + v.path);
    const actions = node('div','card-actions');
    if (v.mode === 'local' || v.status === 'active') {
      const open = node('a','primary','Open viewer ↗');
      open.href = v.url; open.target = '_blank'; open.rel = 'noopener noreferrer';
      actions.append(open);
    }
    if (v.mode === 'forward') {
      const running = v.status === 'active' || v.status === 'activating';
      const control = button(running ? 'Stop' : 'Start','secondary',() => viewerAction(v.id,running ? 'stop' : 'start'));
      control.disabled = !state.managed_forwards;
      if (!state.managed_forwards) control.title = 'Managed forwards require a Linux console; the web CLI also works on macOS/Windows.';
      actions.append(control);
    }
    if (v.mode === 'local' || ['inactive','failed','unknown'].includes(v.status)) {
      actions.append(button('Remove','quiet danger', async () => {
        if (confirm('Remove the saved card “' + v.name + '”? The original viewer and desktop will stay unchanged.')) await viewerAction(v.id,'remove');
      }));
    }
    card.append(art,head,address,actions); $('#viewer-grid').append(card);
  }
}
async function refresh() {
  if (!token || refreshing) return;
  refreshing = true;
  try {
    state = await api('/api/state');
    $('.privacy').textContent = '◉ Account: ' + (state.account || 'default');
    $('#unlock').hidden = true; $('#app').hidden = false; $('#lock').hidden = false;
    $('#device-count').textContent = $('#nav-count').textContent = state.devices.length;
    $('#viewer-count').textContent = state.viewers.length;
    $('#online-count').textContent = state.devices.some(p => p.probe) ? state.devices.filter(p => p.probe?.status === 'reachable').length : '—';
    $('#check-all').textContent = state.checking ? 'Checking…' : '↻ Check connections';
    $('#check-all').disabled = state.checking;
    renderDevices(); renderViewers();
    clearTimeout(checkTimer);
    if (state.checking && !document.hidden) checkTimer = setTimeout(() => refresh().catch(e => toast(e.message,true)), 2000);
  } finally { refreshing = false; }
}
async function check(device) {
  await api('/api/check',device ? {device} : {});
  await refresh();
}
async function viewerAction(id,action) {
  await api('/api/viewers/action',{id,action});
  await refresh();
  toast(action === 'start' ? 'Forward enabled. It will reconnect independently of this browser.' : action === 'stop' ? 'Only this forward was stopped.' : 'Saved card removed.');
}
function localMode() {
  const checked = $('#viewer-local').checked;
  if (checked) {
    const local = state.devices.find(p => p.local);
    if (local) $('#viewer-device').value = local.name;
    $('#local-port').value = $('#remote-port').value;
  }
  $('#viewer-device').disabled = checked;
  $('#local-port').readOnly = checked;
}
function addViewer() {
  if (!state) return;
  $('#viewer-form').reset();
  $('#viewer-device').replaceChildren();
  for (const p of state.devices) {
    const option = node('option','',p.name + (p.local ? ' (this computer)' : ''));
    option.value = p.name; $('#viewer-device').append(option);
  }
  $('#viewer-local').disabled = !state.managed_forwards;
  $('#viewer-local').checked = !state.managed_forwards;
  localMode(); $('#viewer-dialog').showModal(); $('#viewer-name').focus();
}
document.querySelectorAll('[data-tab]').forEach(b => b.addEventListener('click',() => showTab(b.dataset.tab)));
document.querySelectorAll('[data-command]').forEach(b => b.addEventListener('click',() => copy(b.dataset.command)));
$('#theme').addEventListener('click',() => {
  const theme = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
  document.documentElement.dataset.theme = theme; localStorage.setItem('lazytunnel-theme',theme);
});
$('#lock').addEventListener('click',lock);
$('#login-form').addEventListener('submit',async e => {
  e.preventDefault(); token = $('#access-code').value.trim();
  $('#access-code').value = '';
  try { await refresh(); sessionStorage.setItem('lazytunnel-code',token); }
  catch (err) { toast(err.message,true); }
});
$('#search').addEventListener('input',renderDevices);
$('#check-all').addEventListener('click',() => check().catch(e => toast(e.message,true)));
for (const mode of ['grid','list']) $('#' + mode + '-mode').addEventListener('click',() => {
  $('#device-grid').classList.toggle('list',mode === 'list');
  $('#grid-mode').classList.toggle('selected',mode === 'grid');
  $('#list-mode').classList.toggle('selected',mode === 'list');
});
$('#add-viewer').addEventListener('click',addViewer); $('#add-empty').addEventListener('click',addViewer);
$('#close-dialog').addEventListener('click',() => $('#viewer-dialog').close());
$('#viewer-local').addEventListener('change',localMode); $('#remote-port').addEventListener('input',localMode);
$('#viewer-form').addEventListener('submit',async e => {
  e.preventDefault(); const submit = e.target.querySelector('[type=submit]'); submit.disabled = true;
  try {
    await api('/api/viewers',{name:$('#viewer-name').value,device:$('#viewer-device').value,
      remote_port:Number($('#remote-port').value),local_port:Number($('#local-port').value),
      path:$('#viewer-path').value,mode:$('#viewer-local').checked ? 'local' : 'forward'});
    $('#viewer-dialog').close(); await refresh(); toast('Viewer saved.');
  } catch (err) { toast(err.message,true); } finally { submit.disabled = false; }
});
setInterval(() => { if (!document.hidden && token) refresh().catch(e => toast(e.message,true)); },15000);
document.addEventListener('visibilitychange',() => { if (!document.hidden && token) refresh().catch(e => toast(e.message,true)); });
if (token) refresh().catch(e => toast(e.message,true));
