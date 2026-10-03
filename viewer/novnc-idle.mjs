// Adapter for the existing full noVNC UI. Never replaces its input handling.
import UI from './app/ui.js';
import { IdlePolicy } from './idle-policy.mjs';

const policy = new IdlePolicy();
policy.visibility(document.hidden, Date.now());
let paused = false;
let previousRfb;
const bar = document.createElement('div');
bar.id = 'lazytunnel-idle-bar';
const status = document.createElement('span');
const pauseButton = document.createElement('button');
const label = document.createElement('label');
const keep = document.createElement('input');
keep.type = 'checkbox';
label.append(keep, ' Keep live while visible');
bar.append(status, pauseButton, label);
document.body.append(bar);
const overlay = document.createElement('div');
overlay.id = 'lazytunnel-idle-overlay';
overlay.hidden = true;
const message = document.createElement('p');
const resumeButton = document.createElement('button');
resumeButton.textContent = 'Resume desktop';
overlay.append(message, resumeButton);
document.body.append(overlay);

function render() {
    status.textContent = paused ? 'Paused · desktop stream closed' : 'Data saver · pauses after 2 minutes idle';
    pauseButton.textContent = paused ? 'Resume' : 'Pause';
    overlay.hidden = !paused;
}
function pause(reason) {
    if (paused) return;
    // Use noVNC's deliberate-disconnect path to inhibit its auto-reconnect.
    UI.inhibitReconnect = true;
    if (UI.reconnectCallback != null) {
        clearTimeout(UI.reconnectCallback);
        UI.reconnectCallback = null;
    }
    if (UI.rfb) UI.disconnect();
    paused = true;
    message.textContent = (reason === 'hidden' ? 'Viewer paused while hidden.' : 'Viewer paused to save data.') +
        ' Your remote apps are still running. Resume when ready.';
    render();
}
function resume(event) {
    // This click only resumes: it is never forwarded as a desktop click/key.
    event?.preventDefault();
    event?.stopPropagation();
    if (document.hidden || UI.rfb) return;
    policy.activity(Date.now());
    paused = false;
    UI.inhibitReconnect = false;
    UI.connect(null, UI.reconnectPassword);
    render();
}
pauseButton.addEventListener('click', e => paused ? resume(e) : pause('manual'));
resumeButton.addEventListener('click', resume);
keep.addEventListener('change', () => {
    policy.keepLive = keep.checked;
    policy.activity(Date.now());
});
for (const event of ['pointerdown', 'pointermove', 'keydown', 'wheel', 'touchstart', 'input', 'compositionend']) {
    document.addEventListener(event, e => {
        if (e.isTrusted && !paused) policy.activity(Date.now());
    }, {capture: true, passive: true});
}
document.addEventListener('visibilitychange', () => {
    policy.visibility(document.hidden, Date.now());
});
// Page close/freeze also releases the WebSocket. Returning never reconnects secretly.
window.addEventListener('pagehide', () => pause('hidden'));
document.addEventListener('freeze', () => pause('hidden'));
setInterval(() => {
    if (UI.rfb && UI.rfb !== previousRfb) {
        previousRfb = UI.rfb;
        policy.activity(Date.now());
        // Higher compression without changing keyboard, clipboard, dimensions or quality.
        UI.rfb.compressionLevel = 6;
        if (paused) UI.disconnect();
    }
    const reason = policy.reason(Date.now());
    if (reason && (UI.rfb || UI.reconnectCallback != null)) pause(reason);
}, 1000);
render();
