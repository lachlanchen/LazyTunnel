#!/usr/bin/env python3
"""Optional browser integration test: real noVNC + disposable fake RFB desktop.

Needs system noVNC/websockify and Python Playwright with Chromium. Does not
connect to any real desktop or use a personal browser profile.
"""
import importlib.util
from pathlib import Path
import socket
import socketserver
import struct
import subprocess
import tempfile
import threading
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('idle_overlay', ROOT/'scripts/novnc-idle.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class RFB(socketserver.BaseRequestHandler):
    def read(self, count):
        result = b''
        while len(result) < count:
            chunk = self.request.recv(count-len(result))
            if not chunk:
                raise EOFError()
            result += chunk
        return result

    def handle(self):
        self.server.opened += 1
        self.server.active += 1
        try:
            self.request.sendall(b'RFB 003.008\n')
            self.read(12)
            self.request.sendall(b'\x01\x01')
            self.read(1)
            self.request.sendall(struct.pack('>I', 0))
            self.read(1)
            name = b'LazyTunnel disposable bandwidth test'
            pixel = struct.pack('>BBBBHHHBBB3x', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
            self.request.sendall(struct.pack('>HH', 64, 64)+pixel+struct.pack('>I', len(name))+name)
            while True:
                kind = self.read(1)[0]
                if kind == 0:
                    self.read(19)
                elif kind == 2:
                    count = struct.unpack('>xH', self.read(3))[0]
                    self.read(4*count)
                elif kind == 3:
                    incremental = self.read(9)[0]
                    if not incremental:
                        self.request.sendall(struct.pack('>BBHHHHHi', 0, 0, 1, 0, 0, 64, 64, 0)+b'\x00\x80\x00\x00'*4096)
                elif kind == 4:
                    self.read(7)
                elif kind == 5:
                    self.read(5)
                elif kind == 6:
                    length = struct.unpack('>xxxI', self.read(7))[0]
                    self.read(length)
                else:
                    raise ValueError('Unexpected RFB message: '+str(kind))
        except (EOFError, ConnectionError):
            pass
        finally:
            self.server.active -= 1


def wait(predicate):
    deadline = time.monotonic()+8
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError('Connection state did not settle')
        time.sleep(.05)


def main():
    with tempfile.TemporaryDirectory(prefix='lazytunnel-viewer-test-') as tmp:
        root = Path(tmp)/'web'
        module.install(Path('/usr/share/novnc'), root)
        server = socketserver.ThreadingTCPServer(('127.0.0.1', 0), RFB)
        server.daemon_threads = True
        server.active = server.opened = 0
        threading.Thread(target=server.serve_forever, daemon=True).start()
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        log = open(Path(tmp)/'websockify.log', 'w')
        proxy = subprocess.Popen(['/usr/bin/python3', '/usr/bin/websockify', '--web', str(root),
                                  '127.0.0.1:'+str(port), '127.0.0.1:'+str(server.server_address[1])], stdout=log, stderr=log)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--disable-gpu'])
                try:
                    page = browser.new_page()
                    errors = []
                    page.on('pageerror', lambda e: errors.append(str(e)))
                    page.clock.install()
                    page.goto(f'http://127.0.0.1:{port}/vnc.html?autoconnect=1&resize=off&reconnect=1')
                    page.wait_for_function("document.documentElement.classList.contains('noVNC_connected')")
                    wait(lambda: server.active == 1)
                    page.clock.run_for(1100)
                    page.clock.fast_forward(125000)
                    page.locator('#lazytunnel-idle-overlay').wait_for(state='visible')
                    wait(lambda: server.active == 0)
                    count = server.opened
                    page.clock.fast_forward(300000)
                    assert server.opened == count, 'Paused viewer reconnected on its own'
                    page.get_by_role('button', name='Resume desktop', exact=True).click()
                    page.wait_for_function("document.documentElement.classList.contains('noVNC_connected')")
                    wait(lambda: server.active == 1)
                    page.locator('#lazytunnel-idle-bar input').check()
                    page.clock.fast_forward(125000)
                    assert server.active == 1, 'Keep live did not preserve visible viewer'
                    page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true, value:true}); document.dispatchEvent(new Event('visibilitychange'))")
                    page.clock.fast_forward(11000)
                    wait(lambda: server.active == 0)
                    page.evaluate("Object.defineProperty(document, 'hidden', {configurable:true, value:false}); document.dispatchEvent(new Event('visibilitychange'))")
                    page.clock.fast_forward(60000)
                    assert server.active == 0, 'Returning silently reconnected'
                    page.get_by_role('button', name='Resume desktop', exact=True).click()
                    page.wait_for_function("document.documentElement.classList.contains('noVNC_connected')")
                    wait(lambda: server.active == 1)
                    page.close()
                    wait(lambda: server.active == 0)
                    assert not errors, errors
                    print('PASS: idle/hidden close actual RFB connections; Resume, Keep live, page close; no auto reconnect or JS errors')
                finally:
                    browser.close()
        finally:
            proxy.terminate()
            proxy.wait(timeout=10)
            server.shutdown()
            server.server_close()
            log.close()


if __name__ == '__main__':
    main()
