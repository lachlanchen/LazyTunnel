# Deployment and rollback

These tools are an early, operator-reviewed implementation, not an unattended
cloud provisioner. They do not buy a server, alter security groups, log in to
a provider, create a public desktop endpoint, or change a workstation's routes.

## 1. Bootstrap cloud administration separately

Use the provider console only if necessary to establish native SSH. Verify the
cloud host fingerprint through that authenticated console before trusting an
Internet key scan. Keep the current administrator/recovery path until a second
key-based session and sudo have passed.

On a freshly installed Ubuntu image, `ssh.socket` can be active while
`ssh.service` is inactive. Starting a second sshd directly can fail because
`/run/sshd` does not exist yet. Starting the native SSH service creates its
runtime directory. A temporary separately named sshd can then bootstrap an
alternate port when outbound port 22 is filtered. Inspect actual errors first.

`scripts/bootstrap-admin.py` is an explicit root-only bootstrap helper. It
reads JSON on stdin containing `username`, `public_key`, and a generated strong
`password`; do not put that JSON in shell arguments or Git. It creates a new
unprivileged user, adds sudo membership, installs the key, and preserves an
existing account password. Verify the resulting key and password-protected
sudo before disabling SSH password login.

`scripts/activate-ssh-ports.sh` is a **specific fresh-Ubuntu recovery script**,
not a general installer. It expects a reviewed, newly added
`/etc/ssh/sshd_config.d/00-lazytunnel-listen.conf` with no predecessor, an
independent transient unit called `lazytunnel-bootstrap.service`, and a free
rollback pathname. It validates sshd, checks that socket generation includes
2222, stops only the temporary listener, and restarts native listener units.
Run it detached from the temporary SSH process. Never use it on an existing
shared server without reviewing and adapting those preconditions.

## 2. Enroll each endpoint

Run as the normal login user, not root. Read the helper first.

```bash
python3 scripts/enroll.py --name alpha --relay-port 23001 --output /secure/alpha.json
```

Use `beta` and another port for the other endpoint. The packet contains public
keys and private topology, not private keys. Transfer it through a trusted
channel. Keys are generated only if absent and stay in `~/.config/lazytunnel`.
Verify host fingerprints independently; a matching JSON shape is not identity
verification. The enrollment helper makes no service or SSH-policy changes.

## 3. Build and inspect the manifest

Merge the approved endpoint objects into `peers`, and supply the reviewed
cloud host, alternate SSH port and Ed25519 host public key under `edge`.
`examples/two-peers.json` uses synthetic test keys and an invalid hostname;
it is for validation/rendering only and **cannot establish a connection**.

```bash
python3 lazytunnel.py validate --config /secure/relay.json
python3 lazytunnel.py plan --config /secure/relay.json
python3 lazytunnel.py render --config /secure/relay.json --role edge --output /secure/edge-candidate
python3 lazytunnel.py render --config /secure/relay.json --role worker --peer alpha --output /secure/alpha-candidate
```

Rendering refuses existing output directories. It does not overwrite live
configuration. Inspect every generated file; hash the exact repository release
and manifest, and retain them in a private change record.

## 4. Install the restricted cloud policy

Transfer the reviewed source and manifest to an owner-only staging directory,
without passwords, browser state, or worker private keys. On the cloud:

```bash
sudo python3 scripts/install-edge.py --config /secure/relay.json
sudo python3 scripts/install-edge.py --config /secure/relay.json --apply
```

The plan is non-mutating. Apply creates dedicated `lt-tun-*` and `lt-hop-*`
accounts without usable passwords or shell sessions, validates sshd, and reloads
only native SSH. It does not change ports or firewall rules. Existing accounts
or policy files without a matching ownership record are refused; membership
changes require a deliberate migration. Run only one installer at a time.

Public authorized-key files are root-owned **0644**, with **0755** parent
directories, because sshd reads them as the destination identity. Making these
particular public files root-only prevents authentication; private identity
keys must remain owner-only. `AllowStreamLocalForwarding no` prevents bypassing
TCP listener restrictions with Unix-socket forwarding.

The saved revision under `/var/lib/lazytunnel/revisions/` contains the previous
managed files and a rollback map. A validation/reload failure restores the
previous files; newly created account records may remain without an authorized
key. Do not delete accounts automatically. Restoration of an accepted revision
requires reviewing the saved map, restoring those exact files, `sshd -t`, and
reloading SSH. Keep an independent administrator session throughout.

## 5. Install one worker per endpoint

The destination agent verifies its local keys and the signed/trusted handoff,
then runs as the normal user:

```bash
python3 scripts/install-worker.py --config /secure/relay.json --peer alpha
python3 scripts/install-worker.py --config /secure/relay.json --peer alpha --apply --start
systemctl --user status lazytunnel.service
ssh -F "$HOME/.config/lazytunnel/ssh_config" beta
```

The installer preserves existing authorized keys, adds only the other peers'
login keys, and creates one user unit. It refuses to overwrite unowned config or
change the configuration of an active carrier. A matching rerun does not
restart a healthy carrier. User lingering is reported, never silently enabled;
an administrator can approve `loginctl enable-linger USER` for boot/logout
persistence. Enabled units are not evidence of a tested reboot.

If acceptance fails, stop only `lazytunnel.service` and restore the exact saved
`worker-before-*/rollback.json` files after reviewing concurrent edits. No
desktop server should be restarted. The earlier UU aliases remain usable by
their original transport whenever that transport is available.

## 6. Acceptance

- Verify both cloud reverse listeners are exactly `127.0.0.1`, not wildcard.
- Verify native shell commands, return codes and UTF-8 in both directions.
- Compare a small random file checksum after scp/sftp round trips.
- Prove a transport key cannot run a shell or open an undeclared forward.
- Stop/restart only a newly owned carrier in an agreed test window; confirm
  future access recovers. Existing SSH sessions do not survive carrier loss.
- Keep remote tmux for long work; verify UU/RDP/VNC takeover does not own this
  carrier. Check boot enablement and distinguish it from an actual reboot test.

This does not guarantee Internet/cloud availability or increase the purchased
bandwidth. A 2 Mbps relay is fine for light shell use but limits bulk transfer.
