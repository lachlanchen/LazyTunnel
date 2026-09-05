#!/usr/bin/env python3
"""Create endpoint-owned SSH identities and an explicitly requested public packet."""
import argparse
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lazytunnel import NAME, public_key, require, port

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--name', required=True)
p.add_argument('--relay-port', required=True, type=int)
p.add_argument('--ssh-port', default=22, type=int)
p.add_argument('--output', required=True)
a=p.parse_args()
require(NAME.fullmatch(a.name), 'Invalid endpoint name')
port(a.relay_port)
require(1 <= a.ssh_port <= 65535, 'Invalid local SSH port')
account=pwd.getpwuid(os.getuid())
require(account.pw_uid != 0, 'Run as the endpoint login user, not root')
home=Path(account.pw_dir)
state=home/'.config/lazytunnel'
require(not state.is_symlink(), 'Refusing a symlink identity directory')
state.mkdir(mode=0o700,parents=True,exist_ok=True)
require(state.stat().st_uid==os.getuid(), 'Identity directory is not user-owned')
os.chmod(state,0o700)
packet={'name':a.name,'user':account.pw_name,'home':str(home),
        'ssh_port':a.ssh_port,'relay_port':a.relay_port,
        'host_key':' '.join(Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2])}
public_key(packet['host_key'])
for role in ['tunnel','jump','login']:
    path=state/f'{role}_ed25519'
    require(not path.is_symlink(), 'Refusing symlink key')
    if not path.exists():
        require(not Path(str(path)+'.pub').exists(), 'Orphaned public key requires review')
        subprocess.run(['/usr/bin/ssh-keygen','-q','-t','ed25519','-N','','-C',f'lazytunnel-{a.name}-{role}','-f',str(path)],check=True)
    info=path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid==os.getuid() and info.st_mode & 0o077 == 0,
            'Private key permissions/ownership are unsafe')
    derived=subprocess.check_output(['/usr/bin/ssh-keygen','-y','-f',str(path)],text=True).strip()
    packet[role+'_key']=public_key(' '.join(derived.split()[:2]))
output=Path(a.output).absolute()
require(not output.is_symlink(), 'Refusing symlink packet')
if output.exists():
    require(json.loads(output.read_text())==packet,'Existing packet differs; review before changing identity')
    print('Existing enrollment packet matches; keys unchanged.')
else:
    output.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'w') as f:json.dump(packet,f,indent=2);f.write('\n')
    print('Public enrollment packet written; private keys remain on this endpoint.')
