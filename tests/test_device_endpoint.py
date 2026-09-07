import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/device-ssh-endpoint.py'
spec = importlib.util.spec_from_file_location('device_endpoint', SCRIPT)
endpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(endpoint)

# Public synthetic test key; no corresponding private key is distributed.
KEY = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'


class DeviceEndpointTests(unittest.TestCase):
    def test_restricted_key_is_not_readded_without_restrictions(self):
        old = 'restrict,command="hostname" ' + KEY + ' existing\n'
        self.assertEqual(endpoint.merge_keys(old, [KEY]), old)

    def test_append_preserves_final_comment_and_is_idempotent(self):
        old = '# keep this comment without newline'
        new = endpoint.merge_keys(old, [KEY])
        self.assertTrue(new.startswith(old + '\nssh-ed25519 '))
        self.assertEqual(endpoint.merge_keys(new, [KEY]), new)

    def test_rejects_private_material_and_authorized_key_options(self):
        for value in ['-----BEGIN OPENSSH PRIVATE KEY-----', 'restrict ' + KEY,
                      'ssh-ed25519 broken-base64']:
            with self.assertRaises(ValueError):
                endpoint.public_key(value)

    def test_identical_write_keeps_inode_and_backup_preserves_original(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'config'
            endpoint.write(p, 'Host old\n')
            inode = p.stat().st_ino
            endpoint.write(p, 'Host old\n')
            self.assertEqual(inode, p.stat().st_ino)
            endpoint.write(p, 'Host new\n')
            backups = list((p.parent / 'device-ssh-backups').iterdir())
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), 'Host old\n')
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)

    def test_symlink_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / 'target'
            target.write_text('original')
            p = Path(d) / 'config'
            p.symlink_to(target)
            with self.assertRaises(RuntimeError):
                endpoint.write(p, 'changed')
            self.assertEqual(target.read_text(), 'original')


if __name__ == '__main__':
    unittest.main()
