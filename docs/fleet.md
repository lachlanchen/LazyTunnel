# Fleet server and clients

LazyTunnel connects enrolled Linux, macOS and Windows computers through an
ordinary cloud SSH server. It does not depend on a UU desktop takeover, a
Windows neighbor, a VPN, or a particular LAN address. A client can move networks
and reconnect using its existing identity.

CLI version 0.3.0 adds [independent accounts on one relay](accounts.md), with
key/password login, invitations and owner-only enrollment/revocation. Version-2
manifests scope the fleet below to the device's account. Version-1 fleets keep
their existing shared trust until an explicit operator upgrade.

## Components and boundaries

```text
client A ── outbound carrier ── cloud loopback SSH port
client B ── restricted cloud jump ── A's SSH server

client B browser ── B's loopback web port ── encrypted SSH ── A's existing noVNC
```

The server has three narrowly scoped identities per newly enrolled computer:

| Account role | Capability |
| --- | --- |
| `lf-tun-NAME` | Own one exact loopback reverse listener; no shell or forward to arbitrary ports |
| `lf-hop-NAME` | Connect only to the declared fleet SSH listeners; no shell or reverse listeners |
| `lf-info-NAME` | Read that device's configuration bundle through a fixed `cat` command; no forwarding or arbitrary commands |

Endpoint login uses a separate key and the destination's own SSH server. The
registry uses the enrolled jump identity to read public routing/configuration
data. It never distributes an administrator private key or endpoint private key.
New accounts use the separate `lf-*` namespace. Existing `lt-*` carriers and
their additional approved device-mesh keys are preserved. An `external_carrier`
entry explicitly reuses a reviewed existing listener instead of competing for it.

## Code and private state are separate

| Component | Code | Private identity/configuration |
| --- | --- | --- |
| Cloud | `/usr/local/lib/lazytunnel/server/releases/` and `current` | `/var/lib/lazytunnel-fleet/`, `/etc/lazytunnel-fleet/` |
| Linux/macOS client | `~/.local/share/lazytunnel/client/releases/` and `current` | `~/.config/lazytunnel-fleet/` |
| Windows client | `%USERPROFILE%\.local\share\lazytunnel\client\code` | `%USERPROFILE%\.config\lazytunnel-fleet` |

Git contains code, synthetic examples, tests and sanitized documentation only.
Real enrollment packets, bundles, host inventories, passwords, administrator
credentials and keys belong outside the checkout. Unknown credential fields
in fleet manifests are rejected. Each device creates its own private keys.

Updating code does not regenerate keys, log out UU, restart a desktop, or
replace a healthy carrier. `sync` obtains the latest reviewed configuration
from the pinned cloud registry. Carrier identity/port migrations are refused
until an operator explicitly coordinates them. Registry expansion is additive;
removing a device is a separate [revocation operation](accounts.md#4-revoke-a-device-or-disable-an-account).

## Install a client

Linux/macOS require Python 3 and OpenSSH. Windows uses PowerShell and OpenSSH;
no Python installation or container is needed there. Use a reviewed checkout.

```bash
python3 scripts/lazytunnel-client.py install
export PATH="$HOME/.local/bin:$PATH"
lazytunnel prepare --name alpha > /private/path/alpha-enrollment.json
```

The installer also adds the commands directory to subsequent Bash and zsh
sessions. It does not inject commands into existing terminals.

Windows PowerShell, from the repository:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\lazytunnel.ps1 install
& "$env:USERPROFILE\.local\bin\lazytunnel.cmd" prepare -Name alpha -Output "$env:USERPROFILE\alpha-enrollment.json"
```

The enrollment packet contains **public** identities and destination metadata.
Transfer it through an already authenticated channel to the cloud administrator.
Do not send the `*_ed25519` private files. A UU account/device list is discovery
information, not automatic authorization to grant shell access to an unknown
computer. Identify the OS/user and verify its host key first.

## Install/update the server

From a reviewed checkout on the cloud:

```bash
sudo python3 scripts/lazytunnel-server.py install --apply
sudo lazytunnel-server apply --manifest /private/path/fleet.json
sudo lazytunnel-server apply --manifest /private/path/fleet.json --apply
sudo lazytunnel-server status
```

A fleet manifest contains `version: 1`, the edge's public `host`, `port` and
`host_key`, and a `peers` array. For the first peer, use its prepared packet and
add a unique `relay_port`, optional `aliases`, and `external_carrier: false`.
Each peer must have `platform` (`linux`, `darwin`, or `windows`). The legacy
two-peer example documents the other identity fields. Do not put credentials
inside this file. Have the operator verify the cloud host key out of band.

For subsequent devices:

```bash
sudo lazytunnel-server enroll --packet /private/path/alpha-enrollment.json --port 23008
sudo lazytunnel-server enroll --packet /private/path/alpha-enrollment.json --port 23008 --apply
sudo lazytunnel-server export --name alpha --output /private/path/alpha-bundle.json
```

The server validates ownership, unique identities/ports and `sshd -t`, saves
rollback data, and reloads SSH policy. It never replaces the firewall or public
SSH port configuration. Existing clients can now run `lazytunnel sync` to learn
the new destination and authorize its endpoint-login key.

## Login means device enrollment

This release uses an administrator-approved enrollment bundle or an
[account invitation](accounts.md), without a public web signup service.
For the manual bundle workflow, after the public
packet is accepted, deliver the private bundle to its own device through the
existing trusted channel. The client verifies that the bundle matches its
user, host key and locally held private identities.

```bash
lazytunnel login --bundle /private/path/alpha-bundle.json
lazytunnel boot
lazytunnel status
lazytunnel devices
lazytunnel sync
```

Windows:

```powershell
lazytunnel login -Bundle "$env:USERPROFILE\alpha-bundle.json"
lazytunnel boot
lazytunnel status
lazytunnel devices
lazytunnel sync
```

`boot` may need the local administrator for a first Linux linger setting or
macOS LaunchDaemon installation. It never reboots the computer. Linux uses
user systemd plus lingering, macOS uses a LaunchDaemon running as the endpoint
user, and Windows uses an S4U scheduled task without a stored user password.
FileVault/BitLocker unlock, firmware boot selection and a powered-off computer
remain outside the tunnel's control.

Windows Task Scheduler requires a valid restart interval; a 30-second interval
was rejected during validation. The installer uses one-minute failure recovery
and an indefinite five-minute scheduler trigger with `IgnoreNew`. This retries
after prolonged outages while retaining one active carrier. See Microsoft's
[trigger documentation](https://learn.microsoft.com/en-us/powershell/module/scheduledtasks/new-scheduledtasktrigger).

## Daily SSH and file transfers

The same aliases are installed on every enrolled device:

```bash
ssh-lazy-alpha
ssh-lazy-beta hostname
ssh-lazy beta
ssh lazy-beta
scp-lazy ./example.txt lazy-beta:Downloads/
```

Linux/macOS also support `lazytunnel ssh beta hostname`; Windows supports
`lazytunnel ssh -Device beta hostname`. These are normal SSH connections:
destination permissions and application authentication still apply. For a long
job, use tmux on the destination. A reconnect restores connectivity, not a
shell already lost during an outage.

### Windows proxy shutdown issue

In the live deployment Microsoft's OpenSSH could run `hostname` successfully
but hang while closing a nested proxy when output was captured. `-n` did not
fix shutdown. The same command completed correctly using Git's OpenSSH.

The new `ssh-lazy-*`, `scp-lazy` and client SSH/web commands therefore select
an existing Git for Windows Bash/SSH backend when present. Native Windows sshd
and the healthy outbound carrier remain unchanged. Generic system `ssh` and
unrelated SSH aliases are not replaced.

For a minimal Windows VM without Git, an operator can reuse only the SSH/Bash
runtime and its recursively discovered DLL dependencies from an already trusted
Git installation. In the tested installation this was 23 files, about 16.4 MiB.
Run on a POSIX operator host with `objdump` and authenticated SSH aliases:

```bash
python3 scripts/copy-git-ssh-runtime.py --source windows-with-git --destination small-windows-vm
```

The helper verifies destination SHA-256 hashes, skips matching installed files,
and copies no credentials. Keep applicable Git/MSYS/Bash/OpenSSH license notices
with a redistributed runtime; do not commit binaries or private runtime caches.
Then update the client code and run `lazytunnel sync` on that Windows device.

## Independent code updates

After fetching and reviewing a newer checkout:

```bash
lazytunnel update --source /path/to/LazyTunnel
sudo lazytunnel-server update --source /path/to/LazyTunnel --apply
```

Run the server command on the cloud only. Windows uses
`lazytunnel update -Source C:\path\to\LazyTunnel\scripts`.
Run `lazytunnel sync` separately when the server's device configuration changed.
Code updates do not assume permission to rotate or erase credentials. There is
no automatic Git updater or tight background polling loop.

## noVNC, WeChat, WeCom and existing desktops

An [optional private browser console](gui.md) provides device cards,
on-demand SSH checks and saved viewer controls. It runs separately on an
enrolled client; it does not add a public management service to the cloud.

Any enrolled endpoint can forward an existing HTTP/WebSocket noVNC service:

```bash
lazytunnel web alpha 6144 --local-port 16144 --path /wecom
```

Windows:

```powershell
lazytunnel web -Device alpha -Port 6144 -LocalPort 16144 -Path /wecom
```

Keep that terminal open and browse `http://127.0.0.1:16144/wecom` **on the
client running the forward**. The same port can serve `/wechat`, `/wecom`, or
other paths offered by the original app. If a VM viewer is served by its Linux
host, select the **host's** alias, not the guest's alias. A conflicting local
port is refused instead of taking over another application's listener.

An existing persistent `lazy-web` service can be reused. See
[private-web.md](private-web.md) for persistent Linux forwards and remote LAN
targets. SSH transport carries WebSockets transparently; it does not remove
the viewer's authentication, same-origin checks, or input-control lease.
A raw WebSocket test without the browser's `Origin` header may correctly fail.

This feature forwards an existing desktop/viewer; it does not create another
GNOME session. To share a computer's own desktop, select its already configured
shared-session VNC/noVNC service. Do not launch a second desktop or restart RDP
merely to create a tunnel. Cloud bandwidth limits desktop video throughput;
SSH command latency and GUI frame rate are different measurements.

## Acceptance, limitations and rollback

The September 2026 live deployment enrolled seven devices across Linux, macOS
and Windows and passed all 49 directed hostname checks, including self-routes.
The old two-peer carriers retained their running processes through expansion.
Per-host file-transfer, registry refresh, noVNC and boot-enablement evidence
belongs in the operator's private report. Boot settings were inspected without
rebooting user computers; this is not a claim of a completed reboot test.

One UU device was online but failed terminal initialization from both Linux/Wine
and a native Windows controller. Other listed devices were offline. They remain
pending enrollment; aliases must not imply they were installed or reachable.
An intermittent direct cloud TCP timeout occurred during deployment. The cloud
was reachable through an independent administrator path and had no matching
local firewall ban; direct access later recovered. Its network root cause was
not proven and no global route or desktop setting was changed for it.

For rollback, stop only the named fleet carrier/task on the affected endpoint,
retain its keys, and restore the reviewed private backup. Server revisions save
the previous owned policy and public authorization material. Preserve the old
`lt-*` carrier, normal SSH server, UU/RDP/VNC and administrator route. Removing
a client from the fleet requires revoking both its cloud authorization and its
endpoint-login keys on other peers; hiding its alias is not revocation.
