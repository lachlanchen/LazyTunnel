#!/usr/bin/python3
"""Relay operator account administration; preview unless --apply is specified."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from accounts import upgrade, inventory
from fleet import validate
from lazytunnel import public_key, require

STATE=Path('/var/lib/lazytunnel-fleet')


def arguments():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('init');p.add_argument('--host',required=True);p.add_argument('--port',type=int,default=2222)
    p.add_argument('--host-key-file',required=True,type=Path);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('add');p.add_argument('name');p.add_argument('--key-file',type=Path)
    p.add_argument('--password-file',type=Path);p.add_argument('--apply',action='store_true')
    for action in ('disable','enable'):
        p=sub.add_parser(action);p.add_argument('name');p.add_argument('--apply',action='store_true')
    p=sub.add_parser('password');p.add_argument('name');p.add_argument('--password-file',required=True,type=Path);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('key');p.add_argument('name');p.add_argument('--key-file',required=True,type=Path);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('invite');p.add_argument('name');p.add_argument('--output',required=True,type=Path)
    sub.add_parser('list')
    return ap.parse_args()


def read_password(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        info=os.fstat(fd)
        require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077 and info.st_nlink==1, 'Password file must be regular, owner-only and not linked')
        with os.fdopen(fd,'r',closefd=False) as f: value=f.read(1025).rstrip('\r\n')
        require(12<=len(value)<=1024 and not any(c in value for c in '\r\n\x00'), 'Use a single-line password of 12–1024 characters')
        return value
    finally: os.close(fd)


def main():
    a=arguments();os.umask(0o077)
    manifest=STATE/'manifest.json'
    old=manifest.read_bytes() if manifest.exists() else None
    if a.action=='init':
        require(old is None,'Relay already initialized; account add preserves the existing fleet')
        key=public_key(' '.join(a.host_key_file.read_text().split()[:2]))
        c={'version':2,'edge':{'host':a.host,'port':a.port,'host_key':key},'peers':[],
           'accounts':{'default':{'enabled':True,'password_auth':False,'login_keys':[]}}}
    else:
        require(old is not None,'Initialize the relay first')
        c=upgrade(json.loads(old))
    password=None
    if hasattr(a,'name'):
        require(re.fullmatch(r'[a-z][a-z0-9-]{0,19}',a.name),'Invalid account name')
    if a.action=='list':
        for name, account in c['accounts'].items():
            print(name,'enabled' if account['enabled'] else 'disabled',sum(p.get('account')==name for p in c['peers']),'devices')
        return
    if a.action=='add':
        require(a.key_file or a.password_file,'Provide --key-file or --password-file for account authentication')
        keys=[public_key(' '.join(a.key_file.read_text().split()[:2]))] if a.key_file else []
        record={'enabled':True,'login_keys':keys,'password_auth':bool(a.password_file)}
        if a.name in c['accounts']:
            require(c['accounts'][a.name]==record,'Account exists with different settings')
            print('Account already exists; password unchanged.');return
        c['accounts'][a.name]=record
        if a.password_file: password=read_password(a.password_file)
    if a.action in ('disable','enable','password','key','invite'):
        require(a.name in c['accounts'],'Unknown account')
        if a.action in ('disable','enable'): c['accounts'][a.name]['enabled']=a.action=='enable'
        if a.action=='password':
            password=read_password(a.password_file);c['accounts'][a.name]['password_auth']=True
        if a.action=='key':c['accounts'][a.name]['login_keys']=[public_key(' '.join(a.key_file.read_text().split()[:2]))]
        if a.action=='invite':
            require(c['accounts'][a.name]['enabled'],'Account disabled')
            require(c['accounts'][a.name]['login_keys'] or c['accounts'][a.name]['password_auth'],'Configure account credentials before exporting an invitation')
            fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
            with os.fdopen(fd,'w') as f:json.dump({'version':1,'account':a.name,'edge':c['edge']},f,indent=2);f.write('\n')
            print('Pinned account invitation:',a.output);return
    validate(c)
    print('Account operation:',a.action,getattr(a,'name','relay'))
    if not a.apply:
        print('Preview only; add --apply to change the owned relay policy.');return
    require(os.getuid()==0,'Run account administration as root')
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    with tempfile.NamedTemporaryFile(mode='w',dir=STATE,suffix='.json') as f:
        json.dump(c,f);f.flush()
        argv=['/usr/bin/python3',str(Path(__file__).with_name('fleet-install-edge.py')),f.name,'--apply']
        if old:argv+=['--expect-revision',hashlib.sha256(old).hexdigest()]
        subprocess.run(argv,check=True)
    if password:
        # The password reaches chpasswd through a private pipe, never argv/logs.
        subprocess.run(['/usr/sbin/chpasswd'],input='lf-acct-'+a.name+':'+password+'\n',text=True,check=True,
                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    print('Account policy installed. Existing device identities retained.')


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,subprocess.SubprocessError) as error:
        print('Account administration failed:',str(error),file=sys.stderr);sys.exit(1)
