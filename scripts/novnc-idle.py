#!/usr/bin/env python3
"""Prepare a separate noVNC web root with a client-side idle disconnect policy."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile

ASSETS = Path(__file__).resolve().parents[1] / 'viewer'
MARKER = 'LazyTunnel noVNC idle overlay v1\n'


def install(source, output):
    source = source.resolve()
    output = output.absolute()
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Use a separate user-owned output directory')
    if output.is_symlink():
        raise ValueError('Refusing symlink output directory')
    marker = output / '.lazytunnel-overlay'
    if output.exists() and (not marker.is_file() or marker.read_text() != MARKER):
        raise ValueError('Refusing an unowned output directory')
    html = (source / 'vnc.html').read_text()
    ui = (source / 'app/ui.js').read_text()
    if '</head>' not in html or '</body>' not in html or not all(
        s in ui for s in ['inhibitReconnect', 'reconnectPassword', 'disconnect()', 'connect(']
    ):
        raise ValueError('Unsupported noVNC UI: use the full upstream vnc.html UI')
    output.mkdir(parents=True, mode=0o700, exist_ok=True)
    marker.write_text(MARKER)
    for child in source.iterdir():
        if child.name in ('vnc.html', '.lazytunnel-overlay') or child.name in {p.name for p in ASSETS.iterdir()}:
            continue
        target = output / child.name
        if target.is_symlink() and target.resolve() == child.resolve():
            continue
        if target.exists() or target.is_symlink():
            raise ValueError('Conflicting overlay asset: ' + child.name)
        target.symlink_to(child.resolve(), target_is_directory=child.is_dir())
    assets = {name: (ASSETS/name).read_bytes() for name in ('idle-policy.mjs', 'novnc-idle.mjs', 'novnc-idle.css')}
    revision = hashlib.sha256(b''.join(assets.values())).hexdigest()[:12]
    html = html.replace('</head>', f'<link rel="stylesheet" href="novnc-idle.css?v={revision}">\n</head>')
    html = html.replace('</body>', f'<script type="module" src="novnc-idle.mjs?v={revision}"></script>\n</body>')
    assets['vnc.html'] = html.encode()
    for name, data in assets.items():
        target = output/name
        if target.is_symlink():
            raise ValueError('Refusing symlink managed asset: '+name)
        fd, tmp = tempfile.mkstemp(dir=output)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
            os.replace(tmp, target)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    return revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('/usr/share/novnc'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    print('noVNC idle overlay:', install(args.source, args.output))
    print('Point only the intended websockify --web at', args.output)
    print('Reload existing viewer tabs once. Hidden: 10s. Idle: 120s. Desktop/apps unchanged.')


if __name__ == '__main__':
    main()
