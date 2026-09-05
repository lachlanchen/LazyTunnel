import base64
import copy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import lazytunnel as lt


def key(n):
    raw = b'\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20' + bytes([n]) * 32
    return 'ssh-ed25519 ' + base64.b64encode(raw).decode()


def fixture():
    return {"version": 1, "edge": {"host": "edge.example.invalid", "port": 2222, "host_key": key(1)},
            "peers": [{"name": name, "user": "alice", "home": "/home/alice", "ssh_port": 22,
                       "relay_port": 23000+i, "host_key": key(2+i), "tunnel_key": key(10+3*i),
                       "jump_key": key(11+3*i), "login_key": key(12+3*i)}
                      for i, name in enumerate(["alpha", "beta"])]}


class RenderTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(lt.validate(fixture())["version"], 1)

    def test_injections_and_invalid_values(self):
        for field, value in [("name", "x\nHost *"), ("user", "root"), ("home", "/home/a b"),
                             ("home", "/home/../root"), ("home", "/home/%u"),
                             ("relay_port", True), ("relay_port", 22), ("ssh_port", 0),
                             ("tunnel_key", "ssh-ed25519 not-a-key")]:
            with self.subTest(field=field, value=value):
                c = fixture(); c["peers"][0][field] = value
                with self.assertRaises(ValueError): lt.validate(c)

    def test_unknown_credentials_field_rejected(self):
        c = fixture(); c["password"] = "not-real"
        with self.assertRaises(ValueError): lt.validate(c)

    def test_host_identity_collisions(self):
        c=fixture();c['peers'][1]['host_key']=c['peers'][0]['tunnel_key']
        with self.assertRaises(ValueError):lt.validate(c)
        c=fixture();c['peers'][1]['host_key']=c['peers'][0]['host_key']
        with self.assertRaises(ValueError):lt.validate(c)

    def test_duplicate_ports_names_and_keys_rejected(self):
        for f in ["name", "relay_port", "tunnel_key", "jump_key", "login_key"]:
            c = fixture(); c["peers"][1][f] = c["peers"][0][f]
            with self.subTest(field=f), self.assertRaises(ValueError): lt.validate(c)

    def test_relay_identity_separation(self):
        c = fixture(); c["peers"][0]["jump_key"] = c["peers"][0]["tunnel_key"]
        with self.assertRaises(ValueError): lt.validate(c)

    def test_edge_restrictions(self):
        f = lt.edge_files(lt.validate(fixture()))
        text = f['60-lazytunnel.conf']
        for expected in ['GatewayPorts no', 'MaxSessions 0', 'AllowTcpForwarding remote',
                         'AllowTcpForwarding local', 'PermitOpen none', 'PermitListen none']:
            self.assertIn(expected, text)
        self.assertIn('permitlisten="127.0.0.1:23000"', f['keys/lt-tun-alpha'])
        self.assertIn('permitopen="127.0.0.1:23001"', f['keys/lt-hop-alpha'])
        self.assertNotIn('23000', f['keys/lt-hop-alpha'])
        self.assertNotIn('0.0.0.0', text)
        self.assertNotIn('Port 2222', text)

    def test_worker_identity_and_supervision(self):
        f = lt.worker_files(lt.validate(fixture()), 'alpha')
        self.assertIn('StrictHostKeyChecking yes', f['ssh_config'])
        self.assertIn('RemoteForward 127.0.0.1:23000 127.0.0.1:22', f['ssh_config'])
        self.assertIn('RestartSec=15', f['lazytunnel.service'])
        self.assertIn('-F /home/alice/.config/lazytunnel/ssh_config -W %h:%p', f['ssh_config'])
        self.assertNotIn(key(12), f['authorized_keys.append'])
        self.assertIn(key(15), f['authorized_keys.append'])
        self.assertNotIn('Host uu-', f['ssh_config'])

    def test_ssh_parses_candidate_without_connecting(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'ssh_config'
            path.write_text(lt.worker_files(lt.validate(fixture()), 'alpha')['ssh_config'])
            r = subprocess.run(['/usr/bin/ssh', '-G', '-F', str(path), 'beta'], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('port 23001\n', r.stdout)
            self.assertIn('hostname 127.0.0.1\n', r.stdout)

    def test_bundle_owner_only_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'candidate'
            lt.write_bundle(p, {'keys/a': 'public\n'})
            self.assertEqual((p/'keys/a').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(ValueError): lt.write_bundle(p, {'keys/a': 'replace'})
            self.assertEqual((p/'keys/a').read_text(), 'public\n')

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); (root/'link').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError): lt.write_bundle(root/'link'/'out', {'a': 'bad'})

    def test_unknown_peer_rejected(self):
        with self.assertRaises(ValueError): lt.worker_files(fixture(), 'missing')


if __name__ == '__main__': unittest.main()
