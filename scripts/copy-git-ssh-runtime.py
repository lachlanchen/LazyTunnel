#!/usr/bin/env python3
"""Copy a minimal existing Git SSH runtime between trusted Windows endpoints.

Run on a POSIX operator machine with OpenSSH and GNU objdump. No private keys
or Git browser/account settings are read. Binaries stay in an ignored cache.
This avoids replacing Microsoft's SSH server and native outbound carrier.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import subprocess


def ps(host,script):
    encoded=base64.b64encode(script.encode('utf-16le')).decode()
    r=subprocess.run(['ssh','-oBatchMode=yes',host,
        'powershell.exe -NoProfile -NonInteractive -EncodedCommand '+encoded],
        check=True,capture_output=True,text=True,timeout=30)
    return r.stdout


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',required=True,help='existing trusted Windows SSH alias with Git installed')
    ap.add_argument('--destination',required=True,help='trusted Windows SSH alias')
    ap.add_argument('--cache',type=Path,default=Path.home()/'.cache/lazytunnel/git-ssh-runtime')
    a=ap.parse_args()
    for host in (a.source,a.destination):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]+',host):raise ValueError('Use a trusted SSH alias')
    raw=ps(a.source,"@(Get-ChildItem 'C:\\Program Files\\Git\\usr\\bin\\*' -Include '*.dll','*.exe'|Select-Object -ExpandProperty Name)|ConvertTo-Json")
    available=set(json.loads(raw));todo=['ssh.exe','scp.exe','sftp.exe','bash.exe','sh.exe'];seen=set()
    root=a.cache/'usr/bin';root.mkdir(parents=True,exist_ok=True)
    manifest={}
    while todo:
        name=todo.pop(0)
        if name in seen:continue
        if not re.fullmatch(r'[A-Za-z0-9_.-]+',name):raise ValueError('Invalid runtime filename')
        path=root/name
        subprocess.run(['scp','-q',a.source+':C:/Program Files/Git/usr/bin/'+name,str(path)],check=True,timeout=60)
        seen.add(name)
        headers=subprocess.check_output(['objdump','-p',str(path)],text=True)
        for dll in re.findall(r'DLL Name: (\S+)',headers):
            if dll in available and dll not in seen:todo.append(dll)
        manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest().upper()
    ps(a.destination,'New-Item -ItemType Directory -Force "$env:USERPROFILE\\.local\\share\\lazytunnel\\ssh-runtime\\usr\\bin", "$env:USERPROFILE\\.local\\share\\lazytunnel\\ssh-runtime\\tmp"|Out-Null')
    probe="@(Get-ChildItem \"$env:USERPROFILE\\.local\\share\\lazytunnel\\ssh-runtime\\usr\\bin\"|Get-FileHash -Algorithm SHA256|ForEach-Object {@{name=(Split-Path -Leaf $_.Path);hash=$_.Hash}})|ConvertTo-Json"
    previous=json.loads(ps(a.destination,probe) or '[]')
    old={p['name']:p['hash'] for p in previous}
    for name in seen:
        if old.get(name)==manifest[name]:continue
        subprocess.run(['scp','-q',str(root/name),a.destination+':.local/share/lazytunnel/ssh-runtime/usr/bin/'+name],check=True,timeout=60)
    actual=json.loads(ps(a.destination,probe))
    hashes={p['name']:p['hash'] for p in actual}
    if any(hashes.get(n)!=h for n,h in manifest.items()):raise RuntimeError('Destination checksum mismatch')
    (a.cache/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2))
    print('Verified',len(seen),'runtime files. Run the client login/sync to select this backend.')


if __name__=='__main__':main()
