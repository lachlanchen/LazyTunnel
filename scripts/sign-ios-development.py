#!/usr/bin/env python3
"""Sign a built iOS app for devices in an existing private development profile.

Run on macOS. The resulting IPA contains provisioning/device information and
belongs in private distribution, not a public GitHub release. No Apple account
credentials are required and no keychain settings are changed by this script.
"""
import argparse
from datetime import datetime
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile


def sign(app, profile, identity, output):
    if sys.platform != 'darwin':
        raise ValueError('Run signing on macOS with Xcode installed')
    app, profile, output = app.resolve(), profile.resolve(), output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Choose a new output path; existing packages are preserved')
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    bundle = info['CFBundleIdentifier']
    if bundle != 'art.lazying.lazytunnel':
        raise ValueError('Unexpected application identifier')
    raw = subprocess.check_output(['security', 'cms', '-D', '-i', str(profile)], stderr=subprocess.DEVNULL)
    provisioning = plistlib.loads(raw)
    allowed = provisioning['Entitlements']
    if not allowed.get('get-task-allow') or not provisioning.get('ProvisionedDevices'):
        raise ValueError('This helper accepts development profiles with registered devices only')
    if provisioning['ExpirationDate'] <= datetime.utcnow():
        raise ValueError('Provisioning profile has expired')
    application_id = provisioning['ApplicationIdentifierPrefix'][0] + '.' + bundle
    pattern = allowed['application-identifier']
    if not (pattern == application_id or pattern.endswith('.*') and application_id.startswith(pattern[:-1])):
        raise ValueError('The profile does not authorize this application identifier')
    groups = allowed.get('keychain-access-groups', [])
    if not any(g == application_id or g.endswith('.*') and application_id.startswith(g[:-1]) for g in groups):
        raise ValueError('The profile does not authorize the app keychain group')
    entitlements = {k: v for k, v in allowed.items() if k in ('get-task-allow', 'com.apple.developer.team-identifier')}
    entitlements.update({'application-identifier': application_id, 'keychain-access-groups': [application_id]})
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ios-sign-', dir=output.parent) as temporary:
        staging = Path(temporary)
        payload = staging / 'Payload'
        target = payload / 'LazyTunnel.app'
        shutil.copytree(app, target, symlinks=True)
        shutil.copyfile(profile, target / 'embedded.mobileprovision')
        entitlement_file = staging / 'entitlements.plist'
        entitlement_file.write_bytes(plistlib.dumps(entitlements))
        frameworks = target / 'Frameworks'
        for item in sorted([*frameworks.glob('*.framework'), *frameworks.glob('*.dylib')]):
            subprocess.run(['codesign', '--force', '--sign', identity, '--timestamp=none', str(item)], check=True)
        subprocess.run(['codesign', '--force', '--sign', identity, '--timestamp=none', '--entitlements', str(entitlement_file), str(target)], check=True)
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(target)], check=True)
        archive = staging / 'signed.ipa'
        subprocess.run(['ditto', '-c', '-k', '--keepParent', str(payload), str(archive)], check=True)
        archive.chmod(0o600)
        # Link only if the destination remains unused; never replace a package.
        os.link(archive, output)
    print('Signed development IPA:', output)
    print('Keep this package private. It installs only on devices authorized by its profile.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app', type=Path, required=True)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--identity', required=True, help='Signing identity SHA-1 from security find-identity')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sign(args.app, args.profile, args.identity, args.output)
