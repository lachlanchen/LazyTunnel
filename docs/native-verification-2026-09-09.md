# Native preview 0.2.0 verification — 2026-09-09

This release adds a standalone controller agent, a GUI-independent Dart client,
native Flutter applications, and the LazyRemote launch website. It is a
developer preview, not an App Store, TestFlight or Play Store distribution.

## Build and installation matrix

| Target | Build | Runtime and installation evidence | Distribution |
| --- | --- | --- | --- |
| Ubuntu 24.04 x64 | Release passed | Per-user installer run twice with the same resulting release; native light/dark windows, live agent, fleet and viewers checked | Complete portable bundle plus installer |
| Windows 11 x64 | Release passed with VS 2019 Build Tools | Per-user Start shortcut; native window and responsiveness verified from the interactive user session, screenshot captured | Complete ZIP, no Authenticode signature |
| macOS Intel | Release passed on macOS 15.7.7 / Xcode 26.3 | Installed in user Applications; process and on-screen native window confirmed | Ad-hoc signed ZIP, not notarized |
| Android | Signed release APKs for ARM64, ARMv7, x64 | Android 14 emulator installation, live controller connection, saved profile after restart, and embedded CJK viewer checked | Stable release-key-signed APKs |
| iOS | Simulator and unsigned device builds passed with Xcode 26.3 | Installed; Flutter debugger connected, widget/render trees returned and first-frame rasterization acknowledged; screen capture limitation below | Simulator build and source; physical devices require signing |

All five targets use **Flutter 3.47.2 / Dart 3.13.2**. Ubuntu, Windows and macOS
each passed static analysis and the three native widget tests on their own
build hosts. The widget tests cover phone/desktop layout and rejection of
missing SSH host fingerprints. The pure-Dart package passed seven transport
and data-model tests, and the Python suite passed 56 tests.

## Operational checks

- Both authenticated browser and standalone agent APIs returned the existing
  seven-device fleet. Existing viewer bookmarks were preserved.
- The native Dart client authenticated over real pinned SSH, fetched the fleet,
  opened an SSH PTY and validated a command marker, forwarded a private viewer,
  and closed its own connections. A wrong host fingerprint was rejected.
- Android secure storage preserved a saved connection across a force-stop and
  restart of the test app. No physical phone or unrelated emulator was touched.
- The Android WebView visibly rendered English, Chinese and Japanese from a
  temporary local test page. This is not a claim that every remote desktop or
  mobile dictation/clipboard implementation was tested.
- The SSH carrier, UU bridge and XRDP service process IDs remained unchanged.
  Only the new agent and optional browser adapter were installed/restarted.
- No reboot, logout, graphics-driver change, default-route change or public
  management port was needed. Enabled units establish startup configuration;
  they are not evidence of a reboot test.

## Build and review lessons

**Android API 37.0:** Gradle initially could not resolve the installed platform
with AGP 9.1.0. The official API compatibility table requires **9.1.1**. Pinning
that patch resolved the build. The final manifest also explicitly disables
subdomain matching for loopback-only cleartext HTTP exceptions. Lint remains
enabled.

**Windows toolchain:** the installed Visual Studio Build Tools lacked the ATL
headers required by a plugin. Installing only its ATL component, without a
reboot, fixed compilation. A process inspection made over SSH reported no main
window because it ran outside the interactive window station. Repeating that
inspection as the logged-in user showed a visible, responsive LazyTunnel
window, and a screenshot confirmed rendering. The original Impeller build
worked; a speculative renderer override was removed. Do not change graphics
settings to compensate for a window-inspection context error.

**macOS privacy:** CoreGraphics confirmed the app's on-screen window. The
existing Screen Recording/Accessibility permissions blocked remote screenshot
and UI automation. These permissions were not weakened for the build.

**iOS simulator:** the initial headless launch accepted the application but
returned a black capture. A later capture reported `Timeout waiting for screen
surfaces`. A final launch using Flutter's debugger and the existing prebuilt
bundle connected to the Dart VM, returned the application's widget/render
trees, and reported `didSendFirstFrameRasterizedEvent` as true. The capture
still contained only black pixels. Launching Apple's Safari in the same
simulator also produced an entirely black capture. This points to the host's
simulator display/capture path; it does not establish that the application
itself displays a black screen.

No interactive iOS visual check or signed physical-device installation is
claimed. Treat the simulator artifact as a developer preview and validate on
your own supported Xcode host before relying on it. The owned simulator was
shut down after this check; no global simulator, graphics or privacy settings
were changed.

**iOS signing:** two existing matching development identities were present,
but command-line signing returned `errSecInternalComponent`, including after
unlocking the build user's keychain. Key ACLs and partition lists were not
rewritten. No signed physical-device installation is claimed. Use the included
`sign-ios-development.py` helper with a signing identity that the operator has
authorized for codesign, or sign through Xcode normally. An IPA containing a
development provisioning profile must remain private because it lists devices.

**Mobile limits:** native interactive SSH and viewer connections need the app
in the foreground. Persistent controller services remain independent. This is
not an always-on background mobile daemon or a replacement for noVNC's own
authentication and clipboard support.

## Launch website and screenshots

https://remote.lazying.art is a static public website, never a public endpoint
to the private agent. Browser checks passed at 390, 768 and 1440 pixels with no
horizontal overflow. All five platform tabs, image loading, screenshot dialog
and FAQ were exercised. Real Linux and Android application captures use the
read-only sample fleet in `scripts/demo-agent.py`, not private operator data.
See [brand provenance](lazyremote-brand.md) and [website maintenance](../website/README.md).

## Reference material

- [Native setup, builds and signing](native-apps.md)
- [Android API/AGP compatibility](https://developer.android.com/build/releases/about-agp)
- [Flutter Impeller and desktop behavior](https://docs.flutter.dev/perf/impeller)
- [Flutter Windows embedding API](https://api.flutter.dev/windows-embedder/dart__project_8h_source.html)

## Published release and cleanup

[Preview 0.2.0](https://github.com/lachlanchen/LazyTunnel/releases/tag/v0.2.0)
is public. All ten uploaded assets were compared with their local SHA-256
digests and sizes; the public checksum download returned the same file.
The release also includes full-page
[desktop](https://github.com/lachlanchen/LazyTunnel/releases/download/v0.2.0/LazyRemote-website-desktop.png)
and [mobile](https://github.com/lachlanchen/LazyTunnel/releases/download/v0.2.0/LazyRemote-website-mobile.png)
website screenshots.

GitHub Pages completed successfully and HTTPS is enforced. The live site
passed image loading, all platform tabs, arrow/Home/End keyboard navigation,
and the same three responsive widths, with no JavaScript errors.

The temporary Ubuntu preview desktop, sample agent and viewer fixture were
stopped after capture. The Android test emulator and Windows preview app were
closed; completed Windows build/review tasks were removed. Installed apps and
the existing fleet service remain available. The standalone controller and
browser adapter are enabled under the lingering user systemd manager.

Credentials, signing keys, provisioning profiles, browser profiles, SDKs and
private logs are excluded from the public release.
