# LazyTunnel native app

A real Flutter application for Ubuntu, macOS, Windows, iOS and Android.
The agent and reusable transport remain independent of this UI.

- Native computer inventory, saved connections and status checks.
- Verified SSH, optional cloud jump, UTF-8 terminals and private viewers.
- Light/dark themes, responsive desktop/mobile navigation and platform secure storage.
- A mobile WebView only for forwarded noVNC/web content; desktop viewers use the normal browser.

Start with the [complete installation and connection guide](../../docs/native-apps.md).
The [pure-Dart core](../../packages/lazytunnel_client) has no Flutter dependency.

```bash
# With the pinned Flutter SDK in PATH
flutter pub get --enforce-lockfile
flutter analyze
flutter test
flutter run -d linux
```

Signing credentials and connection profiles are external to source. Do not copy
SDKs, signing keys or build caches into this directory or a public archive.
