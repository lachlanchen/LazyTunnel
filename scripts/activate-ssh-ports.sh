#!/usr/bin/env bash
# Explicit one-time fresh-Ubuntu socket cutover, after candidate validation.
# Must run in an independent systemd unit, not the bootstrap SSH session.
set -euo pipefail
target=/etc/ssh/sshd_config.d/00-lazytunnel-listen.conf
failed=/root/lazytunnel-listen.failed.conf
[[ $EUID -eq 0 && -f "$target" && ! -L "$target" && ! -e "$failed" ]]
rollback() {
  local code=$?
  trap - ERR
  # Precondition: this new file had no predecessor. Retain the failed candidate.
  mv -- "$target" "$failed"
  /usr/sbin/sshd -t
  systemctl daemon-reload
  systemctl restart ssh.socket
  systemctl restart ssh.service
  systemctl restart lazytunnel-bootstrap.service || true
  exit "$code"
}
trap rollback ERR
/usr/sbin/sshd -t
systemctl daemon-reload
systemctl show ssh.socket -p Listen --value | grep -q ':2222 '
systemctl stop lazytunnel-bootstrap.service
systemctl restart ssh.socket
systemctl restart ssh.service
systemctl enable ssh.socket
/usr/sbin/sshd -t
ss -ltn 'sport = :2222' | grep -q LISTEN
ss -ltn 'sport = :22' | grep -q LISTEN
trap - ERR
printf '%s\n' 'Native SSH sockets active on 22 and 2222; key-only authentication.'
