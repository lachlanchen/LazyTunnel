#!/usr/bin/env python3
"""Explicit root-only administrator bootstrap. Secret JSON arrives on stdin."""
import json
import os
from pathlib import Path
import pwd
import re
import subprocess
import sys

if os.geteuid() != 0:
    raise SystemExit('Run on the reviewed cloud server as root')
data = json.load(sys.stdin)
user, key, password = data['username'], data['public_key'].strip(), data['password']
if not re.fullmatch('[a-z][a-z0-9_-]{0,30}', user) or user == 'root':
    raise SystemExit('Invalid unprivileged administrator name')
if not key.startswith('ssh-ed25519 ') or '\n' in key or '\r' in key:
    raise SystemExit('Invalid administrator public key')
if len(password) < 20 or '\n' in password or ':' in password:
    raise SystemExit('Use a generated password without line separators')
try:
    account = pwd.getpwnam(user)
    created = False
except KeyError:
    subprocess.run(['useradd', '--create-home', '--shell', '/bin/bash', user], check=True)
    account = pwd.getpwnam(user)
    created = True
if created:
    subprocess.run(['chpasswd'], input=f'{user}:{password}\n', text=True, check=True)
subprocess.run(['usermod', '--append', '--groups', 'sudo', user], check=True)
directory = Path(account.pw_dir)/'.ssh'
if directory.is_symlink(): raise SystemExit('Refusing symlink .ssh')
directory.mkdir(mode=0o700, exist_ok=True)
os.chmod(directory, 0o700); os.chown(directory, account.pw_uid, account.pw_gid)
path = directory/'authorized_keys'
if path.is_symlink(): raise SystemExit('Refusing symlink authorized_keys')
previous = path.read_text() if path.exists() else ''
if key not in previous.splitlines():
    fd=os.open(path, os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w') as f:
        if previous and not previous.endswith('\n'): f.write('\n')
        f.write(key+'\n')
os.chmod(path, 0o600); os.chown(path, account.pw_uid, account.pw_gid)
print(json.dumps({'username':user, 'created':created, 'sudo_group':True,
                  'password_set':created, 'ssh_public_key_installed':True}))
