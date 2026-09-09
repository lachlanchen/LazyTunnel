# LazyTunnel client core

A pure-Dart package for the independent LazyTunnel agent. It imports no Flutter
widgets, browser assets, secure-storage plugin or desktop shell.

- Typed inventory, viewer and connection models.
- Authenticated, bounded loopback HTTP, with redirects disabled.
- SSH transport with mandatory SHA256 host-key pinning and an optional verified jump.
- Loopback-only viewer forwarding and UTF-8 PTY streams.
- Explicit connection ownership and cleanup.

The application supplies credentials and decides whether to persist them in its
platform secret store. A plain profile contains no credentials. SSH host-key
changes are rejected; there is no silent accept-all fallback.

```sh
cd packages/lazytunnel_client
dart pub get
dart analyze
dart test
```

`bin/verify_connection.dart` accepts a private JSON connection packet and verifies
the agent, a fleet terminal and an available viewer. It prints counts and
outcomes, not credentials. Keep its input outside the repository.

See [native application guide](../../docs/native-apps.md) for architecture,
platform packaging, connection setup and mobile lifecycle limits.
