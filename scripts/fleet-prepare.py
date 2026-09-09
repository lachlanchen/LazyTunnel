#!/usr/bin/env python3
"""Create local fleet identities and print only public enrollment data (POSIX)."""
import json
import os
from pathlib import Path
import platform
import pwd
import re
import subprocess
import sys

name = sys.argv[1]
if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,19}', name):
    raise SystemExit('Invalid device name')
os.umask(0o077)
home = Path.home()
root = home / '.config/lazytunnel-fleet'
if root.is_symlink():
    raise SystemExit('Refusing symlink identity directory')
root.mkdir(parents=True, exist_ok=True, mode=0o700)
root.chmod(0o700)
keys = {}
for role in ('tunnel', 'jump', 'login'):
    path = root / (role + '_ed25519')
    if path.is_symlink():
        raise SystemExit('Refusing symlink identity')
    if not path.exists():
        if Path(str(path)+'.pub').exists():
            raise SystemExit('Orphaned public key: review before enrollment')
        subprocess.run(['/usr/bin/ssh-keygen', '-q', '-t', 'ed25519', '-N', '',
                        '-f', str(path), '-C', 'lazy-fleet-'+name+'-'+role], check=True)
    if path.stat().st_mode & 0o077 or path.stat().st_uid != os.getuid():
        raise SystemExit('Unsafe private-key permissions')
    keys[role+'_key'] = ' '.join(subprocess.check_output(
        ['/usr/bin/ssh-keygen','-y','-f',str(path)], universal_newlines=True).split()[:2])
print(json.dumps(dict(keys, name=name, user=pwd.getpwuid(os.getuid()).pw_name,
    home=str(home), platform=platform.system().lower(),
    hostname=platform.node(), ssh_port=22,
    host_key=' '.join(Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2]))))
