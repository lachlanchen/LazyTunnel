#!/usr/bin/env python3
"""Small POSIX client: code updates are separate from enrollment and live SSH."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile

STATE=Path.home()/'.config/lazytunnel-fleet'
CODE=Path.home()/'.local/share/lazytunnel/client'


def run(*args,**kwargs):return subprocess.run(args,check=True,**kwargs)
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    for name in ('install','update'):
        p=sub.add_parser(name);p.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1])
    p=sub.add_parser('prepare');p.add_argument('--name',required=True)
    p=sub.add_parser('login',help='activate a reviewed private enrollment bundle')
    p.add_argument('--bundle',type=Path,required=True)
    sub.add_parser('sync',help='fetch this enrolled device’s latest configuration over pinned SSH')
    sub.add_parser('status');sub.add_parser('devices');sub.add_parser('boot')
    p=sub.add_parser('ssh');p.add_argument('device');p.add_argument('args',nargs=argparse.REMAINDER)
    p=sub.add_parser('web');p.add_argument('device');p.add_argument('port',type=int)
    p.add_argument('--local-port',type=int);p.add_argument('--path',default='/')
    p=sub.add_parser('gui',help='optional local browser console')
    p.add_argument('action',nargs='?',default='open',choices=['open','serve','install','stop','status','code','rotate-code'])
    p.add_argument('--port',type=int,default=17765)
    a=ap.parse_args();os.umask(0o077)
    if a.command in ('install','update'):
        candidate=(a.source/'scripts/lazytunnel-client.py').resolve()
        if candidate != Path(__file__).resolve():
            # Let the reviewed new release define its complete file set.
            # Otherwise an old installer silently drops newly added modules.
            os.execv(sys.executable,[sys.executable,str(candidate),a.command,'--source',str(a.source.resolve())])
        names=['scripts/lazytunnel-client.py','scripts/fleet-prepare.py','scripts/fleet-install-posix.py','scripts/lazy-web']
        names+=['gui/'+n for n in ('server.py','index.html','app.js','style.css','icon.svg')]
        texts={n:(a.source/n).read_bytes() for n in names}
        digest=hashlib.sha256(b''.join(texts[n] for n in sorted(texts))).hexdigest()[:16]
        release=CODE/'releases'/digest
        for n,t in texts.items():
            p=release/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t);p.chmod(0o700)
        CODE.mkdir(parents=True,exist_ok=True)
        link=CODE/'next'
        if link.exists() or link.is_symlink():raise RuntimeError('An update is already staged')
        link.symlink_to(release);os.replace(link,CODE/'current')
        bindir=Path.home()/'.local/bin';bindir.mkdir(parents=True,exist_ok=True)
        launcher=bindir/'lazytunnel'
        if launcher.is_symlink():raise RuntimeError('Refusing unrelated launcher symlink')
        launcher.write_text('#!/bin/sh\nexec /usr/bin/python3 "'+str(CODE/'current/scripts/lazytunnel-client.py')+'" "$@"\n')
        launcher.chmod(0o755)
        pathline='export PATH="$HOME/.local/bin:$PATH" # LazyTunnel client commands'
        profiles=['.profile','.bashrc']
        if sys.platform=='darwin':profiles+=['.zprofile','.zshrc']
        for filename in profiles:
            profile=Path.home()/filename
            if profile.is_symlink():continue
            old=profile.read_text() if profile.exists() else ''
            if pathline not in old.splitlines():
                if old:
                    backup=CODE/'profile-backups';backup.mkdir(exist_ok=True)
                    saved=backup/(filename+'.'+hashlib.sha256(old.encode()).hexdigest()[:16])
                    if not saved.exists():saved.write_text(old)
                profile.write_text(old+'\n'+pathline+'\n')
        print('Client code installed:',digest,'— credentials and running carrier unchanged.');return
    code=Path(__file__).resolve().parent
    if a.command=='gui':
        os.execv(sys.executable,[sys.executable,str(code.parent/'gui/server.py'),a.action,'--port',str(a.port)])
    if a.command=='prepare':
        run(sys.executable,str(code/'fleet-prepare.py'),a.name);return
    if a.command in ('login','sync'):
        if a.command=='login':data=a.bundle.read_bytes()
        else:
            data=subprocess.check_output(['/usr/bin/ssh','-F',str(STATE/'ssh_config'),'lazy-fleet-registry'],timeout=30)
        parsed=json.loads(data)
        # The installer checks the local user, host key and all private/public
        # identity matches before accepting a server-provided bundle.
        STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
        fd,tmp=tempfile.mkstemp(dir=STATE,suffix='.candidate.json')
        try:
            with os.fdopen(fd,'wb') as f:f.write(data)
            run(sys.executable,str(code/'fleet-install-posix.py'),tmp,'--apply')
            os.replace(tmp,STATE/'bundle.json')
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
        print('Enrolled:',parsed['peer']['name'],'— aliases updated.');return
    b=json.loads((STATE/'bundle.json').read_text())
    if a.command=='boot':
        p=b['peer']
        if p['platform']=='linux':
            linger=subprocess.check_output(['loginctl','show-user',p['user'],'-p','Linger','--value'],text=True).strip()
            if linger!='yes':run('sudo','loginctl','enable-linger',p['user'])
            unit='lazytunnel.service' if p.get('external_carrier') else 'lazytunnel-fleet.service'
            run('systemctl','--user','enable','--now',unit)
        else:
            src=STATE/'art.lazying.lazytunnel-fleet.plist'
            dst=Path('/Library/LaunchDaemons')/src.name
            if dst.exists() and dst.read_bytes()!=src.read_bytes():raise ValueError('Existing daemon differs; explicit migration required')
            run('/usr/bin/plutil','-lint',str(src))
            if not dst.exists():run('sudo','/usr/bin/install','-o','root','-g','wheel','-m','0644',str(src),str(dst))
            label='system/art.lazying.lazytunnel-fleet'
            active=subprocess.run(['launchctl','print',label],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
            if not active:run('sudo','launchctl','bootstrap','system',str(dst))
            run('sudo','launchctl','enable',label)
        print('Boot startup configured; no reboot or desktop restart performed.');return
    if a.command=='devices':
        print('\n'.join('ssh-lazy-'+n for n in b['aliases']));return
    if a.command=='status':
        p=b['peer'];print('Device:',p['name']);print('User:',p['user']);print('Platform:',p['platform'])
        print('Private state:',STATE);print('Client code:',code)
        print('Carrier:', 'existing independently managed service' if p.get('external_carrier') else 'lazytunnel-fleet')
        print('Configured destinations:',len(b['aliases']));return
    if a.device not in b['aliases']:raise ValueError('Unknown enrolled device')
    if a.command=='ssh':
        os.execv('/usr/bin/ssh',['ssh','-F',str(STATE/'ssh_config'),'lazy-'+a.device]+a.args)
    if a.command=='web':
        local=a.local_port or a.port
        if not 1024 <= local <= 65535 or not 1 <= a.port <= 65535:raise ValueError('Invalid port')
        if not a.path.startswith('/') or any(ord(c)<32 for c in a.path):raise ValueError('Invalid URL path')
        print('Open on THIS computer: http://127.0.0.1:'+str(local)+a.path,flush=True)
        os.execv(sys.executable,[sys.executable,str(code/'lazy-web'),'run','lazy-'+a.device,str(a.port),
            '--ssh-config',str(STATE/'ssh_config'),'--local-port',str(local)])


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:
        print('LazyTunnel:',str(e),file=sys.stderr);sys.exit(1)
