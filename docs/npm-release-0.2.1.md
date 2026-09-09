# npm 0.2.1 acceptance record — 2026-09-09

Published package: [@lazyingart/lazytunnel](https://www.npmjs.com/package/@lazyingart/lazytunnel).
Stable source: `00625042a86e1d311dbeb49eb95fa83fecea0694`, tag `npm-v0.2.1`.
[Successful GitHub release run](https://github.com/lachlanchen/LazyTunnel/actions/runs/34326058954).

The owner-authenticated bootstrap version `0.2.1-bootstrap.0` established the
package. A trusted publisher was then configured for `lachlanchen/LazyTunnel`,
`npm-publish.yml`, with no environment. Stable 0.2.1 was published through that
GitHub OIDC workflow with provenance; no npm credential was added to GitHub.
The first workflow attempt ran before trust was accepted and correctly failed
publication; after the trust fix, the same source completed successfully.

## Verified

- 9 Node wrapper/installation tests and 69 Python core tests passed in CI.
- Package allowlist: 32 files, no npm runtime dependencies, no install hooks.
- Public tarball: 59,868 bytes; SHA-512 verified against registry metadata.
- Linux temporary-prefix tarball install: all CLI versions, prerequisite doctor
  and non-root server-install preview passed.
- Windows temporary-prefix install: Node 22.20.0, PowerShell/OpenSSH doctor,
  existing device inventory and real cross-machine SSH command passed.
- Linux public-registry global installation: version, doctor, persistent client
  code install and real SSH to a second Ubuntu machine passed. Existing agent,
  browser console, UU and XRDP PIDs were retained.
- Local static website preview served the npm installation FAQ successfully.

```text
sha512-gchlvRDyhGqL6qdK15uopQN8r+tYgmUXLc3H1si+Jyp5UiGC6Ii7UopSXUHfyMlbRzjELwwYBaQWXJsgw56V+w==
```

No fleet-wide npm migration, relay-policy change, desktop restart, or reboot was
needed. Windows/macOS are fleet clients; the independent controller service and
relay server remain Linux features. The native preview version remains 0.2.0.

## Publishing lessons

The existing LazyNPM browser/CDP and registered key were reused. A stale saved
WebAuthn assertion counter caused generic npm authentication failures. Chrome's
non-resident credential results can omit `rpId`; the helper must merge them by
an unambiguous existing credential ID and save the actual counter while retaining
the RP and key. It must not drop that update or decrease a saved counter.

Use npm 11.19.1 for current trust administration with `--allow-publish`; npm
11.10's old trust request returned HTTP 400. Release publishing itself succeeded
with the workflow's pinned npm 11.10.0. Run auth checks from the package directory:
a project `.npmrc` in the home directory may override an explicit user config.

All credentials, authentication URLs and browser state stay outside this repo.
See [npm installation and release commands](npm.md).
