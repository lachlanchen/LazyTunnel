#!/usr/bin/env python3
"""Standalone LazyTunnel agent; runs without either user interface."""
import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lazytunnel_core.controller import Controller, STATE, atomic
from lazytunnel_core.http_api import Server

PORT = 17766
MARKER = '# Managed by LazyTunnel agent v1\n'


def unit_argument(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('%', '%%').replace('$', '$$') + '"'


def ready(port, seconds=8):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            with opener.open('http://127.0.0.1:' + str(port) + '/health', timeout=.5) as response:
                if json.load(response).get('service') == 'lazytunnel-agent':
                    return True
        except (OSError, ValueError):
            pass
        time.sleep(.2)
    return False


def install(port):
    if sys.platform != 'linux':
        raise ValueError('Agent service installation currently requires Linux; use serve otherwise')
    script = Path.home() / '.local/share/lazytunnel/client/current/lazytunnel_core/agent.py'
    if not script.is_file():
        raise ValueError('Install the updated client from the reviewed checkout first')
    unit = Path.home() / '.config/systemd/user/lazytunnel-agent.service'
    expected = MARKER + '[Unit]\nDescription=LazyTunnel independent control agent\n\n[Service]\nExecStart=' + \
        ' '.join(unit_argument(v) for v in [sys.executable, script, 'serve', '--port', port]) + \
        '\nRestart=on-failure\nRestartSec=5\nUMask=0077\nNoNewPrivileges=true\nPrivateTmp=true\n\n[Install]\nWantedBy=default.target\n'
    unit.parent.mkdir(parents=True, exist_ok=True)
    if unit.is_symlink() or (unit.exists() and unit.read_text() != expected):
        raise ValueError('Existing agent unit differs; explicit migration required')
    if not unit.exists():
        import socket
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', port))
        atomic(unit, expected)
    subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
    subprocess.run(['systemctl', '--user', 'enable', '--now', unit.name], check=True)
    if not ready(port):
        raise ValueError('Agent did not become ready; inspect lazytunnel agent status')
    print('Independent agent ready on loopback port', port)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', default='status', choices=['serve', 'install', 'stop', 'status', 'code', 'rotate-code'])
    parser.add_argument('--port', type=int, default=PORT)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise ValueError('Invalid agent port')
    os.umask(0o077)
    controller = Controller(port=args.port)
    if args.action == 'code':
        print(controller.code())
        return
    if args.action == 'rotate-code':
        atomic(controller.folder / 'access-code', secrets.token_urlsafe(32) + '\n')
        print('Access code rotated. SSH credentials and forwards are unchanged.')
        return
    if args.action == 'install':
        install(args.port)
        return
    if args.action in ('stop', 'status'):
        unit = Path.home() / '.config/systemd/user/lazytunnel-agent.service'
        if args.action == 'stop':
            if unit.is_symlink() or not unit.is_file() or not unit.read_text().startswith(MARKER):
                raise ValueError('Refusing to stop an unowned agent unit')
            subprocess.run(['systemctl', '--user', 'disable', '--now', unit.name], check=True)
            print('Agent stopped. SSH carriers and independent web forwards remain running.')
        else:
            subprocess.run(['systemctl', '--user', 'status', '--no-pager', unit.name], check=False)
        return
    lock = (controller.folder / 'agent.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('This identity already has a running agent')
    server = Server(('127.0.0.1', args.port), controller)
    print('LazyTunnel independent agent: http://127.0.0.1:' + str(args.port), flush=True)
    try:
        server.serve_forever(poll_interval=.5)
    finally:
        server.server_close()
        controller.pool.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('LazyTunnel agent:', error, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
