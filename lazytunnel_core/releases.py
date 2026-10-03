"""Immutable, validated POSIX code releases. Never changes a carrier or identity."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def file_digest(contents):
    digest = hashlib.sha256()
    for name in sorted(contents):
        data = contents[name]
        digest.update(name.encode() + b'\0' + str(len(data)).encode() + b'\0' + data)
    return digest.hexdigest()


def point(base, name, target):
    fd, tmp = tempfile.mkstemp(prefix='.' + name + '-', dir=base)
    os.close(fd)
    os.unlink(tmp)
    try:
        os.symlink(target, tmp)
        os.replace(tmp, base/name)
    finally:
        if os.path.lexists(tmp):
            os.unlink(tmp)


def install_release(source, base, names, entry):
    source, base = Path(source).resolve(), Path(base)
    contents = {name: (source/name).read_bytes() for name in names}
    # Validate every Python file before touching the active release.
    for name, data in contents.items():
        if name.endswith('.py') or name == 'scripts/lazy-web':
            compile(data, name, 'exec')
    digest = file_digest(contents)
    base.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (base/'.update.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        releases = base/'releases'
        releases.mkdir(exist_ok=True)
        release = releases/digest[:16]
        stage = Path(tempfile.mkdtemp(prefix='.candidate-', dir=releases))
        try:
            for name, data in contents.items():
                path = stage/name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                path.chmod(0o700)
            check = subprocess.run([sys.executable, str(stage/entry), '--help'],
                                   capture_output=True, timeout=20)
            if check.returncode:
                raise ValueError('Candidate CLI failed its launch check; current release retained')
            for cache in stage.rglob('__pycache__'):
                shutil.rmtree(cache)
            receipt = {'sha256': digest, 'entry': entry,
                       'files': {n: hashlib.sha256(b).hexdigest() for n,b in contents.items()}}
            (stage/'release.json').write_text(json.dumps(receipt, indent=2)+'\n')
            if release.exists():
                if release.is_symlink() or file_digest({n:(release/n).read_bytes() for n in names}) != digest:
                    raise ValueError('Existing release content differs; refusing overwrite')
            else:
                stage.rename(release)
            current = base/'current'
            if current.exists() and not current.is_symlink():
                raise ValueError('Current release must be a managed symlink')
            if current.is_symlink():
                old = current.resolve(strict=True)
                if old.parent != releases.resolve():
                    raise ValueError('Current release is outside the managed release directory')
                if old == release.resolve():
                    return release.name
                point(base, 'previous', old)
            point(base, 'current', release.resolve())
            return release.name
        finally:
            if stage.exists():
                shutil.rmtree(stage)
