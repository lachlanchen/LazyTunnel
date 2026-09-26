# Enroll a new Mac without disturbing existing desktops

## Prerequisites

Enable Remote Login for the intended non-root user in macOS Sharing settings.
Verify the host fingerprint before installing a dedicated SSH public key. If
an agent offers too many identities, use `IdentitiesOnly yes` with the intended
`IdentityFile`; do not raise server authentication limits or disable host checks.

Run `python3 --version`, not just `command -v python3`. A new Mac may expose an
Apple developer-tools stub that cannot execute Python. Install Apple Command
Line Tools or a signed Python.org macOS package. Validate a downloaded package
with `pkgutil --check-signature` before installing it. The POSIX launcher now
retains the Python interpreter used for installation, including paths with spaces.
Do not remove that interpreter while its installed client still refers to it.

## Enrollment

Use the workflow in [fleet.md](fleet.md). Generate the three keys on the Mac,
send only its public enrollment packet to the relay administrator, assign an
unused loopback port, export its bundle, and activate it locally:

```sh
python3 scripts/lazytunnel-client.py install
~/.local/bin/lazytunnel prepare --name mac-mini
# Administrator reviews the public packet and returns the enrollment bundle.
~/.local/bin/lazytunnel login --bundle /private/path/mac-mini-bundle.json
~/.local/bin/lazytunnel boot
```

Run `lazytunnel sync` on existing devices. Use their installed
`ssh-lazy-mac-mini` wrappers for testing, especially on Windows: the wrapper may
use a reviewed Git OpenSSH runtime to avoid native nested-ProxyCommand issues.
Test both directions, not just a listening port or successful service activation.

macOS installs a system LaunchDaemon that runs as the endpoint user. Its native
SSH carrier starts independently of GUI login and reconnects with a 20-second
throttle. This does not bypass FileVault preboot unlock. An enabled daemon is
not proof of a successful reboot test.

## Diagnose resets before adding more machinery

Check the active interface and the actual carrier socket. Two addresses from
Ethernet/Wi-Fi are not two different host identities. An inactive interface can
also leave a stale mDNS result. Keep a verified alternate LAN connection while
diagnosing the Internet route.

```sh
networksetup -listnetworkserviceorder
route -n get default
lsof -nP -a -c ssh -iTCP
tail -40 ~/.config/lazytunnel-fleet/carrier.log
launchctl print system/art.lazying.lazytunnel-fleet
```

The optional administrator-managed peer field `"ip_qos": "none"` disables SSH
DSCP marking for that device's carrier, hop, registry and outgoing endpoint
connections. `"cs0"` is also accepted. Absent the field, output is unchanged.
This is a targeted transport workaround, not a universal fix and not a change
to authentication, cipher choices, remote commands or SSH server permissions.
OpenSSH's [release notes](https://www.openssh.com/releasenotes.html) document
recent IPQoS defaults; routers/providers may treat marked traffic differently.

Apply a changed carrier configuration only during an explicit maintenance stop
of that one carrier, retaining independent LAN/admin access and a backup of the
old file. The client intentionally refuses to overwrite a changed live carrier.
Do not remove that check to make an update pass. Update the registry too, so a
later `sync` retains the fix. Do not change unrelated legacy carriers.

Do not mistake dark wake for full availability. A new desktop Mac was observed
cycling through `Maintenance Sleep` and `DarkWake from Deep Idle` even after
setting its idle sleep timer to zero. Short LAN checks could succeed while long
Internet transfers and reverse tunnels stalled. A full wake immediately restored
all 14 tested SSH directions. Inspect `pmset -g log` before changing routers or
adding reconnect loops. For a dedicated always-on desktop, an explicit policy is:

```sh
sudo pmset -c sleep 0
sudo pmset -a disablesleep 1
pmset -g                 # Verify SleepDisabled 1
```

This also prevents manual system sleep and increases idle energy use. It does
not disable screen locking, reboot, shutdown or FileVault. Display sleep can stay
enabled. To restore ordinary sleep eligibility, use `sudo pmset -a disablesleep 0`
and restore the recorded idle-sleep timer. Check again after reboot; no reboot
acceptance is implied by writing these settings.

If ordinary HTTPS transfers also stall, isolate that network problem separately.
A conservative MTU can be a diagnostic workaround for packet-size-dependent
failures, but does not by itself identify the faulty router, driver or link.
Record prior values and test both directions after any route/MTU change. Do not
apply workstation-specific MTU or service-order changes to every fleet member.

## VNC and native UU are separate

LazyTunnel forwards TCP to an existing desktop service; it does not enable
Screen Sharing or grant control permissions. Enable Screen Sharing for the
intended macOS user through System Settings. Apple's documentation notes that
[command-line activation alone does not grant full control](https://support.apple.com/guide/remote-desktop/apd8b1c65bd/mac).

An Ubuntu viewer can forward the Mac's VNC service privately:

```sh
lazy-web start mac-mini-vnc lazy-mac-mini 5900 \
  --ssh-config "$HOME/.config/lazytunnel-fleet/ssh_config" --local-port 15908
```

Although the generic helper prints an HTTP URL, this port carries **VNC**, not
HTTP. Connect Remmina to `127.0.0.1:15908`. Keep the forward loopback-only and
retain VNC authentication. It shares the existing console; it creates no XRDP
login session. Inspect the actual desktop before declaring visual/control success.

Obtain UU only from [NetEase's official site](https://uuyc.163.com/). A tested
4.42.0 package contains both arm64 and x86_64 binaries and runs natively on Apple
Silicon. Verify the installer signature and installed app signature; do not
assume an incompatible third-party download represents the current vendor build.
The user must sign in and allow Accessibility and Screen Recording for UU.
Do not edit TCC databases or disable SIP/Gatekeeper to bypass these permissions.

The vendor CLI can verify installation without exposing account secrets:

```sh
/usr/local/bin/uuyc-cli status
```

`networkStatus=connected` and a running XPC service are not proof that remote
video/control work. Test those only after login and privacy consent are complete.
