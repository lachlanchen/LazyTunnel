# CLI 0.3.1 — idle viewers and validated updates

This release adds optional noVNC idle controls and upgrades the code installer.
It does not change enrollment, SSH permissions or a running desktop's input
handling. The Flutter native app keeps its separate release version.

## Behavior

- Viewer input timeout: 2 minutes. Hidden-page timeout: 10 seconds.
- Pause closes the WebSocket; Resume reconnects normally. Keep live supports
  passive viewing while visible. There is no automatic hidden reconnect loop.
- A separate web root leaves the system noVNC installation intact. Existing
  browser tabs need one reload after deployment.
- Code updates validate a candidate before promotion, retain previous releases
  and leave private identities and live SSH carriers alone.
- The reviewed fleet helper transfers roughly 104 KiB of allowlisted code
  through existing pinned SSH routes. Windows uses SFTP to avoid console-input
  buffering; installing Node on a native PowerShell endpoint is unnecessary.

See [setup, limits, fleet updates and rollback](bandwidth.md).

## Acceptance evidence, 2026-10-03

- 96 Python tests and 20 Node tests passed.
- A disposable real-noVNC/RFB browser test passed idle pause, hidden pause,
  Keep live, explicit Resume and page-close cleanup, without JavaScript errors.
- A read-only live viewer passed pause and reconnection checks. On a dedicated
  test SSH carrier, 15-second TCP payload samples measured **559.352 kbit/s active**
  and **0.084 kbit/s paused**. This is one short sample, not a billing guarantee.
- Native Windows PowerShell 5.1 passed isolated installation, installed
  self-update, legacy-backup retention, identity preservation and rejection of
  an invalid candidate.
- Real Node/OpenSSH account integration passed key/password login, UID ownership,
  idempotent enrollment, list/key/SSH isolation, spoof denial, rollback and
  revocation while an unrelated account's connection stayed working.
- Eight enrolled clients and one cloud server received code updates. Every
  installed updater repeated its own update successfully. Client identity
  hashes and cloud registry/policy hashes remained unchanged. The cloud SSH
  process was not restarted. No reboot was performed.
- Package inspection found no install hooks or unexpected private files. The
  package remains below 100 KiB compressed, without new npm dependencies.

## Lessons from older installations

Old three-script installers could omit newly introduced modules. The fleet
helper executes the reviewed candidate installer directly, then verifies the
installed updater. A regression test covers that legacy migration.

Windows PowerShell 5.1 needs a real temporary path for atomic file-replacement
backups; a null argument can become an invalid empty path. Resolve the default
script source in the script body. Both cases are covered by a native Windows
test, also required by the publishing workflow.

Candidate launch validation caught a missing server-side module before the
active server release changed. The server runtime file list now includes that
dependency and is tested in isolation.

A browser around a native VNC viewer can hide two streams. Pausing its noVNC
page does not stop the nested native viewer's upstream traffic. The unused
native viewer was disconnected once with authorization; reconnecting was not
disabled. Host-specific inventory, traffic logs and rollback files stay private.
