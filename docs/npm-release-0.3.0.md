# CLI 0.3.0: independent accounts

The npm package adds optional account isolation to the existing SSH fleet.
Server operators can create key/password accounts and pinned invitations.
Users can enroll, list and revoke their own devices; the server scopes keys,
bundles and SSH destinations to the authenticated owner.

- Complete setup: [accounts.md](accounts.md).
- Existing version-1 fleets are preserved as `default` on an explicit upgrade.
  Merely installing/updating npm does not migrate a relay or restart services.
- The shared Node CLI adds account login/administration, while native OpenSSH
  provides authentication. No public HTTP login service or new npm dependency.
- The local console shows the enrolled account. Public signup, billing, guest
  sharing and native-app cloud enrollment screens remain outside this release.
- Membership refresh is explicit with client `sync`. Relay revocation is
  immediate and ends affected old SSH sessions; direct endpoint permissions
  require sync and review of separately granted manual keys.

## Validation

The development run passed 12 Node tests, 81 Python tests, profile checks for
all 11 READMEs and the npm package allowlist/credential inspection. The real
SSH integration test runs in disposable Ubuntu 24.04 Docker with no host ports.
It checks key/password authentication, the actual Node account CLI, isolation,
idempotent enrollment, spoofing rejection, effective-policy rollback with file
owner/mode preservation, and another account staying connected during revocation.

The production relay and existing UU/RDP/VNC/fleet processes were not modified.
No reboot or new Windows/macOS account-login acceptance run is claimed.

Publication uses the existing npm trusted publisher and GitHub provenance,
tag `npm-v0.3.0`. The CI workflow repeats the real SSH integration test before
running the exact-artifact release helper. npm CLI and native-app release
versions are independent; this is not a new App Store or native binary release.

## Published artifact

Published successfully on 2026-09-09 with npm provenance:
[release workflow](https://github.com/lachlanchen/LazyTunnel/actions/runs/34332460875).
Source commit: `f0bed1a49b407daca04952d78cd270e4ebc41508`.
The registry tarball has 37 files and is 73,663 bytes compressed.

```text
sha512-6T3YlsAhOm/AH5UIlU0WYk8A9kFmciVT+QgukqiK8nnbU1rTG1r2wcV+foZXW30ItrbBf/8KdjPUueVARui46Q==
```

All published members and modes matched the committed source; a canonical pack
using Git file modes reproduced the exact tarball. A first pack of the private
worktree differed only because its files had owner-only permissions. Compare
member contents and canonical modes before treating a local archive mismatch
as a source discrepancy; do not relax permissions on private workstation files.

The public package was installed on the operator's Linux client. Account help
and version checks passed, and client code updated without changing enrollment,
keys or carrier configuration. Existing agent/browser/XRDP process IDs stayed
unchanged. The older `lazytunnel` launcher remains preserved on PATH; use the
unambiguous `lazytunnel-client` and `lazytunnel-server` npm commands there.
