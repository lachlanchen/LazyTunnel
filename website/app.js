'use strict';
const release = 'https://github.com/lachlanchen/LazyTunnel/releases/download/v0.2.0/';
const platforms = {
 linux: ['LINUX · x64', 'A home on your desktop.', 'A native GTK desktop application. Install the complete bundle with the included per-user installer.', 'Get Ubuntu build', release + 'LazyTunnel-0.2.0-linux-x64.tar.gz', 'Ubuntu 24.04 verified. The app itself needs no administrator privileges.'],
 macos: ['macOS · INTEL', 'Your Mac. Your workspace.', 'A native macOS app with Keychain storage and private SSH connections. This preview build targets Intel Macs.', 'Get macOS build', release + 'LazyTunnel-0.2.0-macos-x64.zip', 'Built on macOS 15.7. Apple Silicon builds are available from source. This preview is not notarized; follow the release instructions.'],
 windows: ['WINDOWS · x64', 'A familiar place to connect.', 'A native Windows app. Unzip the complete bundle and use the included Start-menu installer.', 'Get Windows build', release + 'LazyTunnel-0.2.0-windows-x64.zip', 'Windows 11 verified. Requires the Microsoft Visual C++ runtime. This preview has no Authenticode signature.'],
 ios: ['iOS · DEVELOPER PREVIEW', 'Your computers, in your pocket.', 'Native iPhone and iPad screens, in-app SSH terminals, and a foreground viewer. Build with Xcode and your own Apple signing.', 'iOS build & signing guide', 'https://github.com/lachlanchen/LazyTunnel/blob/main/docs/native-apps.md#ios-signing', 'Simulator and device builds verified. Not distributed on the App Store or TestFlight. Installation requires provisioning.'],
 android: ['ANDROID · ARM64', 'Room for your whole workspace.', 'A signed Android APK with secure saved profiles, native terminal controls, and embedded private viewers.', 'Get Android APK', release + 'LazyTunnel-0.2.0-android-arm64.apk', 'Android 7.0 or later. Tested on an Android 14 emulator. Other architectures and signing checksums are in the release.']
};
const tabs = [...document.querySelectorAll('[data-os]')];
function selectPlatform(key, focus = false) {
 if (!platforms[key]) return;
 const [badge, title, description, label, url, note] = platforms[key];
 tabs.forEach(tab => { const active = tab.dataset.os === key; tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1; if (active && focus) tab.focus(); });
 document.getElementById('download-badge').textContent = badge;
 document.getElementById('download-title').textContent = title;
 document.getElementById('download-description').textContent = description;
 const link = document.getElementById('download-link'); link.textContent = label + ' ↗'; link.href = url;
 document.getElementById('download-note').textContent = note;
 document.getElementById('download-detail').setAttribute('aria-labelledby', 'tab-' + key);
}
tabs.forEach((tab, i) => {
 tab.addEventListener('click', () => selectPlatform(tab.dataset.os));
 tab.addEventListener('keydown', event => {
  let next;
  if (event.key === 'ArrowRight') next = (i + 1) % tabs.length;
  if (event.key === 'ArrowLeft') next = (i + tabs.length - 1) % tabs.length;
  if (event.key === 'Home') next = 0;
  if (event.key === 'End') next = tabs.length - 1;
  if (next !== undefined) { event.preventDefault(); selectPlatform(tabs[next].dataset.os, true); }
 });
});
const ua = navigator.userAgent;
selectPlatform(/Android/.test(ua) ? 'android' : /iPhone|iPad/.test(ua) ? 'ios' : /Windows/.test(ua) ? 'windows' : /Macintosh/.test(ua) ? 'macos' : 'linux');
const modal = document.getElementById('screenshot-dialog');
document.querySelectorAll('.screenshot-button').forEach(button => button.addEventListener('click', () => {
 const image = document.getElementById('screenshot-full'); image.src = button.dataset.image; image.alt = button.dataset.caption;
 document.getElementById('screenshot-caption').textContent = button.dataset.caption;
 modal.showModal();
}));
document.getElementById('close-screenshot').addEventListener('click', () => modal.close());
modal.addEventListener('click', event => { if (event.target === modal) { const r = modal.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) modal.close(); } });
