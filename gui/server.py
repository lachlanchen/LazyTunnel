#!/usr/bin/env python3
"""Optional loopback console. Python stdlib; Linux systemd owns web forwards."""
import argparse
import concurrent.futures
import contextlib
import fcntl
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / '.config/lazytunnel-fleet'
DEFAULT_PORT = 17765
NAME = re.compile(r'[a-z0-9][a-z0-9-]{0,19}\Z')
ID = re.compile(r'[a-f0-9]{16}\Z')
MARKER = '# Managed by LazyTunnel GUI v1\n'


def atomic(path, value):
    if path.is_symlink():
        raise ValueError('Refusing a symlink configuration file')
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
        os.chmod(name, 0o600)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def private_dir(path):
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or path.stat().st_uid != os.getuid():
        raise ValueError('Private directory must be owned by this user')
    path.chmod(0o700)


def run(command, timeout=12):
    """A timed-out SSH probe must not leave its ProxyCommand running."""
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, start_new_session=True) as process:
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise ValueError('Connection timed out; existing sessions were preserved')
        return process.returncode, out.decode('utf-8', 'replace'), err.decode('utf-8', 'replace')


def devices(state):
    """Read existing enrolled aliases without exposing keys, bundles or edge IPs."""
    bundle = json.loads((state / 'bundle.json').read_text())
    result, block = {}, None
    for line in bundle['files']['ssh_config'].splitlines():
        parts = shlex.split(line, comments=True)
        if not parts:
            continue
        if parts[0].lower() == 'host':
            aliases = [p[5:] for p in parts[1:] if p.startswith('lazy-') and p[5:] in bundle['aliases']]
            block = {'aliases': aliases} if aliases else None
        elif block is not None:
            if parts[0].lower() == 'user':
                block['user'] = parts[1]
            if parts[0].lower() == 'hostkeyalias' and parts[1].startswith('lazy-fleet-'):
                name = parts[1][11:]
                if not NAME.fullmatch(name):
                    raise ValueError('Invalid enrolled name')
                block['name'] = name
                block['local'] = name == bundle['peer']['name']
                result[name] = block
    return list(result.values())


class Console:
    def __init__(self, state=STATE, port=DEFAULT_PORT):
        self.state, self.port = Path(state), port
        self.folder = self.state / 'gui'
        private_dir(self.folder)
        self.lock = threading.RLock()
        self.probes = {}
        self.checking = False
        self.last_check = 0
        self.pool = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.cache, self.cache_at = {}, 0
        self.code()

    def code(self):
        path = self.folder / 'access-code'
        if path.is_symlink():
            raise ValueError('Refusing a symlink access code')
        if not path.exists():
            # Exclusive creation also protects concurrent CLI launches.
            try:
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'w') as stream:
                    stream.write(secrets.token_urlsafe(32) + '\n')
            except FileExistsError:
                pass
        if path.stat().st_uid != os.getuid() or path.stat().st_mode & 0o077:
            raise ValueError('Access code must be owned by this user with mode 0600')
        value = path.read_text().strip()
        if len(value) < 40:
            raise ValueError('Invalid access code; rotate it from the local CLI')
        return value

    def entries(self):
        path = self.folder / 'forwards.json'
        if path.is_symlink():
            raise ValueError('Refusing a symlink profile file')
        return json.loads(path.read_text()) if path.exists() else []

    def save(self, rows):
        atomic(self.folder / 'forwards.json', json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
        self.cache_at = 0

    def validate(self, data):
        allowed = {'name', 'device', 'remote_port', 'local_port', 'path', 'mode'}
        if not isinstance(data, dict) or set(data) != allowed:
            raise ValueError('Provide a name, enrolled device, two ports, path and mode')
        d = dict(data)
        if not isinstance(d['name'], str) or not 1 <= len(d['name'].strip()) <= 64 or any(ord(c) < 32 for c in d['name']):
            raise ValueError('Use a short printable name')
        d['name'] = d['name'].strip()
        peers = {p['name']: p for p in devices(self.state)}
        if not isinstance(d['device'], str) or d['device'] not in peers:
            raise ValueError('Select an enrolled device')
        if d['mode'] not in ('forward', 'local'):
            raise ValueError('Unknown connection mode')
        for key, minimum in (('remote_port', 1), ('local_port', 1024)):
            if type(d[key]) is not int or not minimum <= d[key] <= 65535:
                raise ValueError('Invalid port')
        if d['local_port'] == self.port:
            raise ValueError('That port belongs to this console')
        path = d['path']
        if not isinstance(path, str) or not path.startswith('/') or len(path) > 1024:
            raise ValueError('Use a relative viewer path, for example /vnc.html?resize=scale')
        decoded = unquote(path)
        if decoded.startswith('//') or '\\' in decoded or any(ord(c) < 32 or ord(c) == 127 for c in decoded):
            raise ValueError('Invalid viewer path')
        if d['mode'] == 'local' and (not peers[d['device']]['local'] or d['local_port'] != d['remote_port']):
            raise ValueError('An existing local viewer must use this computer and the same port')
        return d

    def add(self, data):
        with self.lock:
            d = self.validate(data)
            rows = self.entries()
            for row in rows:
                if {k: v for k, v in row.items() if k != 'id'} == d:
                    return row
                # Local bookmarks may share a port with different viewer paths.
                if row['local_port'] == d['local_port'] and (row['mode'] != 'local' or d['mode'] != 'local'):
                    raise ValueError('A saved forward already uses that local port')
            if len(rows) >= 64:
                raise ValueError('Maximum 64 saved viewers')
            d['id'] = secrets.token_hex(8)
            rows.append(d)
            self.save(rows)
            return d

    def get(self, ident):
        if not isinstance(ident, str) or not ID.fullmatch(ident):
            raise ValueError('Invalid viewer ID')
        for row in self.entries():
            if row['id'] == ident:
                if row.get('mode') not in ('forward', 'local'):
                    raise ValueError('Invalid saved viewer mode')
                return row
        raise ValueError('Viewer not found')

    def service(self, row):
        return 'lazytunnel-web-gui-' + row['id'] + '.service'

    def unit_path(self, row):
        return Path.home() / '.config/systemd/user' / self.service(row)

    def verify_owned(self, row):
        path = self.unit_path(row)
        if path.exists() or path.is_symlink():
            if path.is_symlink() or not path.read_text().startswith('# Managed by LazyTunnel lazy-web v1\n'):
                raise ValueError('Refusing an unowned service')

    def action(self, ident, action):
        with self.lock:
            row = self.get(ident)
            if row['mode'] == 'local':
                if action != 'remove':
                    raise ValueError('An existing viewer is managed by its original application')
            else:
                if sys.platform != 'linux':
                    raise ValueError('Managed forwards currently require Linux systemd; use the web CLI on macOS/Windows')
                self.verify_owned(row)
                helper = ROOT.parent / 'scripts/lazy-web'
                if action == 'start':
                    # A previously enrolled device can still have its old
                    # forward stopped/removed; only new starts require it now.
                    self.validate({k: v for k, v in row.items() if k != 'id'})
                    cmd = [sys.executable, str(helper), 'start', 'gui-' + ident, 'lazy-' + row['device'],
                           str(row['remote_port']), '--local-port', str(row['local_port']),
                           '--ssh-config', str(self.state / 'ssh_config')]
                elif action == 'stop':
                    cmd = [sys.executable, str(helper), 'stop', 'gui-' + ident]
                elif action == 'remove':
                    # Never stop an active connection merely to remove a card.
                    _, active, _ = run(['systemctl', '--user', 'is-active', self.service(row)])
                    _, enabled, _ = run(['systemctl', '--user', 'is-enabled', self.service(row)])
                    if active.strip() not in ('inactive', 'failed', 'unknown') or enabled.strip() == 'enabled':
                        raise ValueError('Stop this forward before removing its saved card')
                    cmd = None
                else:
                    raise ValueError('Unknown action')
                if cmd:
                    rc, out, err = run(cmd, timeout=25)
                    if rc:
                        # Only this bounded owned helper's diagnostics, never journal contents.
                        raise ValueError((err or out)[-700:].strip())
            if action == 'remove':
                self.save([r for r in self.entries() if r['id'] != ident])
            self.cache_at = 0

    def check(self, name=None):
        with self.lock:
            if self.checking or time.monotonic() - self.last_check < 15:
                return
            peers = devices(self.state)
            if name is not None:
                peers = [p for p in peers if p['name'] == name]
                if not peers:
                    raise ValueError('Unknown device')
            if len(peers) > 64:
                raise ValueError('Maximum 64 devices per check')
            self.checking = True
            self.last_check = time.monotonic()
        def probe(peer):
            started = time.monotonic()
            try:
                rc, out, err = run(['/usr/bin/ssh', '-F', str(self.state / 'ssh_config'),
                                    '-n', '-T', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=6',
                                    '-o', 'ConnectionAttempts=1', '-o', 'StrictHostKeyChecking=yes',
                                    '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no',
                                    'lazy-' + peer['name'], 'hostname'], timeout=10)
                status = 'reachable' if rc == 0 else 'unreachable'
                detail = 'SSH authenticated' if rc == 0 else 'SSH did not connect; check the client or network'
            except (OSError, ValueError):
                status, detail = 'unreachable', 'SSH timed out or could not start'
            with self.lock:
                self.probes[peer['name']] = {'status': status, 'detail': detail,
                    'ms': round((time.monotonic() - started) * 1000), 'checked_at': int(time.time())}
        def batch():
            try:
                list(self.pool.map(probe, peers))
            finally:
                with self.lock:
                    self.checking = False
        threading.Thread(target=batch, daemon=True).start()

    def snapshot(self):
        with self.lock:
            peers = [dict(p, probe=self.probes.get(p['name'])) for p in devices(self.state)]
            rows = self.entries()
            if time.monotonic() - self.cache_at > 3:
                states = {}
                owned = [self.service(r) for r in rows if r['mode'] == 'forward']
                if owned and sys.platform == 'linux':
                    rc, out, _ = run(['systemctl', '--user', 'show', '--property=Id,ActiveState,SubState', *owned], timeout=5)
                    for block in out.split('\n\n'):
                        fields = dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
                        if 'Id' in fields:
                            states[fields['Id']] = fields.get('ActiveState', 'unknown')
                self.cache, self.cache_at = states, time.monotonic()
            views = []
            for row in rows:
                view = dict(row)
                view['unit'] = self.service(row) if row['mode'] == 'forward' else None
                view['status'] = self.cache.get(view['unit'], 'inactive') if view['unit'] else 'existing'
                view['url'] = 'http://127.0.0.1:' + str(row['local_port']) + row['path']
                views.append(view)
            return {'devices': peers, 'viewers': views, 'checking': self.checking,
                    'managed_forwards': sys.platform == 'linux', 'version': 1}


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
                return self.reply(200, {'service': 'lazytunnel-gui', 'version': 1})
            if self.path.startswith('/api/'):
                if not self.authorized():
                    return
                if self.path == '/api/state':
                    return self.reply(200, self.server.console.snapshot())
                return self.reply(404, {'error': 'Unknown API'})
            assets = {'/': ('index.html', 'text/html; charset=utf-8'), '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/style.css': ('style.css', 'text/css; charset=utf-8'), '/icon.svg': ('icon.svg', 'image/svg+xml')}
            if self.path in assets:
                path, content = assets[self.path]
                return self.reply(200, (ROOT / path).read_bytes(), content)
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


def gui_unit(port):
    # Stable pointer permits immutable client-code updates; no carrier restart.
    script = Path.home() / '.local/share/lazytunnel/client/current/gui/server.py'
    if not script.is_file():
        raise ValueError('Run lazytunnel update --source /path/to/LazyTunnel first')
    import importlib.util
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader('lazy_web', str(ROOT.parent / 'scripts/lazy-web'))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    helper = importlib.util.module_from_spec(spec)
    loader.exec_module(helper)
    return MARKER + '[Unit]\nDescription=LazyTunnel optional local console\n\n[Service]\n' + \
        'ExecStart=' + ' '.join(helper.unit_argument(v) for v in [sys.executable, str(script), 'serve', '--port', str(port)]) + \
        '\nRestart=on-failure\nRestartSec=5\nUMask=0077\nNoNewPrivileges=true\nPrivateTmp=true\n\n[Install]\nWantedBy=default.target\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', nargs='?', choices=['open', 'serve', 'install', 'stop', 'status', 'code', 'rotate-code'], default='open')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise ValueError('Invalid console port')
    os.umask(0o077)
    console = Console(port=args.port)
    if args.action == 'code':
        print(console.code())
        return
    if args.action == 'rotate-code':
        atomic(console.folder / 'access-code', secrets.token_urlsafe(32) + '\n')
        print('Access code rotated. Run lazytunnel gui code and unlock your browser again.')
        return
    unit = Path.home() / '.config/systemd/user/lazytunnel-gui.service'
    if args.action in ('install', 'stop', 'status'):
        if sys.platform != 'linux':
            raise ValueError('Service management currently requires Linux; use serve for a foreground console')
        if args.action != 'status' and (unit.exists() or unit.is_symlink()):
            if unit.is_symlink() or not unit.read_text().startswith(MARKER):
                raise ValueError('Refusing an unowned console service')
        if args.action == 'install':
            expected = gui_unit(args.port)
            unit.parent.mkdir(parents=True, exist_ok=True)
            if unit.exists() and unit.read_text() != expected:
                raise ValueError('Existing console settings differ; stop and review the unit before migration')
            if not unit.exists():
                with socket.socket() as sock:
                    sock.bind(('127.0.0.1', args.port))
                atomic(unit, expected)
            subprocess.run(['systemctl', '--user', 'daemon-reload'], check=True)
            subprocess.run(['systemctl', '--user', 'enable', '--now', unit.name], check=True)
            # systemctl may return before Python has bound its listener.
            import urllib.request
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            ready = False
            for _ in range(20):
                try:
                    with opener.open('http://127.0.0.1:' + str(args.port) + '/health', timeout=.5) as response:
                        ready = json.load(response).get('service') == 'lazytunnel-gui'
                    if ready:
                        break
                except (OSError, ValueError):
                    pass
                time.sleep(.25)
            if not ready:
                raise ValueError('Console did not become ready; inspect lazytunnel gui status')
            apps = Path.home() / '.local/share/applications'
            apps.mkdir(parents=True, exist_ok=True)
            desktop = apps / 'art.lazying.LazyTunnel.desktop'
            launcher = Path.home() / '.local/bin/lazytunnel'
            icon = Path.home() / '.local/share/lazytunnel/client/current/gui/icon.svg'
            if not desktop.exists() or desktop.read_text().startswith(MARKER):
                def quoted(text):
                    return '"' + str(text).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'
                atomic(desktop, MARKER + '[Desktop Entry]\nType=Application\nName=LazyTunnel\n' +
                       'Comment=Private SSH and desktop viewers\nExec=' + quoted(launcher) + ' gui --port ' + str(args.port) +
                       '\nIcon=' + str(icon) + '\nTerminal=false\nCategories=Network;RemoteAccess;\nKeywords=SSH;noVNC;Tunnel;Remote;\n')
            print('Console enabled. SSH carriers and existing desktop services unchanged.')
        elif args.action == 'stop':
            subprocess.run(['systemctl', '--user', 'disable', '--now', unit.name], check=True)
            print('Console stopped. Independent saved web forwards remain running.')
        else:
            subprocess.run(['systemctl', '--user', 'status', '--no-pager', unit.name], check=False)
        return
    url = 'http://127.0.0.1:' + str(args.port)
    if args.action == 'open':
        import urllib.request
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(url + '/health', timeout=2) as response:
                if json.load(response).get('service') != 'lazytunnel-gui':
                    raise ValueError('The port belongs to another application')
        except OSError:
            raise ValueError('Start the console with lazytunnel gui install, or lazytunnel gui serve')
        print(url + '\nFirst visit: run lazytunnel gui code and paste the code into the console.')
        webbrowser.open(url)
        return
    # One console process per identity, even if a second port was requested.
    lock = (console.folder / 'server.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise ValueError('This client already has a running console')
    server = Server(('127.0.0.1', args.port), console)
    print('LazyTunnel console: ' + url, flush=True)
    print('Unlock using the output of: lazytunnel gui code', flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        server.server_close()
        console.pool.shutdown(wait=False, cancel_futures=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print('LazyTunnel GUI:', error, file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        pass
