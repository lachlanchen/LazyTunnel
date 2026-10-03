import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('peer_update', ROOT/'scripts/update-peer.py')
peer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(peer)


class PeerUpdateTests(unittest.TestCase):
    def test_allowlist_and_reproducible_transfer(self):
        raw = peer.package(ROOT)
        self.assertEqual(raw, peer.package(ROOT))
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            self.assertIn('lazytunnel_core/releases.py', archive.namelist())
            self.assertIn('viewer/novnc-idle.mjs', archive.namelist())
            self.assertFalse(any('/private/' in '/'+p for p in archive.namelist()))
        self.assertLess(len(raw), 256*1024)

    def test_legacy_installer_bypassed_and_self_update_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            state = home/'.config/lazytunnel-fleet'
            state.mkdir(parents=True)
            bundle = state/'bundle.json'
            bundle.write_text(json.dumps({'peer': {'name': 'test', 'user': 'test', 'platform': 'linux'}, 'aliases': []}))
            before = bundle.read_bytes()
            launcher = home/'.local/bin/lazytunnel'
            launcher.parent.mkdir(parents=True)
            # An old installer cannot copy new modules. It must not be invoked.
            launcher.write_text('#!/bin/sh\nexit 77\n')
            launcher.chmod(0o700)
            raw = peer.package(ROOT)
            code = peer.POSIX.replace('EXPECTED', repr(hashlib.sha256(raw).hexdigest()))
            result = subprocess.run([sys.executable, '-c', code], input=raw,
                                    env={**os.environ, 'HOME': str(home)}, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(bundle.read_bytes(), before)
            self.assertIn(b'"self_update_verified": true', result.stdout)
            current = home/'.local/share/lazytunnel/client/current'
            self.assertTrue((current/'lazytunnel_core/releases.py').is_file())
            self.assertTrue((current/'release.json').is_file())


if __name__ == '__main__':
    unittest.main()
