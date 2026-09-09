# Install the server and client with npm

The package is **`@lazyingart/lazytunnel`**, the SSH fleet and controller behind
[LazyRemote](https://remote.lazying.art). One small package includes separate
server/client commands. It reuses the existing Python/OpenSSH and Windows
PowerShell implementations; Node is a launcher, not a second tunnel daemon.
The optional Flutter native app remains a separate download/build.

## Install

Use Node.js 22 or newer with npm. Linux/macOS clients also need Python 3.9+ and
OpenSSH. Windows uses its installed PowerShell and OpenSSH client. The relay
server requires Linux, Python 3.9+, OpenSSH Server and systemd. npm does not
silently install operating-system packages or require a container.

```bash
npm install -g @lazyingart/lazytunnel
lazytunnel --version
lazytunnel doctor
```

For a one-off command without a global installation:

```bash
npx --yes @lazyingart/lazytunnel --help
```

Installation has no lifecycle hooks and starts no services. A user-owned npm
prefix avoids needing `sudo` for a client installation. The runtime has no npm
dependencies. Only the explicit commands below write persistent code or enroll
a device; installing the package never changes SSH ports, firewall policy,
default routes, UU, RDP or VNC.

## Client: install, enroll, use

For personal use or a server with independent user accounts, start with
[one relay, separate accounts](accounts.md). CLI version 0.3.0 supports:

```bash
lazytunnel-client install
lazytunnel-client login --invite alice.json --name laptop --identity ~/.ssh/lazytunnel-account
lazytunnel-client account devices --identity ~/.ssh/lazytunnel-account
```

Omit `--identity` for an operator-enabled account password. The manual bundle
workflow below remains supported. Account mode is an explicit server upgrade;
updating npm does not migrate a running fleet.

```bash
lazytunnel-client install
lazytunnel-client prepare --name alpha > alpha-enrollment.json
```

`install` copies the packaged runtime into the existing versioned per-user code
directory. Credentials are separate in `$HOME/.config/lazytunnel-fleet`. The
public enrollment packet goes to your relay administrator through a trusted
channel. It does not contain private keys. The endpoint needs its own running
SSH server and a readable host public key to complete preparation.

After the administrator approves it and delivers its matching private bundle:

```bash
lazytunnel-client login --bundle /private/alpha-bundle.json
lazytunnel-client boot
lazytunnel-client devices
lazytunnel-client ssh beta hostname
lazytunnel-client web beta 6080 --local-port 16080
```

`lazytunnel <command>` and `lazytunnel client <command>` are equivalent client
entry points. `login` activates the reviewed enrollment; `boot` enables the
existing platform startup mechanism. They do not log in to a public account
service or take over a desktop. See [fleet enrollment and SSH](fleet.md).

On Windows, the common `--name`, `--bundle`, `--output`, `--local-port` and
`--path` flags are mapped to the existing PowerShell parameters. Native forms
such as `-Name`, `-Device`, `-Bundle` and `-Output` also work. To save a public
packet without Windows PowerShell's redirection encoding differences:

```powershell
lazytunnel-client install
lazytunnel-client prepare --name alpha --output "$env:USERPROFILE\alpha-enrollment.json"
lazytunnel-client login --bundle "$env:USERPROFILE\alpha-bundle.json"
lazytunnel-client ssh -Device beta hostname
```

## Server: install and administer on the relay

Install the same npm package on the Linux cloud server. Then:

```bash
lazytunnel-server install
sudo lazytunnel-server install --apply
sudo lazytunnel-server apply --manifest /private/fleet.json
sudo lazytunnel-server apply --manifest /private/fleet.json --apply
sudo lazytunnel-server status
```

The first command previews a code release. `install --apply` writes code only;
the separate manifest `apply --apply` changes the owned relay policy after
validation. A code install/update does not reload SSH or replace enrollment.
`lazytunnel server <command>` is an equivalent entry point. If a user-installed
npm command is outside sudo's PATH, invoke its verified absolute path and make
sure Node is available to that administrative environment.

For subsequent devices:

```bash
sudo lazytunnel-server enroll --packet /private/alpha-enrollment.json --port 23008
sudo lazytunnel-server enroll --packet /private/alpha-enrollment.json --port 23008 --apply
sudo lazytunnel-server export --name alpha --output /private/alpha-bundle.json
```

The initial manifest and administrator-reviewed enrollment process are unchanged;
see [server setup](fleet.md#installupdate-the-server). No private manifest,
endpoint key or cloud credential is included in the npm package.

## Optional controller and browser GUI

On an enrolled Linux client:

```bash
lazytunnel-client agent install
lazytunnel-client gui install
lazytunnel-client gui
```

Run client `install` first so those services reference the persistent runtime,
not an npm cache or temporary `npx` directory. The independent agent uses
loopback port 17766; the optional browser console uses 17765 and its existing
private access code. The native apps connect to that controller. Windows/macOS
clients can use the fleet without installing the Linux controller service.

## Update and coexist with an older checkout installation

```bash
npm install -g @lazyingart/lazytunnel@latest
lazytunnel-client update
```

On the cloud, run the code update separately:

```bash
sudo lazytunnel-server update --apply
```

Package updates and these code updates preserve identities and running SSH
carriers. `sync` is a separate command when fleet enrollment has changed.
An already running Python agent/browser must be restarted deliberately to load
new service code; installing npm does not restart it behind the operator's back.
Do not stop an unrelated desktop or tunnel just to update a GUI.

The npm launcher passes `--no-launcher` (PowerShell: `-NoLauncher`) to code
installation. This preserves npm's command links and existing shell profiles.
An older `$HOME/.local/bin/lazytunnel` or `/usr/local/bin/lazytunnel-server` may
still precede npm on PATH. Use `command -v lazytunnel` / `Get-Command lazytunnel`
to identify it. Use the new `lazytunnel-client` entry or `npx @lazyingart/lazytunnel`
to address the packaged code explicitly. If npm reports an existing command
collision, install into a separate prefix and invoke its bin path; do not use
`--force` to overwrite an unrelated command.

Direct Python/PowerShell installation from Git remains supported. Its ordinary
launcher creation is unchanged unless `--no-launcher` / `-NoLauncher` is used.
Removing the npm package removes npm-owned commands; it does not revoke a
device, erase private state or shut down independently installed services.

## Packaging and releases

The approach follows AgInTiFlow's thin CLI, explicit `files` allowlist, package
inspection and registry verification. The package excludes native SDKs/builds,
Apple signing material, browser profiles, caches and private fleet state.
The npm CLI version is separate from the current native-app preview version.

From a checkout:

```bash
npm install --package-lock-only --ignore-scripts
npm test
npm run test:core
npm run verify:package
```

See the release helper and GitHub workflow for authenticated publication.
The first package publish may need the owner's npm web/passkey confirmation;
after that, a matching GitHub trusted publisher can use OIDC without storing
an npm token in GitHub. Use the existing authorized browser/passkey where
available. Never copy a passkey, token, browser profile or approval URL into
source, documentation or a public log.

`npm run release:npm` requires a clean tree, runs tests/package inspection and
prepares the current version without publishing. `npm run release:npm --
--publish` additionally publishes the exact packed bytes and checks registry
integrity. An identical existing version succeeds without republishing; a
different existing version fails. A failed/uncertain upload is not blindly
retried. Run release preparation on a POSIX host with Python and Git available.

For tokenless CI, configure npm's trusted publisher for repository
`lachlanchen/LazyTunnel`, workflow `npm-publish.yml`, with no environment name.
The workflow uses npm 11.10.0, tests the core and package, then publishes with
provenance. Trigger it with an exact matching `npm-vX.Y.Z` tag or the manual
`version` input. The separate `npm-v` tag namespace avoids confusing a CLI
package update with a native-app build or Apple release. The LazyNPM toolkit
provides the shared private browser/CDP/passkey recovery path; no account
credentials or browser-specific authentication code is embedded in LazyTunnel.
