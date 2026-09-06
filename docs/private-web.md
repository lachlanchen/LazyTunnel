# Private web and LAN access over LazyTunnel

Use the existing end-to-end SSH connection to open a peer's web services.
No new cloud port, public proxy, VPN, desktop takeover or default-route change
is needed. The same mechanism carries ordinary TCP, HTTP, HTTPS and WebSocket
connections. Existing application authentication remains in effect.

## What localhost means

`127.0.0.1` normally refers to the computer running the browser. Opening
`http://127.0.0.1:6144/wechat` on beta cannot reach alpha until beta has a
forward for that port:

```text
beta browser → beta 127.0.0.1:6144
             → authenticated SSH through LazyTunnel
             → alpha 127.0.0.1:6144 → /wechat
```

The cloud still exposes only SSH. Its restricted jump identity reaches the
peer's SSH listener, and the separately authenticated endpoint opens the web
connection. Do not relax the cloud's PermitOpen/PermitListen restrictions.
This provides selected private TCP access; it does not make the computers a
broadcast LAN or route ping/UDP traffic.

## Install once on each endpoint

From a checked-out LazyTunnel repository:

```bash
install -D -m 0755 scripts/lazy-web "$HOME/.local/bin/lazy-web"
lazy-web --help
```

The helper uses standard-library Python, OpenSSH and user systemd. It reads
the existing `~/.config/lazytunnel/ssh_config`; it does not generate new keys
or alter the carrier. Use actual peer names listed in that config. An optional
`--ssh-config PATH` selects another already trusted configuration.

## Open one service

On beta, open alpha's port 6144:

```bash
lazy-web run alpha 6144
```

Keep the terminal open and browse `http://127.0.0.1:6144/wechat` **on beta**.
Ctrl+C stops only this forward. To keep a conflicting local port free:

```bash
lazy-web run alpha 6144 --local-port 16144
```

Then use `http://127.0.0.1:16144/wechat`. The helper refuses an occupied port;
it never kills its owner or silently picks another destination. Keep the
original application path and scheme. An application using absolute links,
an additional API port, or strict HTTPS hostnames may need matching forwards
or its own supported base-URL settings; TCP forwarding does not rewrite HTML
or bypass TLS certificate validation.

## Keep a forward after closing terminals and after boot

```bash
lazy-web start alpha-wechat alpha 6144
lazy-web status alpha-wechat
lazy-web status
lazy-web stop alpha-wechat
```

`start` writes and enables `lazytunnel-web-alpha-wechat.service`. Repeating
the exact same command preserves its running SSH PID. A name with different
settings is refused: choose another name, or deliberately review/edit the
saved unit after stopping it. `stop` disables and stops only that owned
forward, retaining its unit for a later matching `start`.

The service runs SSH directly; it does not depend on the project filesystem
remaining mounted. It retries after 15 seconds when SSH exits, checks pinned
host keys, and never starts a shell or forwards an authentication agent. A
reconnection restores new requests; existing HTTP/WebSocket requests can
still fail during an outage and may need a browser refresh. `active` alone
is not an end-to-end health result: verify the actual URL.

For startup before graphical login, inspect the existing login-user policy:

```bash
loginctl show-user "$USER" -p Linger
```

If lingering is not enabled, an administrator can enable it with
`sudo loginctl enable-linger "$USER"`. The helper does not silently change
that policy. Both underlying LazyTunnel carriers, endpoint SSH servers and
the original app must also be available. Enabled units are not a reboot test.

## Access a device on the peer's LAN

The target is resolved/reached **from the remote peer**, which avoids clashes
when both computers' routers use the same private address:

```bash
# Beta opens the router reachable from alpha, without configuring that router.
lazy-web run alpha 80 --host 192.168.1.1 --local-port 18080
```

Browse `http://127.0.0.1:18080` on beta. The same `--host` option works with
`start` and supports IPv4, IPv6 and hostnames. The local listener deliberately
stays on `127.0.0.1`; it is not exposed to everyone on beta's LAN. For the
opposite direction, run the same command on alpha with beta's peer name.

## General application proxy

For many remote targets, use an opt-in SOCKS5 proxy:

```bash
lazy-web socks alpha --local-port 1080
curl --noproxy '' --socks5-hostname 127.0.0.1:1080 http://127.0.0.1:6144/wechat
```

Only applications explicitly configured for that proxy use it. The target
`127.0.0.1` in this proxied request is alpha's loopback. Proxy-aware DNS
resolution also happens from alpha. Browsers may bypass localhost even with
a proxy configured, so a dedicated `run`/`start` forward is the simplest
choice for local development sites. No system-wide browser proxy is set.

## Diagnosis and undo

```bash
lazy-web run alpha 6144 --local-port 16144 --print-command
ssh -F "$HOME/.config/lazytunnel/ssh_config" alpha hostname
journalctl --user -u lazytunnel-web-alpha-wechat.service -n 40 --no-pager
ss -ltn 'sport = :6144'
curl --noproxy '*' --max-time 15 -I http://127.0.0.1:6144/wechat
lazy-web stop alpha-wechat
```

If SSH itself times out, repair that route first; changing app bindings or
restarting UU/RDP is not a web-forward fix. Preserve a healthy existing carrier
while diagnosing new-connection failures. If using HTTP probes, choose a
read-only page/health route rather than an endpoint that sends messages.

## Acceptance evidence (2026-09-07)

- A real loopback web page reached from the other endpoint returned HTTP 200,
  with identical 4,475-byte content and matching SHA-256 at both ends.
- Its viewer JavaScript also returned HTTP 200. A view-only WebSocket
  upgraded with HTTP 101 and received the remote framebuffer greeting;
  no input or control lease was requested.
- Matching `start` kept the same PID. Ending only the new forward's SSH
  process caused one supervised restart; the page returned HTTP 200 again.
- Reverse-direction HTTP and SOCKS5 tests returned the exact test marker
  from a temporary loopback server; both clients and that server were stopped.
- The retained forward binds only loopback. User lingering was already
  enabled; no reboot was performed and no desktop/carrier was restarted.
- Renderer/helper unit tests passed, including port conflicts, invalid names,
  IPv6 targets, unit escaping and unchanged restricted cloud policies.

Protocol reference: [OpenSSH ssh(1), local and dynamic forwarding](https://man.openbsd.org/ssh.1).
