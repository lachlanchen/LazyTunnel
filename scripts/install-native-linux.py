#!/usr/bin/env python3
"""Install a built Linux GUI per user, without changing the independent agent."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

MARKER = '# Managed by LazyTunnel native app v1\n'


def quoted(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def install(bundle):
    source = bundle.resolve()
    binary = source / 'lazytunnel_app'
    if not binary.is_file() or not (source / 'lib/libflutter_linux_gtk.so').is_file():
        raise ValueError('Select the complete Flutter Linux release bundle, not just the executable')
    files = sorted(p for p in source.rglob('*') if p.is_file())
    digest = hashlib.sha256()
    for path in files:
        if not path.resolve().is_relative_to(source):
            raise ValueError('Bundle contains a link outside its directory')
        digest.update(str(path.relative_to(source)).encode())
        with path.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
    version = digest.hexdigest()[:16]
    root = Path.home() / '.local/share/lazytunnel/native'
    root.mkdir(parents=True, exist_ok=True)
    if root.is_symlink():
        raise ValueError('Refusing a symlink installation directory')
    release = root / 'releases' / version
    release.parent.mkdir(exist_ok=True)
    if not release.exists():
        staging = Path(tempfile.mkdtemp(prefix='.stage-', dir=release.parent))
        try:
            shutil.copytree(source, staging, dirs_exist_ok=True, symlinks=True)
            (staging / '.lazytunnel-native').write_text(version + '\n')
            os.replace(staging, release)
        finally:
            if staging.exists():
                shutil.rmtree(staging)
    elif (release / '.lazytunnel-native').read_text().strip() != version:
        raise ValueError('Existing release is not owned by this installer')
    current = root / 'current'
    if current.exists() and not current.is_symlink():
        raise ValueError('Refusing to replace an unrelated installation')
    link = root / 'next'
    if link.exists() or link.is_symlink():
        raise ValueError('Another installation is staged')
    link.symlink_to(release)
    os.replace(link, current)
    bindir = Path.home() / '.local/bin'
    bindir.mkdir(parents=True, exist_ok=True)
    launcher = bindir / 'lazytunnel-app'
    if launcher.is_symlink() or (launcher.exists() and MARKER not in launcher.read_text()):
        raise ValueError('Refusing to replace an unrelated launcher')
    import shlex
    launcher.write_text('#!/bin/sh\n' + MARKER + 'exec ' + shlex.quote(str(current / 'lazytunnel_app')) + ' "$@"\n')
    launcher.chmod(0o755)
    icon = Path(__file__).resolve().parents[1] / 'gui/icon.svg'
    if icon.is_file():
        shutil.copyfile(icon, root / 'icon.svg')
    apps = Path.home() / '.local/share/applications'
    apps.mkdir(parents=True, exist_ok=True)
    desktop = apps / 'art.lazying.LazyTunnel.Native.desktop'
    if desktop.is_symlink() or (desktop.exists() and not desktop.read_text().startswith(MARKER)):
        raise ValueError('Refusing to replace an unrelated application entry')
    desktop.write_text(MARKER + '[Desktop Entry]\nType=Application\nName=LazyTunnel Native\n'
        'Comment=Private computers, SSH terminals and desktop viewers\nExec=' + quoted(launcher) + '\nIcon=' + str(root / 'icon.svg') +
        '\nTerminal=false\nCategories=Network;RemoteAccess;\nKeywords=SSH;noVNC;Tunnel;Remote;\n')
    if shutil.which('update-desktop-database'):
        subprocess.run(['update-desktop-database', str(apps)], check=False)
    print('Native GUI installed:', release)
    print('Open LazyTunnel Native in Applications, or run lazytunnel-app')
    print('The agent, SSH services, profiles and existing windows were preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    args = parser.parse_args()
    install(args.bundle)
