#!/usr/bin/env python3
"""Install additive, separately owned lf-* relay accounts; legacy lt-* is untouched."""
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
from fleet import validate, edge_files


def run(*args): return subprocess.run(args,check=True,capture_output=True,text=True)
def atomic(path,text,mode=0o644):
    if path.is_symlink():raise ValueError('Refusing symlink destination')
    fd,tmp=tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd,'w') as f:f.write(text)
    os.chmod(tmp,mode);os.replace(tmp,path)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest');ap.add_argument('--apply',action='store_true')
    a=ap.parse_args();c=validate(json.loads(Path(a.manifest).read_text()));files=edge_files(c)
    print('Fleet:',', '.join(p['name'] for p in c['peers']))
    if not a.apply:return
    assert os.getuid()==0,'Root required for cloud policy installation'
    state=Path('/var/lib/lazytunnel-fleet');policy=Path('/etc/ssh/sshd_config.d/70-lazytunnel-fleet.conf')
    keys=Path('/etc/lazytunnel-fleet/keys')
    for path in (state,keys,keys.parent,policy):
        assert not path.is_symlink(),'Symlink deployment path'
    previous=json.loads((state/'manifest.json').read_text()) if (state/'manifest.json').exists() else None
    assert previous or not policy.exists(),'Unowned existing policy'
    if previous:
        new={p['name']:p for p in c['peers']}
        for p in previous['peers']:
            assert p['name'] in new,'Removing an enrolled peer requires explicit revocation'
            for field in ('relay_port','host_key','tunnel_key','jump_key','external_carrier'):
                assert p.get(field)==new[p['name']].get(field),'Identity or port migration requires review'
    accounts=[s.split('/')[1] for s in files if s.startswith('keys/')]
    old_accounts=set(s.split('/')[1] for s in edge_files(previous) if s.startswith('keys/')) if previous else set()
    for account in accounts:
        try:
            u=pwd.getpwnam(account)
            shell='/bin/sh' if account.startswith('lf-info-') else '/usr/sbin/nologin'
            assert account in old_accounts and u.pw_gecos=='LazyTunnel fleet' and u.pw_shell==shell,'Unowned account'
        except KeyError:pass
    run('/usr/sbin/sshd','-t')
    # Refuse to bind a new fleet port over an existing owner's listener.
    sockets=run('ss','-Hltn').stdout
    oldnames={p['name'] for p in previous['peers']} if previous else set()
    for p in c['peers']:
        if not p.get('external_carrier') and p['name'] not in oldnames:
            assert not any(row.split()[3].endswith(':'+str(p['relay_port'])) for row in sockets.splitlines()),'Relay port occupied'
    state.mkdir(mode=0o700,parents=True,exist_ok=True);keys.mkdir(mode=0o755,parents=True,exist_ok=True)
    keys.parent.chmod(0o755);keys.chmod(0o755)
    bundles=keys.parent/'bundles';assert not bundles.is_symlink()
    bundles.mkdir(mode=0o755,exist_ok=True)
    targets={policy:files['70-lazytunnel-fleet.conf']}
    targets.update({keys/n.split('/')[1]:t for n,t in files.items() if n.startswith('keys/')})
    targets.update({bundles/n.split('/')[1]:t for n,t in files.items() if n.startswith('bundles/')})
    if previous==c and all(p.exists() and p.read_text()==t for p,t in targets.items()):
        print('Already installed; no SSH reload.');return
    rev=Path(tempfile.mkdtemp(prefix='revision-',dir=state))
    before={str(p):p.read_text() if p.exists() else None for p in targets}
    atomic(rev/'rollback.json',json.dumps(before,indent=2),0o600)
    for account in accounts:
        try:pwd.getpwnam(account)
        except KeyError:run('useradd','--system','--no-create-home','--home-dir','/' if account.startswith('lf-info-') else '/nonexistent',
                           '--shell','/bin/sh' if account.startswith('lf-info-') else '/usr/sbin/nologin',
                           '--password','*','--comment','LazyTunnel fleet',account)
        if account.startswith('lf-info-') and pwd.getpwnam(account).pw_dir=='/nonexistent':
            run('usermod','--home','/',account)
    # Record ownership before applying so interrupted enrollment is recoverable.
    atomic(state/'manifest.json',json.dumps(c,indent=2),0o600)
    try:
        for p,t in targets.items():
            atomic(p,t)
            if p.parent==bundles:
                os.chown(p,pwd.getpwnam('lf-info-'+p.stem).pw_uid,0)
                p.chmod(0o400)
        run('/usr/sbin/sshd','-t');run('systemctl','reload','ssh.service')
    except Exception:
        for path,text in before.items():
            p=Path(path)
            if text is None:
                if p.exists():p.rename(rev/(p.name+'.failed'))
            else:atomic(p,text)
        run('/usr/sbin/sshd','-t');run('systemctl','reload','ssh.service');raise
    print('Validated and reloaded fleet policy. Rollback:',rev)


if __name__=='__main__':main()
