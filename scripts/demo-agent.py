#!/usr/bin/env python3
"""Read-only sample fleet for real-app screenshots; never touches SSH or inventory."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEVICES = ['studio-linux', 'home-mac', 'render-node', 'cloud-relay', 'workstation-win', 'lab-mini']
STATE = {
    'devices': [dict(name=name, user='demo', local=i == 0,
        aliases=['ssh-lazy-' + name], probe={'status': 'reachable', 'ms': 12 + i * 7,
        'detail': 'Sample connection — not a live probe'}) for i, name in enumerate(DEVICES)],
    'viewers': [dict(id='sample-' + str(i), name=name, device='studio-linux', mode='local',
        status='active', path='/', local_port=17768, remote_port=17768)
        for i, name in enumerate(['Studio desktop', 'Private workspace'])],
    'checking': False, 'managed_forwards': False,
}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body):
        raw = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == '/api/state':
            self.reply(200, STATE)
        else:
            self.reply(404, {'error': 'Screenshot fixture only'})

    def do_POST(self):
        self.reply(403, {'error': 'Sample fleet is read-only; no operation was performed'})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=17769)
    args = parser.parse_args()
    if args.port in (17765, 17766) or not 1024 <= args.port <= 65535:
        parser.error('Choose an unprivileged port separate from the live console and agent')
    print('Sample agent on 127.0.0.1:' + str(args.port), flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
