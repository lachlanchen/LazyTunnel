#!/usr/bin/env python3
"""Optional web adapter for the independent LazyTunnel agent."""
import argparse
import contextlib
import fcntl
import http.client
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import threading
import time
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lazytunnel_core.controller import Controller, STATE, atomic
from lazytunnel_core.http_api import Server as BoundedServer, Handler as BoundaryHandler

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 17765
AGENT_PORT = 17766
MARKER = '# Managed by LazyTunnel GUI v1\n'

class Server(BoundedServer):
    def __init__(self, address, agent_port=AGENT_PORT):
        self.agent_port = agent_port
        super().__init__(address, None)
        self.RequestHandlerClass = Handler

class Handler(BoundaryHandler):
    def proxy(self, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.agent_port, timeout=30)
        try:
            headers = {'Authorization': self.headers.get('Authorization', ''), 'Content-Type': 'application/json'}
            connection.request('GET' if body is None else 'POST', self.path, body=body, headers=headers)
            response = connection.getresponse()
            data = response.read(2 * 1024 * 1024 + 1)
            if len(data) > 2 * 1024 * 1024:
                raise ValueError('Agent response exceeded limit')
            self.reply(response.status, data)
        except (OSError, ValueError, http.client.HTTPException):
            self.reply(503, {'error': 'Agent unavailable. Start it with lazytunnel agent install.'})
        finally:
            connection.close()

    def do_GET(self):
        if not self.boundary():
            return
        if self.path == '/health':
            return self.reply(200, {'service': 'lazytunnel-gui', 'version': 2})
        if self.path == '/api/state':
            return self.proxy()
        assets = {'/': ('index.html','text/html; charset=utf-8'), '/app.js': ('app.js','text/javascript; charset=utf-8'),
                  '/style.css': ('style.css','text/css; charset=utf-8'), '/icon.svg': ('icon.svg','image/svg+xml')}
        if self.path in assets:
            name, mime = assets[self.path]
            return self.reply(200, (ROOT / name).read_bytes(), mime)
        self.reply(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.boundary():
            return
        if self.path not in ('/api/check','/api/viewers','/api/viewers/action'):
            return self.reply(404, {'error': 'Not found'})
        try:
            if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length', [])) != 1:
                raise ValueError('Bounded JSON required')
            size = int(self.headers.get('Content-Length','0'))
            if not 0 < size <= 8192:
                return self.reply(413, {'error': 'Request too large'})
            if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
                return self.reply(415, {'error': 'JSON required'})
            return self.proxy(self.rfile.read(size))
        except (ValueError, OSError):
            self.reply(400, {'error': 'Invalid request'})

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
    console = Controller(port=args.port)
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
            subprocess.run([sys.executable, str(ROOT.parent / 'lazytunnel_core/agent.py'), 'install'], check=True)
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
    server = Server(('127.0.0.1', args.port))
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
