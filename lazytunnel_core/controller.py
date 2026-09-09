"""UI-independent inventory, checks and forwarding controller."""
import concurrent.futures
import contextlib
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import signal
import subprocess
import sys
import tempfile
import threading
import time
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent
STATE = Path.home() / '.config/lazytunnel-fleet'
DEFAULT_PORT = 17766
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


class Controller:
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
        if d['local_port'] in (self.port, 17765, 17766):
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
            account=json.loads((self.state/'bundle.json').read_text())['peer'].get('account','default')
            return {'account': account, 'devices': peers, 'viewers': views, 'checking': self.checking,
                    'managed_forwards': sys.platform == 'linux', 'version': 1}
