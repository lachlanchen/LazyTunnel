#!/usr/bin/python3
"""Restricted SSH account RPC. No arbitrary shell, paths, commands or forwarding."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import sys
import tempfile
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from accounts import request

STATE = Path('/var/lib/lazytunnel-fleet')


def authenticated_account():
    if os.geteuid() != 0 or len(sys.argv) != 1:
        raise ValueError('Restricted account command')
    uid = int(os.environ.get('SUDO_UID', '-1'))
    user = pwd.getpwuid(uid)
    if uid <= 0 or not user.pw_name.startswith('lf-acct-') or user.pw_gecos != 'LazyTunnel fleet':
        raise ValueError('Authenticated account required')
    return user.pw_name.removeprefix('lf-acct-')


def main():
    os.umask(0o077)
    signal.alarm(60)
    account = authenticated_account()
    line = sys.stdin.buffer.readline(65537)
    if len(line) > 65536 or not line.endswith(b'\n'):
        raise ValueError('Request must be one bounded JSON line')
    message = json.loads(line)
    with (STATE/'accounts.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        raw = (STATE/'manifest.json').read_bytes()
        c = json.loads(raw)
        sockets = subprocess.check_output(['/usr/bin/ss','-Hltn'], text=True, timeout=5)
        occupied = {int(row.split()[3].rsplit(':',1)[1]) for row in sockets.splitlines()}
        candidate, result = request(c, account, message, occupied)
        if candidate != c:
            fd, filename = tempfile.mkstemp(dir=STATE, suffix='.json')
            try:
                with os.fdopen(fd, 'w') as f: json.dump(candidate, f)
                subprocess.run(['/usr/bin/python3', str(Path(__file__).with_name('fleet-install-edge.py')),
                                filename, '--apply', '--expect-revision', hashlib.sha256(raw).hexdigest()],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=45)
            finally: os.unlink(filename)
        print(json.dumps({'ok': True, **result}), flush=True)


if __name__ == '__main__':
    try: main()
    except (ValueError, KeyError, TypeError):
        print(json.dumps({'ok':False,'error':'Request denied or invalid for this account'}));sys.exit(1)
    except Exception:
        # One bounded private diagnostic, never request bodies or passwords.
        if os.geteuid()==0:
            try:
                fd=os.open(STATE/'account-last-error.log',os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
                with os.fdopen(fd,'w') as log:log.write(traceback.format_exc()[-16000:])
            except OSError:pass
        print(json.dumps({'ok':False,'error':'Account operation failed; ask the relay administrator to inspect its state'}));sys.exit(1)
