#!/usr/bin/env bash
# Git for Windows supplies a consistent POSIX shell for ProxyJump's binary
# stream. Never pass the stream through PowerShell text pipelines or cmd.exe.
set -euo pipefail
case "${1:-}" in
    ssh|scp|sftp) device_ssh_program="$1"; shift ;;
    *) printf 'Expected ssh, scp or sftp\n' >&2; exit 2 ;;
esac
export SHELL=/bin/bash
exec "/usr/bin/$device_ssh_program" "$@"
