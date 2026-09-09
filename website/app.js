'use strict';
const release = 'https://github.com/lachlanchen/LazyTunnel/releases/download/v0.2.0/';
const platformSets = { en: {
 linux: ['LINUX · x64', 'A home on your desktop.', 'A native GTK desktop application. Install the complete bundle with the included per-user installer.', 'Get Ubuntu build', release + 'LazyTunnel-0.2.0-linux-x64.tar.gz', 'Ubuntu 24.04 verified. The app itself needs no administrator privileges.'],
 macos: ['macOS · INTEL', 'Your Mac. Your workspace.', 'A native macOS app with Keychain storage and private SSH connections. This preview build targets Intel Macs.', 'Get macOS build', release + 'LazyTunnel-0.2.0-macos-x64.zip', 'Built on macOS 15.7. Apple Silicon builds are available from source. This preview is not notarized; follow the release instructions.'],
 windows: ['WINDOWS · x64', 'A familiar place to connect.', 'A native Windows app. Unzip the complete bundle and use the included Start-menu installer.', 'Get Windows build', release + 'LazyTunnel-0.2.0-windows-x64.zip', 'Windows 11 verified. Requires the Microsoft Visual C++ runtime. This preview has no Authenticode signature.'],
 ios: ['iOS · DEVELOPER PREVIEW', 'Your computers, in your pocket.', 'Native iPhone and iPad screens, in-app SSH terminals, and a foreground viewer. Build with Xcode and your own Apple signing.', 'iOS build & signing guide', 'https://github.com/lachlanchen/LazyTunnel/blob/main/docs/native-apps.md#ios-signing', 'Simulator and device builds verified. Not distributed on the App Store or TestFlight. Installation requires provisioning.'],
 android: ['ANDROID · ARM64', 'Room for your whole workspace.', 'A signed Android APK with secure saved profiles, native terminal controls, and embedded private viewers.', 'Get Android APK', release + 'LazyTunnel-0.2.0-android-arm64.apk', 'Android 7.0 or later. Tested on an Android 14 emulator. Other architectures and signing checksums are in the release.']
}, 'zh-hans': {
 linux: ['LINUX · x64', '在桌面上，回到自己的电脑。', '原生 GTK 桌面应用。完整压缩包内含用户级安装程序。', '下载 Ubuntu 版本', release + 'LazyTunnel-0.2.0-linux-x64.tar.gz', '已在 Ubuntu 24.04 验证；应用本身无需管理员权限。'],
 macos: ['macOS · INTEL', '你的 Mac，你的工作空间。', '原生 macOS 应用，使用钥匙串保存资料并建立私有 SSH 连接。本预览包面向 Intel Mac。', '下载 macOS 版本', release + 'LazyTunnel-0.2.0-macos-x64.zip', '构建于 macOS 15.7。Apple Silicon 可从源码构建；本预览版未经公证，请按发行说明操作。'],
 windows: ['WINDOWS · x64', '熟悉的电脑，随时可以连接。', '原生 Windows 应用。解压完整包后，使用随附的开始菜单安装程序。', '下载 Windows 版本', release + 'LazyTunnel-0.2.0-windows-x64.zip', '已在 Windows 11 验证。需要 Microsoft Visual C++ 运行库；本预览版没有 Authenticode 签名。'],
 ios: ['iOS · 开发者预览', '把自己的电脑放进口袋。', '原生 iPhone 和 iPad 界面，带应用内 SSH 终端和前台查看器。请用 Xcode 和自己的 Apple 签名构建。', '查看 iOS 构建与签名指南', 'https://github.com/lachlanchen/LazyTunnel/blob/main/docs/native-apps.md#ios-signing', '模拟器和真机版本已经验证，但尚未通过 App Store 或 TestFlight 分发；安装需要自行配置签名。'],
 android: ['ANDROID · ARM64', '小屏幕，也容得下整个工作空间。', '已签名的 Android APK，提供安全保存的连接资料、原生终端控件和内嵌私有查看器。', '下载 Android APK', release + 'LazyTunnel-0.2.0-android-arm64.apk', '支持 Android 7.0 及以上版本，已在 Android 14 模拟器验证；其他架构与签名校验值见发行页。']
}};
const pageLanguage = document.documentElement.lang.toLowerCase();
const platforms = platformSets[pageLanguage] || platformSets.en;
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
