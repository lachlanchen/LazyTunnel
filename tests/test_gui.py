import concurrent.futures
import copy
import http.client
import importlib.util
import json
from pathlib import Path
import socket
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

from fleet import bundle, validate

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gui_server', ROOT / 'gui/server.py')
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name)
        c = json.loads((ROOT / 'examples/two-peers.json').read_text())
        for p in c['peers']:
            p['platform'] = 'linux'
        c['peers'][0]['aliases'] = ['first-computer']
        c['peers'][1]['name'] = '7090'
        self.name = c['peers'][0]['name']
        self.other = c['peers'][1]['name']
        b = bundle(validate(c), self.name)
        (self.state / 'bundle.json').write_text(json.dumps(b))
        (self.state / 'ssh_config').write_text(b['files']['ssh_config'])
        self.console = gui.Console(self.state)
        self.data = dict(name='Test viewer', device=self.other, remote_port=6080,
                         local_port=16080, path='/vnc.html?resize=scale', mode='forward')

    def tearDown(self):
        self.console.pool.shutdown(wait=True)
        self.temp.cleanup()

    def test_inventory_deduplicates_aliases_without_leaking_keys(self):
        ds = gui.devices(self.state)
        self.assertEqual(len(ds), 2)
        self.assertIn('first-computer', ds[0]['aliases'])
        self.assertTrue(ds[0]['local'])
        text = json.dumps(self.console.snapshot())
        self.assertNotIn('ssh-ed25519', text)
        self.assertNotIn('IdentityFile', text)
        self.assertNotIn('edge.example.invalid', text)

    def test_private_access_code_persists_and_rotation_takes_effect(self):
        first = self.console.code()
        self.assertGreaterEqual(len(first), 40)
        self.assertEqual(self.console.code(), first)
        path = self.console.folder / 'access-code'
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        gui.atomic(path, 'x' * 43)
        self.assertEqual(self.console.code(), 'x' * 43)
        path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.console.code()

    def test_save_idempotent_concurrent_and_unique_local_port(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            ids = list(pool.map(lambda _: self.console.add(self.data)['id'], range(10)))
        self.assertEqual(len(set(ids)), 1)
        self.assertEqual(len(self.console.entries()), 1)
        with self.assertRaises(ValueError):
            self.console.add(dict(self.data, remote_port=6000))

    def test_invalid_targets_and_paths_are_rejected(self):
        variants = [dict(device='-oProxyCommand=bad'), dict(mode='shell'), dict(remote_port=0),
                    dict(local_port=22), dict(local_port=17765), dict(remote_port=True),
                    dict(path='//evil.test'), dict(path='/%2fevil.test'), dict(path='/x%0ay'),
                    dict(path='/\\evil.test'), dict(path='javascript:alert(1)'), dict(command='rm'),
                    dict(name='bad\nname'), dict(device='first-computer')]
        for change in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.console.add(dict(self.data, **change))

    def test_existing_local_viewer_is_never_started_or_stopped(self):
        data = dict(self.data, mode='local', device=self.name, remote_port=16080)
        row = self.console.add(data)
        self.console.add(dict(data, path='/wecom', name='Another path'))
        with mock.patch.object(gui, 'run') as run:
            for action in ('start', 'stop'):
                with self.assertRaises(ValueError):
                    self.console.action(row['id'], action)
            self.console.action(row['id'], 'remove')
            run.assert_not_called()

    def test_cannot_remove_running_forward_or_touch_unowned_service(self):
        row = self.console.add(self.data)
        with mock.patch.object(self.console, 'verify_owned'), mock.patch.object(gui, 'run', return_value=(0, 'active', '')):
            with self.assertRaises(ValueError):
                self.console.action(row['id'], 'remove')
        path = self.state / 'unrelated.service'
        path.write_text('A service owned by another app')
        with mock.patch.object(self.console, 'unit_path', return_value=path), mock.patch.object(gui, 'run') as run:
            with self.assertRaises(ValueError):
                self.console.action(row['id'], 'stop')
            run.assert_not_called()

    def test_check_is_bounded_and_not_started_by_snapshot(self):
        with mock.patch.object(gui, 'run', return_value=(0, 'host\n', '')) as run:
            self.console.snapshot()
            run.assert_not_called()
            self.console.check()
            for _ in range(100):
                if not self.console.checking:
                    break
                time.sleep(.01)
            self.console.check()  # Rate limited; no second probe batch.
            self.assertEqual(run.call_count, 2)
            for call in run.call_args_list:
                self.assertEqual(call.args[0][-1], 'hostname')
            self.assertTrue(all(p['status'] == 'reachable' for p in self.console.probes.values()))

    def test_retired_device_forward_can_be_stopped_but_not_restarted(self):
        row = self.console.add(self.data)
        with mock.patch.object(gui, 'devices', return_value=[]), mock.patch.object(self.console, 'verify_owned'), mock.patch.object(gui, 'run', return_value=(0, '', '')) as run:
            self.console.action(row['id'], 'stop')
            self.assertEqual(run.call_count, 1)
            with self.assertRaises(ValueError):
                self.console.action(row['id'], 'start')

    def test_mac_can_remove_local_bookmark_without_systemd(self):
        row = self.console.add(dict(self.data, mode='local', device=self.name, remote_port=16080))
        with mock.patch.object(gui.sys, 'platform', 'darwin'), mock.patch.object(gui, 'run') as run:
            self.console.action(row['id'], 'remove')
            run.assert_not_called()

    def test_timed_out_process_group_is_terminated(self):
        import sys
        start = time.monotonic()
        with self.assertRaises(ValueError):
            gui.run([sys.executable, '-c', 'import time; time.sleep(10)'], timeout=.1)
        self.assertLess(time.monotonic() - start, 2)

    def test_updater_uses_new_release_installer_for_its_file_manifest(self):
        source = self.state / 'checkout'
        (source / 'scripts').mkdir(parents=True)
        (source / 'scripts/lazytunnel-client.py').write_text('print("new release installer invoked")\n')
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/lazytunnel-client.py'),
                                 'update', '--source', str(source)], capture_output=True, text=True, timeout=3)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('new release installer invoked', result.stdout)


class HttpTests(GuiTests):
    def setUp(self):
        super().setUp()
        self.server = gui.Server(('127.0.0.1', 0), self.console)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        super().tearDown()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=3)
        conn.request(method, path, body=body, headers=headers or {})
        response = conn.getresponse()
        result = response.status, response.read(), dict(response.getheaders())
        conn.close()
        return result

    def auth(self):
        return {'Authorization': 'Bearer ' + self.console.code(), 'Content-Type': 'application/json'}

    def test_api_requires_code_and_rejects_cross_origin_and_rebinding(self):
        self.assertEqual(self.request('GET', '/api/state')[0], 401)
        self.assertEqual(self.request('GET', '/api/state', headers=self.auth())[0], 200)
        for extra in ({'Origin':'https://evil.invalid'}, {'Host':'evil.invalid:'+str(self.port)}, {'Sec-Fetch-Site':'cross-site'}):
            self.assertEqual(self.request('GET', '/api/state', headers=dict(self.auth(), **extra))[0], 403)
        gui.atomic(self.console.folder / 'access-code', 'x' * 43)
        self.assertEqual(self.request('GET', '/api/state', headers={'Authorization':'Bearer old-code'})[0], 401)

    def test_static_allowlist_and_security_headers(self):
        status, body, headers = self.request('GET', '/')
        self.assertEqual(status, 200)
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
        for path in ('/../server.py', '/server.py', '/access-code', '/api/state?token=abc', '/.config/lazytunnel-fleet/bundle.json'):
            self.assertEqual(self.request('GET', path, headers=self.auth())[0], 404)

    def test_json_only_size_limit_and_no_shell_api(self):
        self.assertEqual(self.request('POST', '/api/viewers', json.dumps(self.data), self.auth())[0], 200)
        self.assertEqual(self.request('POST', '/api/viewers', 'x' * 8193, self.auth())[0], 413)
        self.assertEqual(self.request('POST', '/api/viewers', '{}', dict(self.auth(), **{'Content-Type':'text/plain'}))[0], 415)
        self.assertEqual(self.request('POST', '/api/shell', '{}', self.auth())[0], 404)
        self.assertEqual(self.request('POST', '/api/check', '{"command":"bad"}', self.auth())[0], 400)


if __name__ == '__main__':
    unittest.main()
