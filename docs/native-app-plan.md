# Native application delivery plan

Goal: installable Ubuntu, macOS, Windows, iOS and Android applications with an
agent and transport library independent of both user interfaces.

## Architecture contract

- The cloud relay remains OpenSSH with its existing restricted identities.
- A standalone Python agent owns device inventory, bounded checks and saved
  forwarding configuration; it imports no web assets or Flutter widgets.
- The web console and native application are separate authenticated API clients.
- The native application uses Flutter widgets. Its reusable Dart package owns
  typed API models, connection profiles and SSH transport without importing Flutter.
- Secret persistence is an adapter at the application boundary, using the
  platform's secure storage. Secrets, signing material and device-specific
  connection profiles stay outside Git and release packages.
- Native SSH forwarding binds loopback and verifies host keys. On desktops,
  existing persistent forwards remain agent-managed when the app closes.
- Mobile foreground/suspension limits must be explicit; do not claim an always-on
  iOS background SSH daemon or modify existing remote-desktop sessions.

## Delivery sequence

1. Audit existing build tools and hosts; pin a supported Flutter release.
2. Extract the UI-independent agent and preserve web/CLI API compatibility.
3. Implement and test a pure-Dart client/transport package.
4. Build the real native UI: connect/unlock, inventory, SSH actions, viewers,
   saved profiles, secure persistence, connection status and lifecycle handling.
5. Compile/test Linux and Android, then Windows, macOS and iOS on appropriate
   build hosts. Run heavy build jobs sequentially and reuse SDK installations.
6. Package outputs, record hashes and actual tests, and provide signing/install
   instructions. Never substitute a platform folder for a verified build.
7. Preserve live services, document deployment/rollback, update public guides
   and publish reviewed code and suitable artifacts.

## Build scope

App-store publication is separate from building. An unsigned iOS archive is not
an installable signed IPA. State any signing/provisioning dependency explicitly
and pursue available build and simulator verification before reporting a blocker.

Use the private runtime record for live host details, SDK paths, build logs,
credentials and progress. Do not place those records in this public plan.

## Research sources

- [Flutter desktop support](https://docs.flutter.dev/platform-integration/desktop)
- [Supported deployment platforms](https://docs.flutter.dev/reference/supported-platforms)
- [Official SDK archive](https://docs.flutter.dev/install/archive)
- [dartssh2](https://pub.dev/packages/dartssh2): explicit host-key verification
- [flutter_secure_storage](https://pub.dev/packages/flutter_secure_storage)
