#!/usr/bin/env python3
"""Prepare a per-device key or install a reviewed SSH peer bundle on POSIX.

Usage: device-ssh-endpoint.py prepare DEVICE_NAME
       device-ssh-endpoint.py install < private-reviewed-bundle.json
Never exports a private key. Existing unrelated SSH configuration is preserved.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile


def backup(path):
    if path.exists():
        data = path.read_bytes()
        dest = path.parent / ('device-ssh-backups')
        dest.mkdir(mode=0o700, exist_ok=True)
        copy = dest / (path.name + '.' + hashlib.sha256(data).hexdigest()[:16])
        if not copy.exists():
            copy.write_bytes(data)
            copy.chmod(0o600)


def write(path, text):
    if path.exists() and path.read_text() == text:
        return
    if path.is_symlink():
        raise RuntimeError('Refusing to replace symlink: ' + str(path))
    backup(path)
    temp = path.with_name(path.name + '.device-ssh-new')
    if temp.exists() or temp.is_symlink():
        raise RuntimeError('Staging path already exists: ' + str(temp))
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write(text)
    os.replace(str(temp), str(path))


def public_key(line):
    fields = line.strip().split()
    if len(fields) < 2 or fields[0] != 'ssh-ed25519':
        raise ValueError('Expected an ed25519 public key without options')
    raw = base64.b64decode(fields[1], validate=True)
    if len(raw) != 51:
        raise ValueError('Invalid ed25519 public key')
    return ' '.join(fields[:2])


def merge_keys(old, keys):
    # Do not weaken an existing restricted occurrence of the same public key.
    existing = old.splitlines()
    for line in keys:
        key = public_key(line)
        blob = key.split()[1]
        if not any(blob in row.split() for row in existing):
            existing.append(key + ' device-ssh')
    return '\n'.join(existing).rstrip() + '\n'


def main():
    os.umask(0o077)
    root = Path.home() / '.ssh'
    root.mkdir(mode=0o700, exist_ok=True)
    if len(sys.argv) == 3 and sys.argv[1] == 'prepare':
        name = sys.argv[2]
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,40}', name):
            raise ValueError('Invalid device name')
        pubs = {}
        for suffix in ('', '_hop'):
            key = root / ('id_ed25519_devices' + suffix)
            if not key.exists():
                if key.with_suffix('.pub').exists():
                    raise RuntimeError('Public key exists without private key')
                subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                                '-C', 'device-ssh-' + name + suffix, '-f', str(key)], check=True)
            pubs[suffix] = public_key(subprocess.check_output(
                ['ssh-keygen', '-y', '-f', str(key)], universal_newlines=True).strip())
        hostkey = Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().strip()
        print(json.dumps({'name': name, 'hostname': socket.gethostname(),
                          'home': str(Path.home()), 'public_key': pubs[''],
                          'hop_public_key': pubs['_hop'],
                          'host_key': public_key(hostkey)}))
    elif sys.argv[1:] == ['install']:
        bundle = json.load(sys.stdin)
        keys = bundle['authorized_keys']
        for key in keys:
            public_key(key)
        config = bundle['config']
        if not config.startswith('# Managed device SSH peers\n'):
            raise ValueError('Unreviewed configuration')
        main_config = root / 'config'
        old = main_config.read_text() if main_config.exists() else ''
        include = 'Include ~/.ssh/devices.conf'
        # Check the candidate together with unrelated existing configuration,
        # before modifying authorization or routing files.
        remainder = '\n'.join(row for row in old.splitlines() if row != include)
        with tempfile.NamedTemporaryFile(mode='w', dir=str(root)) as candidate:
            candidate.write(config + '\nHost *\n' + remainder + '\n')
            candidate.flush()
            subprocess.run(['ssh', '-G', '-F', candidate.name, 'device-server'],
                           stdout=subprocess.DEVNULL, check=True)
        authorized = root / 'authorized_keys'
        write(authorized, merge_keys(authorized.read_text() if authorized.exists() else '', keys))
        write(root / 'devices_known_hosts', bundle['known_hosts'])
        write(root / 'devices.conf', config)
        if include not in old.splitlines():
            write(main_config, include + '\nHost *\n\n' + old)
        result = subprocess.run(['ssh', '-G', 'device-server'], stdout=subprocess.DEVNULL,
                                stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode:
            raise RuntimeError('SSH configuration validation failed: ' + result.stderr)
        print(json.dumps({'installed': True, 'home': str(Path.home()), 'keys': len(keys)}))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
