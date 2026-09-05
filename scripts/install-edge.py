#!/usr/bin/env python3
"""Install a reviewed relay manifest on a dedicated edge; --apply is explicit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import sys
import tempfile
import time

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from lazytunnel import validate, edge_files, require


def run(*args):
    return subprocess.run(args,check=True,capture_output=True,text=True)


def atomic(path, text, mode=0o600):
    require(not path.is_symlink(), 'Refusing symlink target')
    fd,name=tempfile.mkstemp(prefix='.lazytunnel-',dir=path.parent)
    try:
        os.fchmod(fd,mode)
        with os.fdopen(fd,'w') as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name): os.unlink(name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',required=True);p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    config=validate(json.loads(Path(a.config).read_text()))
    files=edge_files(config)
    accounts=files['accounts.txt'].splitlines()
    digest=hashlib.sha256(json.dumps(config,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    print('Manifest SHA256:',digest)
    print('Dedicated transport accounts:',', '.join(accounts))
    if not a.apply:
        print('Plan only; no changes. Public SSH ports/firewall are not modified.');return
    require(os.geteuid()==0,'Explicit --apply requires root on the cloud server')
    policy=Path('/etc/ssh/sshd_config.d/60-lazytunnel.conf')
    state=Path('/var/lib/lazytunnel')
    for path in [state,Path('/etc/lazytunnel'),Path('/etc/lazytunnel/keys'),policy]:
        require(not path.is_symlink(),'Refusing a symlink deployment path')
    old=json.loads((state/'state.json').read_text()) if (state/'state.json').exists() else None
    require(old is not None or not policy.exists(),'Existing policy has no LazyTunnel ownership record')
    if old: require(old['accounts']==accounts,'Peer membership changed; coordinate migration explicitly')
    for user in accounts:
        try:
            u=pwd.getpwnam(user)
            require(old and user in old['accounts'] and u.pw_gecos=='LazyTunnel transport'
                    and u.pw_shell=='/usr/sbin/nologin','Existing account has no verified ownership')
        except KeyError: pass
    run('/usr/sbin/sshd','-t')
    state.mkdir(mode=0o700,parents=True,exist_ok=True)
    revisions=state/'revisions';revisions.mkdir(mode=0o700,exist_ok=True)
    rev=Path(tempfile.mkdtemp(prefix=time.strftime('%Y%m%dT%H%M%S')+'-'+digest[:12]+'-',dir=revisions))
    atomic(rev/'manifest.json',json.dumps(config,indent=2)+'\n')
    # Ownership survives an interrupted first bootstrap; not a success marker.
    if old is None:
        atomic(state/'state.json',json.dumps({'digest':digest,'accounts':accounts,
            'revision':str(rev),'status':'preparing'},indent=2)+'\n')
    # Keys are public and root-owned; sshd reads AuthorizedKeysFile as the user.
    Path('/etc/lazytunnel/keys').mkdir(mode=0o755,parents=True,exist_ok=True)
    os.chmod('/etc/lazytunnel',0o755);os.chmod('/etc/lazytunnel/keys',0o755)
    for user in accounts:
        try: pwd.getpwnam(user)
        except KeyError:
            run('useradd','--system','--no-create-home','--home-dir','/nonexistent',
                '--shell','/usr/sbin/nologin','--password','*','--comment','LazyTunnel transport',user)
    targets={policy:files['60-lazytunnel.conf']}
    targets.update({Path('/etc/lazytunnel')/name:value for name,value in files.items() if name.startswith('keys/')})
    previous={}
    for index,(path,text) in enumerate(targets.items()):
        require(not path.is_symlink(),'Refusing symlink destination')
        previous[path]=path.read_text() if path.exists() else None
        if path.exists(): shutil.copy2(path,rev/f'before-{index}')
    atomic(rev/'rollback-map.json',json.dumps({str(k):v for k,v in previous.items()},indent=2)+'\n')
    try:
        for path,text in targets.items(): atomic(path,text,0o644)
        run('/usr/sbin/sshd','-t')
        run('systemctl','reload','ssh.service')
        atomic(state/'state.json',json.dumps({'digest':digest,'accounts':accounts,'revision':str(rev),'status':'installed'},indent=2)+'\n')
    except Exception:
        for index,(path,content) in enumerate(previous.items()):
            if content is None:
                if path.exists(): os.replace(path,rev/f'failed-{index}')
            else: atomic(path,content,0o644)
        run('/usr/sbin/sshd','-t');run('systemctl','reload','ssh.service')
        raise
    print('Policy validated and reloaded. Revision:',rev)
    print('No workstation tunnel was started. Verify effective Match policy and live boundaries.')


if __name__=='__main__':
    try: main()
    except (ValueError,OSError,subprocess.CalledProcessError) as e:
        print('LazyTunnel edge installation failed:',str(e),file=sys.stderr);sys.exit(1)
