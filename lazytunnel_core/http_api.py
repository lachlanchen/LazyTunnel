"""Authenticated API with no browser assets or UI dependency."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import subprocess
import threading

class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    def __init__(self, address, console):
        self.console = console
        self.slots = threading.BoundedSemaphore(16)
        super().__init__(address, Handler)

    def process_request(self, request, client):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, client)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, client):
        try:
            super().process_request_thread(request, client)
        finally:
            self.slots.release()


class Handler(BaseHTTPRequestHandler):
    server_version = 'LazyTunnel'
    sys_version = ''
    def setup(self):
        super().setup()
        self.connection.settimeout(5)

    def log_message(self, *args):
        pass  # No request bodies, access codes, paths or private inventory in logs.

    def reply(self, code, body, content='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', content)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Content-Security-Policy', "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)

    def boundary(self):
        port = self.server.server_port
        hosts = {'127.0.0.1:' + str(port), 'localhost:' + str(port)}
        if len(self.headers.get_all('Host', [])) != 1 or self.headers.get('Host') not in hosts:
            self.reply(403, {'error': 'Invalid host'})
            return False
        origin = self.headers.get('Origin')
        if origin is not None and origin != 'http://' + self.headers.get('Host'):
            self.reply(403, {'error': 'Cross-origin request denied'})
            return False
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            self.reply(403, {'error': 'Cross-site request denied'})
            return False
        return True

    def authorized(self):
        token = self.headers.get('Authorization', '')
        if not hmac.compare_digest(token.encode(), ('Bearer ' + self.server.console.code()).encode()):
            self.reply(401, {'error': 'Unlock this console with your local access code'})
            return False
        return True

    def do_GET(self):
        try:
            if not self.boundary():
                return
            if self.path == '/health':
                return self.reply(200, {'service': 'lazytunnel-agent', 'version': 1})
            if self.path.startswith('/api/'):
                if not self.authorized():
                    return
                if self.path == '/api/state':
                    return self.reply(200, self.server.console.snapshot())
                return self.reply(404, {'error': 'Unknown API'})
            self.reply(404, {'error': 'Not found'})
        except (OSError, ValueError, KeyError, subprocess.SubprocessError):
            self.reply(503, {'error': 'Local client state unavailable; check lazytunnel status'})

    def do_POST(self):
        try:
            if not self.boundary() or not self.authorized():
                return
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                return self.reply(400, {'error': 'A bounded JSON body is required'})
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 8192:
                return self.reply(413, {'error': 'Request too large'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.reply(415, {'error': 'JSON required'})
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Expected an object')
            console = self.server.console
            if self.path == '/api/check':
                if set(data) - {'device'}:
                    raise ValueError('Unknown check fields')
                console.check(data.get('device'))
                return self.reply(202, {'ok': True})
            if self.path == '/api/viewers':
                return self.reply(200, console.add(data))
            if self.path == '/api/viewers/action':
                if set(data) != {'id', 'action'} or data['action'] not in ('start', 'stop', 'remove'):
                    raise ValueError('Invalid viewer action')
                console.action(data['id'], data['action'])
                return self.reply(200, {'ok': True})
            self.reply(404, {'error': 'Unknown API'})
        except (ValueError, TypeError, KeyError) as error:
            self.reply(400, {'error': str(error)[:700]})
        except (OSError, subprocess.SubprocessError):
            self.reply(503, {'error': 'Local operation failed; existing connections were preserved'})
