import importlib.machinery
import importlib.util
from pathlib import Path
import socket
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/lazy-web'
loader = importlib.machinery.SourceFileLoader('lazy_web', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
web = importlib.util.module_from_spec(spec)
loader.exec_module(web)


class WebTests(unittest.TestCase):
    def test_loopback_listener_and_remote_lan_target(self):
        with tempfile.NamedTemporaryFile() as config:
            command = web.ssh_command(config.name, 'beta', 16144, 80, '192.168.1.1')
            self.assertIn('127.0.0.1:16144:192.168.1.1:80', command)
            self.assertEqual(command[-1], 'beta')
            self.assertIn('StrictHostKeyChecking=yes', command)
            self.assertIn('ExitOnForwardFailure=yes', command)

    def test_ipv6_target_and_socks(self):
        with tempfile.NamedTemporaryFile() as config:
            self.assertIn('127.0.0.1:16144:[::1]:6144', web.ssh_command(config.name, 'beta', 16144, 6144, '::1'))
            command = web.ssh_command(config.name, 'beta', 1080)
            self.assertIn('-D', command)
            self.assertIn('127.0.0.1:1080', command)

    def test_reject_injection_and_public_listener(self):
        with tempfile.NamedTemporaryFile() as config:
            for peer, local, host in [('-oProxyCommand=bad', 8080, 'localhost'),
                                      ('beta', 80, 'localhost'), ('beta', 70000, 'localhost'),
                                      ('beta', 8080, 'host:22:evil'), ('beta', 8080, 'host\nMatch all')]:
                with self.subTest(peer=peer, local=local, host=host), self.assertRaises(ValueError):
                    web.ssh_command(config.name, peer, local, 80, host)
        for name in ('../x', '-x', 'x.service\n', 'x%u'):
            with self.assertRaises(ValueError):
                web.unit_name(name)

    def test_occupied_port_is_not_taken_over(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen()
            with self.assertRaisesRegex(ValueError, 'occupied'):
                web.check_port(listener.getsockname()[1])
            self.assertGreater(listener.fileno(), 0)

    def test_service_escaping_and_ownership(self):
        text = web.render_unit('test', ['/usr/bin/ssh', '/home/a b/100%/$HOME/config'])
        self.assertTrue(text.startswith(web.MARKER))
        self.assertIn('"/home/a b/100%%/$$HOME/config"', text)
        self.assertIn('RestartSec=15', text)
        self.assertIn('Restart=always', text)
        self.assertNotIn('ExecStop=', text)
        with self.assertRaises(ValueError):
            web.render_unit('test', ['bad\nvalue'])
