import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest

import test_gui as fixtures
from lazytunnel_core.http_api import Server as AgentServer

spec = importlib.util.spec_from_file_location('web_adapter', Path(__file__).resolve().parents[1] / 'gui/server.py')
web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(web)


class WebAdapterTests(unittest.TestCase):
    def setUp(self):
        fixtures.GuiTests.setUp(self)
        self.agent = AgentServer(('127.0.0.1', 0), self.console)
        self.web = web.Server(('127.0.0.1', 0), agent_port=self.agent.server_port)
        self.threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (self.agent, self.web)]
        for thread in self.threads:
            thread.start()

    def tearDown(self):
        for server in (self.web, self.agent):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join()
        fixtures.GuiTests.tearDown(self)

    def request(self, server, path, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=3)
        conn.request('GET', path, headers=headers or {})
        response = conn.getresponse()
        result = response.status, response.read()
        conn.close()
        return result

    def test_web_is_an_authenticated_proxy_and_static_adapter(self):
        self.assertEqual(self.request(self.web, '/')[0], 200)
        self.assertEqual(self.request(self.agent, '/')[0], 404)
        self.assertEqual(self.request(self.web, '/api/state')[0], 401)
        headers = {'Authorization':'Bearer ' + self.console.code()}
        status, body = self.request(self.web, '/api/state', headers)
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)['devices']), 2)
        self.assertEqual(self.request(self.web, '/api/state', dict(headers, Origin='https://foreign.invalid'))[0], 403)

    def test_agent_survives_web_shutdown(self):
        self.web.shutdown()
        self.web.server_close()
        status, body = self.request(self.agent, '/api/state', {'Authorization':'Bearer ' + self.console.code()})
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)['devices']), 2)

    def test_core_does_not_import_any_gui(self):
        package = Path(__file__).resolve().parents[1] / 'lazytunnel_core'
        for path in package.glob('*.py'):
            content = path.read_text()
            self.assertNotIn('from gui', content)
            self.assertNotIn('import gui', content)


if __name__ == '__main__':
    unittest.main()
