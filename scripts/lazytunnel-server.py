#!/usr/bin/env python3
"""Cloud administration CLI. Client credentials never enter the code release."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fleet import validate,bundle


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    for cmd in ('install','update'):
        p=sub.add_parser(cmd);p.add_argument('--source',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('apply');p.add_argument('--manifest',required=True,type=Path);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('enroll');p.add_argument('--packet',required=True,type=Path);p.add_argument('--port',required=True,type=int)
    p.add_argument('--alias',action='append',default=[]);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('export');p.add_argument('--name',required=True);p.add_argument('--output',required=True,type=Path)
    sub.add_parser('devices');sub.add_parser('status')
    a=ap.parse_args();os.umask(0o077)
    if a.command in ('install','update'):
        files=['lazytunnel.py','fleet.py','scripts/lazytunnel-server.py','scripts/fleet-install-edge.py']
        contents={n:(a.source/n).read_bytes() for n in files}
        version=hashlib.sha256(b''.join(contents[n] for n in sorted(contents))).hexdigest()[:16]
        print('Server code release:',version)
        if not a.apply:return
        assert os.getuid()==0,'Run server installation as root'
        base=Path('/usr/local/lib/lazytunnel/server');release=base/'releases'/version
        for n,t in contents.items():
            p=release/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(t);p.chmod(0o755)
        link=base/'next'
        assert not link.exists() and not link.is_symlink(),'Pending update exists'
        link.symlink_to(release);os.replace(link,base/'current')
        launcher=Path('/usr/local/bin/lazytunnel-server')
        text='#!/bin/sh\nexec /usr/bin/python3 /usr/local/lib/lazytunnel/server/current/scripts/lazytunnel-server.py "$@"\n'
        if launcher.exists():assert 'lazytunnel/server/current' in launcher.read_text(),'Unowned launcher'
        launcher.write_text(text);launcher.chmod(0o755)
        print('Code updated. Identity registry and live SSH unchanged.');return
    if a.command=='apply':
        argv=[sys.executable,str(Path(__file__).with_name('fleet-install-edge.py')),str(a.manifest)]
        if a.apply:argv.append('--apply')
        subprocess.run(argv,check=True);return
    manifest=Path('/var/lib/lazytunnel-fleet/manifest.json')
    c=validate(json.loads(manifest.read_text()))
    if a.command=='enroll':
        p=json.loads(a.packet.read_text());p.update(relay_port=a.port,aliases=a.alias,external_carrier=False)
        if any(q['name']==p['name'] for q in c['peers']):raise ValueError('Device already enrolled; review identity before modifying it')
        c['peers'].append(p);validate(c)
        print('Enroll:',p['name'],'loopback relay port:',p['relay_port'])
        if not a.apply:return
        with tempfile.NamedTemporaryFile(mode='w',dir=manifest.parent,suffix='.json') as f:
            json.dump(c,f);f.flush()
            subprocess.run([sys.executable,str(Path(__file__).with_name('fleet-install-edge.py')),f.name,'--apply'],check=True)
        print('Registry published. Existing clients: lazytunnel sync. New client: export bundle, then lazytunnel login.');return
    if a.command=='export':
        data=json.dumps(bundle(c,a.name),indent=2)+'\n'
        fd=os.open(a.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write(data)
        print('Private enrollment bundle:',a.output);return
    for p in c['peers']:print(p['name'],p['platform'],'127.0.0.1:'+str(p['relay_port']))
    if a.command=='status':subprocess.run(['ss','-Hltn'],check=True)


if __name__=='__main__':main()
