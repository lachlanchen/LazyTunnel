# Independent SSH without taking over a desktop

Each workstation opens its own outbound SSH connection to a reachable cloud
server. Its SSH daemon is forwarded to a distinct **cloud loopback** port.
Clients reach the other endpoint through a restricted SSH jump account.

```text
workstation A ── outbound SSH ──┐
                               cloud: loopback reverse listeners only
workstation B ── outbound SSH ──┘

A ── authenticated SSH jump ── cloud:port-B ── end-to-end SSH ── B
B ── authenticated SSH jump ── cloud:port-A ── end-to-end SSH ── A
```

Only cloud SSH is public. A cloud jump is a byte transport: endpoint users
still authenticate against the destination SSH daemon and verify its host key.
The cloud must not receive endpoint private keys. Existing UU aliases remain
unchanged; separate aliases identify the independent route.

## What this fixes and what it does not

A UU desktop takeover can close a vendor-owned mapping. An independently
supervised OpenSSH transport is not owned by that desktop session, so taking
control via UU/RDP/VNC does not intentionally stop it. It still depends on
both computers, their Internet access and the cloud server being available.
Automatic reconnection restores future access, not a dead interactive shell;
use remote tmux for long-running work.

This borrows LazyEdge's simple reverse-SSH supervision and private-listener
boundaries. It does **not** modify or bypass LazyEdge's HTTP guards. No Caddy,
VPN, DNS takeover, desktop server, container or kernel routing change is needed
for this two-machine SSH use case.

## Accounts and permissions

- One tunnel identity per endpoint: remote forwarding only to its declared
  cloud loopback port; no sessions, TTY, agent forwarding or X11.
- One jump identity per client: local forwarding only to declared peer
  loopback ports; no shell/session or arbitrary cloud destinations.
- Endpoint login key: authorized by the destination OS user, kept on the
  originating endpoint, distinct from the transport keys.
- Administrator access remains independent of all restricted identities.

OpenSSH `PermitListen` restricts the cloud bind address, not the target selected
by a remote-forward client. The trusted worker configuration pins the target
to its own loopback SSH port. A compromised authorized worker can substitute
that target; end-to-end endpoint host-key verification remains mandatory.

## Recovery and evidence

Use systemd with a bounded restart delay, OpenSSH server-alive checks,
`ExitOnForwardFailure=yes` and strict key checking. Disable connection sharing
for supervised carriers so each unit has a single attributable process.
Cloud client-alive checks release stale listeners after lost connections.
Never kill an unknown listener just to make an intended port available.

Accept only after checking both native SSH directions, shell exit statuses,
UTF-8 output, file round trips, private listener addresses, denied shell and
wrong-forward attempts, and a controlled restart of only the new tunnel unit.
Explicitly record whether reboot recovery was tested or merely configured.

## Primary references

- [OpenSSH client configuration](https://man.openbsd.org/ssh_config)
- [OpenSSH server configuration](https://man.openbsd.org/sshd_config)
- [systemd network-online semantics](https://systemd.io/NETWORK_ONLINE/)
- [LazyEdge](https://github.com/lachlanchen/LazyEdge)
