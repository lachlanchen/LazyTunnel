# Verify the shell, not just the device status

An authenticated hostname command proves more than an online indicator or a
listening relay port. Check every directed pair, including both directions
between Windows, macOS and Linux, using each source's own endpoint key and the
destination's pinned host key. Record failed attempts as well as successful
rechecks. Limit concurrency on small shared relays.

On 3 October 2026, an eight-device fleet produced correct endpoint hostnames
on all 64 directed routes, including eight self routes. The initial result was
58/64. Six Windows-source routes timed out at ten seconds and passed at thirty
seconds; command completion took about 16–27 seconds. This is a point-in-time
check, not proof of interruption-free service. Some other connection attempts
also encountered transient network timeouts. No firewall block or daemon
failure was established for those transient failures.

## Give slow session establishment a bounded deadline

An optional administrator-managed peer field, `"connect_timeout": 30`, changes
the deadline for that device's outgoing hop, registry, and endpoint connections.
The allowed range is 5–60 seconds; the default remains ten. It leaves the
carrier configuration byte-for-byte unchanged, so clients can obtain the
setting through ordinary `lazytunnel sync` without restarting live carriers.

Use the existing wrappers on Windows; they retain the Git OpenSSH backend
needed for reliable nested-proxy shutdown. A longer deadline does not repair
packet loss, promise faster connections, or remove a relay's bandwidth limit.

## One macOS launchd owner per carrier

A Mac had a working GUI-domain carrier and a system-domain job retrying the
same listener every twenty seconds. Its log repeatedly reported
`remote port forwarding failed`. An enabled system job was therefore not
evidence of an additional healthy connection.

Inspect all domains before changing jobs:

```sh
launchctl print gui/$(id -u)/art.lazying.lazytunnel-fleet
launchctl print user/$(id -u)/art.lazying.lazytunnel-fleet
launchctl print system/art.lazying.lazytunnel-fleet
tail -20 ~/.config/lazytunnel-fleet/carrier.log
```

In this instance the failed system job was unloaded while the exact working
GUI carrier PID remained unchanged. The system LaunchDaemon plist was retained
and there was no separate user LaunchAgent file. The system job can load alone
at the next boot. This was not a reboot test. Do not blindly unload the system
job on another Mac: first identify which connection actually owns its listener.

`lazytunnel boot` now detects legacy GUI/user jobs before bootstrapping a
system carrier. It refuses an existing duplicate and otherwise preserves a
legacy job while preparing system activation for the next boot. Separately
configured user autostart still requires an operator review before that boot.

## UU Terminal is a separate transport

The optional UU bridge shell shortcuts can explicitly reuse these verified
SSH routes:

```sh
uu-shell --lazy lab
uu-shell --lazy lab hostname
uu-shell --native lab
```

An explicitly configured fleet profile can also make `uu-shell lab` select
LazyTunnel. The helper identifies the selected transport. It never silently
replaces a failed native UU terminal with cloud SSH. See the
[UU shell guide](https://github.com/lachlanchen/uu-remote-ubuntu-bridge/blob/main/docs/fleet-shell.md)
for installation and the remaining native vendor compatibility limits.
