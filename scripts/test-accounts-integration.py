#!/usr/bin/env python3
"""Exercise the account boundary in one disposable container, with no host ports."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--no-build',action='store_true');args=ap.parse_args()
repo=Path(__file__).resolve().parents[1]
image='lazytunnel-accounts-test:0.3'
with tempfile.TemporaryDirectory(prefix='lazytunnel-accounts-integration-') as directory:
    root=Path(directory)
    for name in ('lazytunnel.py','fleet.py','accounts.py','scripts/lazytunnel-server.py',
                 'scripts/fleet-install-edge.py','scripts/account-admin.py','scripts/account-command.py',
                 'tests/accounts_integration.py','tests/accounts.Dockerfile',
                 'package.json','bin/lazytunnel-client.mjs','lib/cli.mjs','lib/accounts.mjs'):
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(repo/name,target)
    if not args.no_build:
        subprocess.run(['docker','build','-t',image,'-f',str(root/'tests/accounts.Dockerfile'),str(root)],check=True)
    cid=subprocess.check_output(['docker','run','--detach','--rm','--network','none','--hostname','lazytunnel-accounts-test',
                                 '--add-host','lazytunnel-accounts-test:127.0.0.1','--label','lazytunnel.test=accounts',
                                 '--mount','type=bind,source='+str(root)+',target=/src,readonly',
                                 '--mount','type=bind,source='+os.path.realpath(shutil.which('node'))+',target=/usr/local/bin/node,readonly',image],text=True).strip()
    try:subprocess.run(['docker','exec',cid,'python3','/src/tests/accounts_integration.py'],check=True)
    except subprocess.CalledProcessError:
        subprocess.run(['docker','logs','--tail','40',cid],check=False)
        subprocess.run(['docker','exec',cid,'cat','/var/lib/lazytunnel-fleet/account-last-error.log'],check=False)
        raise
    finally:subprocess.run(['docker','stop','--time','5',cid],stdout=subprocess.DEVNULL,check=True)
