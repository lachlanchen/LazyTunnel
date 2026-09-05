#!/usr/bin/env python3
"""Install this user's reviewed worker artifacts; never change desktop services."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lazytunnel import validate, worker_files, require


def run(args, check=True):
    return subprocess.run(args,check=check,capture_output=True,text=True)


def atomic(path, text, mode=0o600):
    require(not path.is_symlink(),'Refusing symlink destination')
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.lazytunnel-',dir=path.parent)
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--peer',required=True)
    p.add_argument('--apply',action='store_true');p.add_argument('--start',action='store_true')
    a=p.parse_args();c=validate(json.loads(Path(a.config).read_text()))
    files=worker_files(c,a.peer);peer=next(x for x in c['peers'] if x['name']==a.peer)
    require(not a.start or a.apply,'--start requires --apply')
    if not a.apply:
        print('Plan only: private SSH configuration, known hosts, endpoint authorized key additions, one user unit.');return
    user=pwd.getpwuid(os.getuid())
    require(user.pw_uid!=0 and user.pw_name==peer['user'] and user.pw_dir==peer['home'],
            'Run as the exact endpoint login user, never as root')
    home=Path(user.pw_dir);state=home/'.config/lazytunnel'
    for path in [home/'.config',state,home/'.ssh',home/'.config/systemd',home/'.config/systemd/user']:
        require(not path.is_symlink(),'Refusing symlink configuration directory')
    for role in ['tunnel','jump','login']:
        key=state/f'{role}_ed25519'
        require(key.is_file() and not key.is_symlink() and key.stat().st_uid==os.getuid()
                and key.stat().st_mode & 0o077==0,'Missing or unsafe private identity')
        pub=run(['/usr/bin/ssh-keygen','-y','-f',str(key)]).stdout.strip()
        require(' '.join(pub.split()[:2])==peer[role+'_key'],'Manifest identity does not match local private key')
    host=' '.join(Path('/etc/ssh/ssh_host_ed25519_key.pub').read_text().split()[:2])
    require(host==peer['host_key'],'Local SSH host key differs from reviewed enrollment')
    auth=home/'.ssh/authorized_keys'
    require(not auth.is_symlink(),'Refusing symlink authorized_keys')
    original=auth.read_text() if auth.exists() else ''
    additions=[]
    for line in files['authorized_keys.append'].splitlines():
        if line not in original.splitlines(): additions.append(line)
    targets={state/'ssh_config':files['ssh_config'],state/'known_hosts':files['known_hosts'],
             home/'.config/systemd/user/lazytunnel.service':files['lazytunnel.service']}
    if additions:targets[auth]=original+('' if not original or original.endswith('\n') else '\n')+'\n'.join(additions)+'\n'
    ownership=state/'worker-state.json'
    old=json.loads(ownership.read_text()) if ownership.exists() else None
    require(old is None or old['peer']==a.peer,'Existing worker belongs to another peer')
    for target in targets:
        require(not target.is_symlink(),'Refusing symlink target')
        if target.exists() and target!=auth:
            require(old is not None,'Existing target has no worker ownership record')
    changed={t:s for t,s in targets.items() if not t.exists() or t.read_text()!=s}
    active=run(['systemctl','--user','is-active','--quiet','lazytunnel.service'],check=False).returncode==0
    require(not active or not changed,'Active configuration would change; coordinate stopping only this carrier before applying')
    digest=hashlib.sha256(json.dumps(c,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if changed:
        state.mkdir(mode=0o700,parents=True,exist_ok=True)
        rev=Path(tempfile.mkdtemp(prefix='worker-before-',dir=state))
        atomic(rev/'rollback.json',json.dumps({str(t):t.read_text() if t.exists() else None for t in changed},indent=2)+'\n')
        for target,text in changed.items():atomic(target,text)
        atomic(ownership,json.dumps({'peer':a.peer,'digest':digest,'rollback':str(rev)},indent=2)+'\n')
        run(['/usr/bin/ssh','-F',str(state/'ssh_config'),'-G','lazytunnel-carrier'])
        run(['systemctl','--user','daemon-reload'])
    if a.start:
        run(['systemctl','--user','enable','--now','lazytunnel.service'])
        print('User carrier enabled; check end-to-end health, not just unit activation.')
    print('Artifacts changed:',len(changed))
    linger=run(['loginctl','show-user',user.pw_name,'-p','Linger'],check=False)
    print(linger.stdout.strip() or 'Linger status unavailable')
    if linger.stdout.strip()!='Linger=yes':
        print('Boot/logout persistence requires administrator approval: loginctl enable-linger '+user.pw_name)
    print('Use: ssh -F ~/.config/lazytunnel/ssh_config PEER')
    print('No UU/RDP/VNC, default route, firewall or system sshd settings changed.')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        print('LazyTunnel worker installation failed:',str(e),file=sys.stderr);sys.exit(1)
