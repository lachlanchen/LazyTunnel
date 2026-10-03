# Bandwidth-efficient private access

An SSH forward with no clients does not transmit a desktop. Small SSH keepalives
keep the route available. A connected VNC viewer is different: clocks, animation
and video can continue consuming bandwidth even when nobody is looking at it.
A static screen alone is not a reliable idle policy.

CLI 0.3.1 adds an optional noVNC data saver and validated code releases. The
existing management GUI does not open thumbnail streams or run automatic remote
SSH probes. Its visible local-state refresh pauses when the page is hidden.

## Viewer behavior

The data saver extends the full upstream noVNC `vnc.html` page:

| Condition | Behavior |
| --- | --- |
| Visible, used normally | Original keyboard, pointer and clipboard paths; compression level 6 |
| No local input for 2 minutes | Disconnect the viewer WebSocket; show **Resume desktop** |
| Page hidden for 10 seconds | Disconnect the viewer, including in Keep live mode |
| Pause button, page close or freeze | Release the viewer connection |
| **Keep live while visible** checked | Watch without the 2-minute input timeout |
| Resume clicked | Reconnect through the existing settings and authentication |

Pausing closes the video transport; hiding a canvas would not save that traffic.
Returning to a paused tab leaves it paused until Resume is clicked. Remote apps
and desktop sessions keep running, and reconnection remains available. The addon
records no keys, clipboard contents, screenshots or activity history. Browser
timer throttling can delay the deadline; this is not a quota or access restriction.

Only the full noVNC UI is supported, not `vnc_lite.html`, native viewers, RDP or
unrelated custom pages. We do not blanket-enable SSH compression for compressed
images, reduce every desktop resolution or weaken recovery keepalives.

## Install at the noVNC web server

On the Linux/macOS host serving the viewer's static files:

```bash
lazytunnel-client update
lazytunnel-client novnc-idle --source /usr/share/novnc \
  --output "$HOME/.local/share/lazytunnel/novnc/my-viewer"
```

Without npm, run `python3 scripts/novnc-idle.py` with the same arguments. This
creates a separate user-owned web root linking the original noVNC assets. It
never edits `/usr/share/novnc`, restarts a desktop, changes authentication or
takes over a service. It refuses an unrelated output directory; rerunning updates
only its own assets. Point **only the intended viewer's** websockify `--web` at
that directory. For an existing VNC server on loopback 5901 and a free port 6081:

```bash
websockify --web "$HOME/.local/share/lazytunnel/novnc/my-viewer" \
  127.0.0.1:6081 127.0.0.1:5901
```

Use the usual private SSH forward and its `/vnc.html` URL. Reload existing tabs
once to load the addon. Preserve original VNC authentication, loopback bindings
and any gateway authentication. Do not expose an unauthenticated desktop publicly.
For persistence, use a separately owned user service with user lingering; leave
other projects' desktop services alone. To remove the optional policy, restore
the original web root and reload. No desktop logout is needed.

### Nested viewers

Remmina inside Xvfb exposed through noVNC has **two streams**. Closing its browser
only stops the outer stream; Remmina may keep receiving the Mac/Windows desktop.
Gracefully disconnect an unused native viewer too, leaving remote apps and SSH
running. Relaunch it normally later. First verify ownership and whether a task
is using it; no browser attached is not by itself permission to terminate it.

## Small fleet updates through LazyTunnel itself

The helper transfers only package-allowlisted code through the pinned
`lazy-DEVICE` route, not a clone, browser profile, credentials, SDK or working
tree. SHA-256 verifies the transferred bytes; this integrity check is not a
separate publisher's signature. Use reviewed source.

```bash
# Default: show target, transfer size and digest without changing the peer.
python3 scripts/update-peer.py lazy-alpha --platform posix
python3 scripts/update-peer.py lazy-alpha --platform posix --apply
python3 scripts/update-peer.py lazy-beta --platform windows --apply
# If a Mac needs its non-system Python:
python3 scripts/update-peer.py lazy-mac --platform posix \
  --python /usr/local/bin/python3 --apply
```

Apply installs code, then asks the installed updater to install itself again to
check repeatability. It verifies unchanged identity/configuration hashes and
cleans its temporary transfer directory. It never restarts carriers, changes
enrollment or calls `sync`. Retry offline peers when reachable; no reconnect
daemon or monitoring loop is installed. No new npm dependencies are needed.

### Release validation and rollback

POSIX client/server updates compile candidate Python and run its CLI help before
promotion. Payloads go to new immutable release directories; existing contents
are never overwritten. A lock prevents simultaneous promotion. `current` changes
atomically, retaining `previous`; an unchanged update preserves that previous
release. Windows parses all three PowerShell scripts before promotion, replaces
`current.txt` atomically and keeps `previous.txt`. Its original legacy entry
script is saved once as `legacy-client-before-update.ps1`; the old helper scripts
remain in `code`. The command path becomes a compatibility launcher. Private
keys and scheduled tasks stay separate. Syntax/help checks cannot prove every
runtime path: verify status and a real SSH command after installation.

For explicit rollback, inspect POSIX `previous`, then atomically point `current`
back to that verified release. On Windows, validate the release in `previous.txt`
and atomically replace `current.txt` with those contents. For the first Windows
legacy migration, restore the saved entry script to `code/lazytunnel.ps1` instead.
These are operator actions, not automatic rollback loops. Keep an independent
administrator connection while updating the cloud. Root server releases stay
root-owned/private. Running carriers keep their existing configuration.

## Validate and measure

```bash
npm test
python3 -m unittest discover -s tests -v
npm run verify:package
# Optional: Playwright, Chromium and system noVNC/websockify required.
python scripts/test-idle-viewer.py
```

The browser test uses a disposable fake RFB desktop. It checks actual socket
closure, no automatic reconnect, explicit Resume, Keep live, hidden-page pause
and cleanup. It never touches a user's desktop or personal browser profile.

On Linux, sample `ss -tinp` counters for the exact SSH process over a bounded
interval, comparing paused and active viewers. A short sample is not a monthly
estimate or proof of zero total traffic. Pausing should stop screen traffic;
keepalives and explicit management requests remain. Check that SSH still works.
