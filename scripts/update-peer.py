#!/usr/bin/env python3
"""Transfer a reviewed client release through its existing LazyTunnel SSH route.

Explicit target, pinned OpenSSH config, code-only update. No carrier restart,
credential migration, npm dependency install, desktop action or polling daemon.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]

POSIX=r'''
import base64,hashlib,io,json,os,pathlib,subprocess,sys,tempfile,zipfile
os.umask(0o077)
state=pathlib.Path.home()/'.config/lazytunnel-fleet'
def identities():
 return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in state.iterdir() if p.is_file() and (p.name in ('bundle.json','ssh_config','known_hosts','carrier.conf') or p.name.endswith('_ed25519'))}
before=identities()
raw=sys.stdin.buffer.read(3*1024*1024+1)
if len(raw)>3*1024*1024 or hashlib.sha256(raw).hexdigest()!=EXPECTED:raise RuntimeError('Transfer digest mismatch')
with tempfile.TemporaryDirectory(prefix='lazytunnel-update-') as tmp:
 root=pathlib.Path(tmp)
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  for info in archive.infolist():
   p=pathlib.PurePosixPath(info.filename)
   if p.is_absolute() or '..' in p.parts or info.file_size>2*1024*1024:raise RuntimeError('Invalid release member')
   dest=root.joinpath(*p.parts);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(archive.read(info))
 launcher=pathlib.Path.home()/'.local/bin/lazytunnel'
 # Some pre-npm installers copy only three scripts; always execute the reviewed
 # candidate so it owns the complete file list, including new modules.
 command=[sys.executable,str(root/'scripts/lazytunnel-client.py')]
 subprocess.run(command+['update','--source',str(root)],check=True,timeout=60)
 current=pathlib.Path.home()/'.local/share/lazytunnel/client/current'
 subprocess.run([str(launcher),'update','--source',str(current)],check=True,timeout=60)
 subprocess.run([str(launcher),'status'],check=True,timeout=20)
 if before!=identities():raise RuntimeError('Identity changed unexpectedly; inspect before proceeding')
 print(json.dumps({'updated':True,'version':json.loads((current/'package.json').read_text())['version'],'release':current.resolve().name,'identity_unchanged':True,'self_update_verified':True}))
'''

WINDOWS=r'''
$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue'
$state=Join-Path $env:USERPROFILE '.config\lazytunnel-fleet'
function IdentityHashes {
 $rows=Get-ChildItem -LiteralPath $state -File | Where-Object {$_.Name -in @('bundle.json','ssh_config','known_hosts','carrier.conf','carrier.ps1') -or $_.Name.EndsWith('_ed25519')} | Sort-Object Name | ForEach-Object {$_.Name+':'+(Get-FileHash -LiteralPath $_.FullName).Hash}
 return ($rows -join "`n")
}
$before=IdentityHashes
$bytes=[IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'release.zip'))
$sha=[Security.Cryptography.SHA256]::Create()
try {$digest=([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLower()}finally{$sha.Dispose()}
if($bytes.Length -gt 3MB -or $digest -cne 'EXPECTED'){throw 'Transfer digest mismatch'}
$tmp=Join-Path $env:TEMP ('lazytunnel-update-'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $tmp|Out-Null
try {
 $zip=Join-Path $tmp 'release.zip';[IO.File]::WriteAllBytes($zip,$bytes)
 Add-Type -AssemblyName System.IO.Compression.FileSystem
 $archive=[IO.Compression.ZipFile]::OpenRead($zip)
 try {
  foreach($entry in $archive.Entries){
   if($entry.FullName.StartsWith('/') -or $entry.FullName.Contains('..') -or $entry.FullName.Contains(':') -or $entry.Length -gt 2MB){throw 'Invalid release member'}
  }
 } finally {$archive.Dispose()}
 $root=Join-Path $tmp 'source';[IO.Compression.ZipFile]::ExtractToDirectory($zip,$root)
 # Explicitly execute the verified candidate: legacy Windows installers copied in place.
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\lazytunnel.ps1') update -Source (Join-Path $root 'scripts')
 if($LASTEXITCODE){throw 'Candidate install failed'}
 $base=Join-Path $env:USERPROFILE '.local\share\lazytunnel\client'
 $revision=[IO.File]::ReadAllText((Join-Path $base 'current.txt')).Trim()
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $base 'code\lazytunnel.ps1') update -Source (Join-Path $base ('releases\'+$revision))
 if($LASTEXITCODE){throw 'Self-update check failed'}
 & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $base 'code\lazytunnel.ps1') status
 if($LASTEXITCODE){throw 'Updated CLI failed'}
 if($before -cne (IdentityHashes)){throw 'Identity changed unexpectedly'}
 [ordered]@{updated=$true;release=$revision;identity_unchanged=$true;self_update_verified=$true}|ConvertTo-Json -Compress
} finally {Remove-Item -LiteralPath $tmp -Recurse -Force}
'''


def package(source):
    metadata=json.loads((source/'package.json').read_text())
    names={'package.json'}
    for pattern in metadata['files']:
        for path in source.glob(pattern):
            if path.is_file() and not path.is_symlink():names.add(path.relative_to(source).as_posix())
    data=io.BytesIO()
    with zipfile.ZipFile(data,'w',zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names):
            if any(part in ('private','runtime','node_modules') for part in Path(name).parts):raise ValueError('Private release member')
            entry=zipfile.ZipInfo(name, date_time=(2020,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,(source/name).read_bytes())
    return data.getvalue()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',help='enrolled alias, such as lazy-alpha')
    parser.add_argument('--platform',choices=['posix','windows'],required=True)
    parser.add_argument('--python',default='/usr/bin/python3',help='verified remote interpreter; Mac may use /usr/local/bin/python3')
    parser.add_argument('--source',type=Path,default=ROOT)
    parser.add_argument('--ssh-config',type=Path,default=Path.home()/'.config/lazytunnel-fleet/ssh_config')
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'lazy-[a-z0-9][a-z0-9-]{0,47}',args.target):parser.error('Use an explicit lazy-DEVICE endpoint alias')
    raw=package(args.source);digest=hashlib.sha256(raw).hexdigest()
    print(json.dumps({'target':args.target,'archive_bytes':len(raw),'sha256':digest,'apply':args.apply}),flush=True)
    if not args.apply:return
    options=['-F',str(args.ssh_config),'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
             '-o','ConnectTimeout=10','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3']
    ssh=['ssh',*options,args.target]
    if args.platform=='windows':
        # Windows OpenSSH/PowerShell console stdin can wait indefinitely for EOF.
        # Use native SFTP, then a short script path; no large command-line payload.
        def ps(code,**kwargs):
            command='powershell.exe -NoLogo -NoProfile -EncodedCommand '+base64.b64encode(code.encode('utf-16le')).decode()
            return subprocess.run(ssh+[command],timeout=45,**kwargs)
        setup="$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';$p=Join-Path $env:TEMP ('lazytunnel-transfer-'+[guid]::NewGuid().ToString('N'));New-Item -ItemType Directory $p|Out-Null;$p.Replace('\\','/')|ConvertTo-Json -Compress"
        remote=json.loads(ps(setup,capture_output=True,text=True,check=True).stdout)
        if not re.fullmatch(r'[A-Za-z]:/[^"\x00-\x1f$`&;<>|]+/lazytunnel-transfer-[a-f0-9]{32}',remote):
            raise ValueError('Unexpected Windows staging path')
        with tempfile.TemporaryDirectory(prefix='lazytunnel-send-') as tmp:
            local=Path(tmp)
            (local/'release.zip').write_bytes(raw)
            (local/'update.ps1').write_text(WINDOWS.replace('EXPECTED',digest))
            subprocess.run(['scp',*options,str(local/'release.zip'),str(local/'update.ps1'),
                            args.target+':'+remote+'/'],check=True,timeout=90)
        command='powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "'+remote+'/update.ps1"'
        p=subprocess.run(ssh+[command],timeout=180)
        ps("$ErrorActionPreference='Stop';Remove-Item -LiteralPath '"+remote.replace("'","''")+"' -Recurse -Force",check=True,capture_output=True)
    else:
        command=shlex.join([args.python,'-c',POSIX.replace('EXPECTED',repr(digest))])
        p=subprocess.run(ssh+[command],input=raw,timeout=180)
    raise SystemExit(p.returncode)


if __name__=='__main__':main()
