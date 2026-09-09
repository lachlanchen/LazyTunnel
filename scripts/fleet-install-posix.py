#!/usr/bin/env python3
"""Install a reviewed fleet bundle as the endpoint user; preserve legacy services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import pwd
import subprocess
import tempfile


def reconcile_authorized(old, prior, desired):
    managed=set(prior.splitlines())
    rows=[row for row in old.splitlines() if row not in managed]
    for line in desired.splitlines():
        if not line:continue
        blob=line.split()[1]
        if not any(blob in row.split() for row in rows):rows.append(line)
    return '\n'.join(rows)+'\n'


def write(path, text, mode=0o600):
    if path.is_symlink():
        raise RuntimeError('Refusing symlink target: '+str(path))
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        before=path.read_bytes()
        if before==text.encode():
            path.chmod(mode); return False
        backup=Path.home()/'.config/lazytunnel-fleet/backups'
        backup.mkdir(mode=0o700,exist_ok=True)
        dest=backup/(path.name+'.'+hashlib.sha256(before).hexdigest()[:16])
        if not dest.exists(): dest.write_bytes(before); dest.chmod(0o600)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.lazy-fleet-')
    with os.fdopen(fd,'w') as f: f.write(text)
    os.chmod(tmp,mode); os.replace(tmp,path)
    return True


def main():
    a=argparse.ArgumentParser();a.add_argument('bundle');a.add_argument('--apply',action='store_true')
    args=a.parse_args();b=json.loads(Path(args.bundle).read_text());p=b['peer'];files=b['files']
    home=Path.home();root=home/'.config/lazytunnel-fleet'
    assert p['home']==str(home) and p['platform']==platform.system().lower()
    assert p['user']==pwd.getpwuid(os.getuid()).pw_name and os.getuid()!=0
    if not args.apply:
        print('Plan:',p['name'],'aliases:',','.join(b['aliases'])); return
    os.umask(0o077)
    previous=root/'bundle.json'
    prior=json.loads(previous.read_text()) if previous.exists() else None
    if prior and prior['peer'].get('account','default') != p.get('account','default'):
        raise RuntimeError('Account transfer requires explicit identity migration')
    for role in ('tunnel','jump','login'):
        actual=subprocess.check_output(['/usr/bin/ssh-keygen','-y','-f',str(root/(role+'_ed25519'))],universal_newlines=True).strip()
        assert ' '.join(actual.split()[:2])==p[role+'_key'], 'Local identity mismatch'
    expected=' '.join(Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2])
    assert expected==p['host_key'], 'Local host identity mismatch'
    # Validate candidates before touching live client settings.
    for filename in ('ssh_config','carrier.conf'):
        with tempfile.NamedTemporaryFile(mode='w',dir=root) as f:
            f.write(files[filename]);f.flush()
            subprocess.run(['/usr/bin/ssh','-T','-G','-F',f.name,'lazy-'+p['name']],stdout=subprocess.DEVNULL,check=True)
    carrier_path=root/'carrier.conf'
    changed=carrier_path.exists() and carrier_path.read_text()!=files['carrier.conf']
    if changed and not p.get('external_carrier'):
        raise RuntimeError('Carrier settings changed: stop this fleet carrier explicitly before migration')
    for name in ('ssh_config','known_hosts','carrier.conf'):
        write(root/name,files[name])
    authorized=home/'.ssh/authorized_keys'
    old=authorized.read_text() if authorized.exists() else ''
    managed=prior['files']['authorized_keys.append'] if prior else ''
    write(authorized,reconcile_authorized(old,managed,files['authorized_keys.append']))
    config=home/'.ssh/config'
    old=config.read_text() if config.exists() else ''
    include='Include ~/.config/lazytunnel-fleet/ssh_config'
    if include not in old.splitlines():write(config,include+'\nHost *\n\n'+old)
    bindir=home/'.local/bin'
    write(bindir/'ssh-lazy',files['ssh-lazy'],0o755)
    if 'scp-lazy' in files:write(bindir/'scp-lazy',files['scp-lazy'],0o755)
    for alias in b['aliases']:
        path=bindir/('ssh-lazy-'+alias)
        if path.is_symlink() and os.readlink(path)=='ssh-lazy':continue
        if path.exists() or path.is_symlink():raise RuntimeError('Existing unrelated alias: '+str(path))
        path.symlink_to('ssh-lazy')
    if prior:
        for alias in set(prior['aliases'])-set(b['aliases']):
            path=bindir/('ssh-lazy-'+alias)
            if path.is_symlink() and os.readlink(path)=='ssh-lazy':path.unlink()
    if not p.get('external_carrier'):
        if p['platform']=='linux':
            unit=home/'.config/systemd/user/lazytunnel-fleet.service'
            write(unit,files['lazytunnel-fleet.service'])
            subprocess.run(['systemctl','--user','daemon-reload'],check=True)
            subprocess.run(['systemctl','--user','enable','--now','lazytunnel-fleet.service'],check=True)
        else:
            # Root installation is a separate explicit step. The daemon runs
            # as the endpoint user, not as root, and does not require GUI login.
            plist=files['art.lazying.lazytunnel-fleet.plist']
            plistlib.loads(plist.encode())
            write(root/'art.lazying.lazytunnel-fleet.plist',plist)
    print(json.dumps({'installed':p['name'],'external_carrier':p.get('external_carrier',False),
                      'commands':len(b['aliases']),'mac_launchdaemon_pending':p['platform']=='darwin'}))


if __name__=='__main__':main()
