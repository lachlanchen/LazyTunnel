# LazyTunnel

Small, independent, private SSH relays using native OpenSSH and systemd.
This is separate from LazyEdge's authenticated HTTP gateway and from UU's
desktop-control lifecycle. Never change an existing UU/RDP/VNC service to
deploy a tunnel.

- Inspect actual listeners, SSH config, firewall, users and active sessions first.
- Reverse listeners bind only to 127.0.0.1; use end-to-end SSH through a restricted jump account.
- Separate tunnel, jump and endpoint identities. Pin host keys.
- Generate reviewed artifacts before installing. Validate sshd before reload;
  retain an independent administrator connection and an exact rollback copy.
- Do not reboot, replace firewall policy, disable existing SSH ports, or publish
  raw desktop/management ports as a deployment shortcut.
- Credentials and host-specific inventory live outside Git. Generated files
  are ignored. Never commit credentials, browser profiles, or private keys.
- Use standard-library Python, argument arrays, bounded checks and systemd
  recovery. Do not add an aggressive monitoring/reconnect loop.
- Preserve unrelated worktree changes. Test with `python3 -m unittest discover
  -s tests -v` and `git diff --check`.

Operational state: preparation, not a verified deployment. Replace this status
only with actual acceptance evidence. Enabling units is not a reboot test.
