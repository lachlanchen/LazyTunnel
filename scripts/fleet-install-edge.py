#!/usr/bin/env python3
"""Install additive, separately owned lf-* relay accounts; legacy lt-* is untouched."""
import argparse
import fcntl
import signal
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
from accounts import transition


def run(*args): return subprocess.run(args,check=True,capture_output=True,text=True)
def atomic(path,text,mode=0o644):
    if path.is_symlink():raise ValueError('Refusing symlink destination')
    fd,tmp=tempfile.mkstemp(dir=path.parent)
    with os.fdopen(fd,'w') as f:f.write(text)
    os.chmod(tmp,mode);os.replace(tmp,path)


def verify_effective_policy(text):
    # sshd uses the first matching value. A preceding wildcard Match must not
    # silently grant a login shell or wider forwarding than our generated policy.
    expected={};current=None
    for line in text.splitlines():
        parts=line.strip().split(None,1)
        if not parts or parts[0].startswith('#'):continue
        if parts[0]=='Match':
            current=parts[1][5:] if parts[1].startswith('User lf-') else None
            if current:expected[current]={}
        elif current:expected[current][parts[0].lower()]=parts[1]
    for user,settings in expected.items():
        actual=run('/usr/sbin/sshd','-T','-C','user='+user+',host=localhost,addr=127.0.0.1').stdout
        values=dict(line.split(None,1) for line in actual.splitlines() if ' ' in line)
        for key,value in settings.items():
            if values.get(key)!=value:
                raise ValueError('Conflicting earlier SSH policy for '+user+': '+key)


def terminate_sessions(users):
    # End only managed identities affected by revocation. Preserve administrators
    # and every other account's carrier/desktop. Open sessions retain old policy.
    if not users:return
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit(): continue
        try:
            if directory.stat().st_uid != 0:continue
            exe = (directory/'comm').read_text().strip()
            command = (directory/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
            if exe in ('sshd', 'sshd-session') and any(command.startswith('sshd: '+u+' ') for u in users):
                os.kill(int(directory.name), signal.SIGTERM)
        except (FileNotFoundError, ProcessLookupError): pass


def main():
    ap=argparse.ArgumentParser();ap.add_argument('manifest');ap.add_argument('--apply',action='store_true');ap.add_argument('--expect-revision')
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
    disconnect=transition(previous,c)
    state.mkdir(mode=0o700,parents=True,exist_ok=True)
    lock=(state/'policy.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX)
    # Re-read under the shared lock; an account enrollment never overwrites a
    # concurrent administrator change made after its planning read.
    latest=(state/'manifest.json').read_bytes() if (state/'manifest.json').exists() else None
    if a.expect_revision:
        assert latest and hashlib.sha256(latest).hexdigest()==a.expect_revision,'Concurrent policy change; retry explicitly'
    previous=json.loads(latest) if latest else None
    disconnect=transition(previous,c)
    accounts=[s.split('/')[1] for s in files if s.startswith('keys/')]
    old_accounts=set(s.split('/')[1] for s in edge_files(previous) if s.startswith('keys/')) if previous else set()
    owned_path=state/'owned-users.json'
    owned=set(json.loads(owned_path.read_text())) if owned_path.exists() else set(old_accounts)
    for account in accounts:
        try:
            u=pwd.getpwnam(account)
            shell='/bin/sh' if account.startswith(('lf-info-','lf-acct-')) else '/usr/sbin/nologin'
            assert account in owned and u.pw_gecos=='LazyTunnel fleet' and u.pw_shell==shell,'Unowned account'
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
    bundles.chmod(0o755)
    targets={policy:files['70-lazytunnel-fleet.conf'], state/'manifest.json':json.dumps(c,indent=2)}
    targets.update({keys/n.split('/')[1]:t for n,t in files.items() if n.startswith('keys/')})
    targets.update({bundles/n.split('/')[1]:t for n,t in files.items() if n.startswith('bundles/')})
    sudoers=Path('/etc/sudoers.d/lazytunnel-accounts')
    if c['version']==2:
        assert Path('/usr/local/lib/lazytunnel/server/current/scripts/account-command.py').is_file(),'Install the account runtime first'
        assert not sudoers.is_symlink() and (previous and previous.get('version')==2 or not sudoers.exists()),'Unowned sudoers policy'
        text='# LazyTunnel account RPC; no arguments or arbitrary root commands.\n'
        text+=''.join('lf-acct-'+name+' ALL=(root) NOPASSWD: /usr/local/lib/lazytunnel/server/current/scripts/account-command.py ""\n' for name in sorted(c['accounts']))
        with tempfile.NamedTemporaryFile(mode='w') as f:
            f.write(text);f.flush();run('/usr/sbin/visudo','-cf',f.name)
        targets[sudoers]=text
    if previous==c and all(p.exists() and p.read_text()==t for p,t in targets.items()):
        print('Already installed; no SSH reload.');return
    rev=Path(tempfile.mkdtemp(prefix='revision-',dir=state))
    before={str(p):dict(text=p.read_text(),mode=p.stat().st_mode & 0o777,uid=p.stat().st_uid,gid=p.stat().st_gid) if p.exists() else None for p in targets}
    atomic(rev/'rollback.json',json.dumps(before,indent=2),0o600)
    for account in accounts:
        try:pwd.getpwnam(account)
        except KeyError:
            run('useradd','--system','--no-create-home','--home-dir','/' if account.startswith(('lf-info-','lf-acct-')) else '/nonexistent',
                '--shell','/bin/sh' if account.startswith(('lf-info-','lf-acct-')) else '/usr/sbin/nologin',
                '--password','*','--comment','LazyTunnel fleet',account)
            owned.add(account)
            atomic(owned_path,json.dumps(sorted(owned)),0o600)
        if account.startswith(('lf-info-','lf-acct-')) and pwd.getpwnam(account).pw_dir=='/nonexistent':
            run('usermod','--home','/',account)
    atomic(owned_path,json.dumps(sorted(owned|set(accounts))),0o600)
    try:
        for p,t in targets.items():
            atomic(p,t,0o600 if p==state/'manifest.json' else 0o440 if p==sudoers else 0o644)
            if p.parent==bundles:
                os.chown(p,pwd.getpwnam('lf-info-'+p.stem).pw_uid,0)
                p.chmod(0o400)
        run('/usr/sbin/sshd','-t')
        verify_effective_policy(files['70-lazytunnel-fleet.conf'])
        run('systemctl','reload','ssh.service')
    except Exception:
        for path,saved in before.items():
            p=Path(path)
            if saved is None:
                if p.exists():p.rename(rev/(p.name+'.failed'))
            else:
                atomic(p,saved['text'],saved['mode']);os.chown(p,saved['uid'],saved['gid'])
        run('/usr/sbin/sshd','-t');run('systemctl','reload','ssh.service');raise
    terminate_sessions(disconnect)
    print('Validated and reloaded fleet policy. Rollback:',rev)


if __name__=='__main__':main()
