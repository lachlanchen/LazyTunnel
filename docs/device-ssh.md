# Consistent SSH names across personal devices

Use normal SSH, SCP and SFTP with a managed set of `device-*` host names.
Keep addresses, user names, public-key inventory and generated bundles in a
private directory outside Git. Names do not create a VPN or route a whole
LAN: each peer uses a verified direct address or an explicit SSH jump path.

## Keys and routes

1. Generate an endpoint login key **on each device**. Never copy private keys.
2. Generate a separate jump key on each device that needs the relay.
3. Collect public host keys through an already authenticated connection or a
   trusted console. Pin them with `HostKeyAlias` in `devices_known_hosts`.
4. Add each approved endpoint public key to the intended peer user accounts.
   This grants shell access as those users; deliberately choose the trust
   group rather than enrolling every machine discovered on a network.
5. Authorize jump public keys only on restricted hop accounts, with the
   existing exact `PermitOpen` ports. Do not grant them tunnel ownership,
   a shell, public forwarding, agent forwarding or unrestricted targets.
6. Route hosts on each LAN directly when possible. Remote LAN-only peers can
   use the reachable workstation on that LAN as `ProxyJump`.

An existing LazyTunnel deployment can supply the two private reverse
listeners. No new network service, desktop process, default route, firewall
policy or public RDP/VNC port is required for these aliases.

## Prepare an endpoint

POSIX (Linux or macOS):

```bash
python3 scripts/device-ssh-endpoint.py prepare alpha
```

Windows, in PowerShell:

```powershell
powershell -NoProfile -File scripts/device-ssh-endpoint.ps1 -Prepare -Name alpha
```

The response contains only public keys, host identity and home-directory
metadata. Private keys stay in `~/.ssh/id_ed25519_devices` and
`~/.ssh/id_ed25519_devices_hop`. Existing keys are reused; a public key
without its private counterpart causes a refusal instead of replacement.

## Review and install a bundle

The private JSON bundle has exactly the material the endpoint will install:

```json
{
  "authorized_keys": ["ssh-ed25519 REVIEWED_PEER_PUBLIC_KEY"],
  "known_hosts": "device-beta ssh-ed25519 VERIFIED_HOST_PUBLIC_KEY\n",
  "config": "# Managed device SSH peers\nHost device-beta\n    HostName REVIEWED_ADDRESS\n    User REVIEWED_USER\n    HostKeyAlias device-beta\n    IdentityFile ~/.ssh/id_ed25519_devices\n    IdentitiesOnly yes\n    StrictHostKeyChecking yes\n    UserKnownHostsFile ~/.ssh/devices_known_hosts\n    ForwardAgent no\nHost *\n"
}
```

The placeholders are intentionally not valid keys or addresses. Render real
values from the verified private inventory. Add separate exact hop stanzas
using the `_hop` identity; do not reuse the endpoint key for relay access.
Use `ProxyJump device-alpha` for a peer behind alpha. The final server must
still authenticate the originating device's key; no private key or agent
needs to be forwarded through alpha.

```bash
python3 scripts/device-ssh-endpoint.py install < /private/reviewed-bundle.json
```

```powershell
powershell -NoProfile -File scripts/device-ssh-endpoint.ps1 -Bundle C:\private\reviewed-bundle.json
```

Installation adds `Include ~/.ssh/devices.conf` at the beginning of the
existing SSH configuration, then restores `Host *` context. It preserves
unrelated aliases and authorization lines. Restricted occurrences of an
already present key are **not** duplicated as unrestricted keys. Changed
files get content-addressed copies in `~/.ssh/device-ssh-backups`.

On standard Windows OpenSSH installations, administrator users use
`C:\ProgramData\ssh\administrators_authorized_keys`. The helper preserves
an existing file and its ACL; it refuses to create that privileged file
without a separate ACL review. This is the Windows administrator-group
authorization boundary, not an isolated per-user key file.

Review effective settings with `ssh -G device-beta` after installation.
Client configuration is read for every new SSH invocation; Bash aliases
and shell startup reloads are not required for normal `ssh device-beta`.
Existing SSH sessions keep their current configuration. No SSH daemon
restart is needed merely to append authorized public keys.

### Windows SSH service / nested-client compatibility

One tested Windows OpenSSH 9.5 client hung before configuration diagnostics
when started inside an SSH-served session, even with `-F NUL`. That does
not establish a universal Windows bug or prove that its interactive desktop
client is broken. Git for Windows' existing OpenSSH client worked, but its
implicit jump command initially ran through a Windows text shell and corrupted
the binary SSH banner. Running the complete command through Git Bash with
`SHELL=/bin/bash` fixed the tested nested connection.

For that situation, install `device-ssh-dispatch.sh` and
`device-ssh-shell.ps1` together in the Windows user's `.ssh` directory, then
add this line to the user's PowerShell profile:

```powershell
. "$HOME\.ssh\device-ssh-shell.ps1"
```

Open a new PowerShell terminal, or run that line in an existing one. The
helper routes only `device-*` SSH/SCP/SFTP arguments through the already
installed Git for Windows tools. Other hosts keep Windows OpenSSH. Existing
user functions/aliases are not replaced; the explicit `ssh-device` helper
remains available in that case:

```powershell
ssh device-beta
ssh-device beta hostname
scp .\small-test.txt device-beta:/tmp/
```

Do not globally replace Windows OpenSSH, disable host-key checking, pipe an
SSH transport through `Out-String`, or run a binary proxy stream through a
text-encoding shell. No SSH server restart, machine-wide PATH change, or
desktop logout is required for this helper. Remove the profile source line
and reopen the terminal to stop using it.

## Acceptance and rollback

Test every desired direction, not only connections from the deployment host:

```bash
ssh device-beta hostname
ssh device-beta 'ssh device-alpha hostname'
scp small-test.txt device-beta:/tmp/
```

Use a small disposable file and compare its checksum after a round trip.
Check that restricted jump accounts reject shell execution and forwarding
to ports outside their allowed list. Verify idempotent reinstallation and
ensure existing desktop processes/tunnels are unaffected. Host names alone
do not prove file transfer, reconnect behavior or reboot persistence.

For a changed route, edit only its managed stanza and revalidate. For full
rollback, restore the recorded configuration/authorization backups **after
checking for newer unrelated edits**. For revocation, remove the specific
device's endpoint public key from every enrolled account and its jump key
from the hop accounts. Leave other keys and existing tunnel services intact.

Offline machines cannot be enrolled or verified until reachable. A stock
phone can act as an SSH client using an appropriate app; this does not turn
it into an always-running SSH server. Import only its public key through a
trusted path when adding it to the trust group.
