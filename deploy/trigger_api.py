#!/usr/bin/env python3
"""
Simple trigger API that runs the tunnel script and returns the Tunnel URL.
Run as: python3 /opt/tunnel/trigger_api.py (systemd unit provided separately)
"""
import os
import re
import shlex
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

HOST = '127.0.0.1'
PORT = 5055

TRIGGER_TOKEN = os.environ.get('TRIGGER_TOKEN')
TUNNEL_SCRIPT = os.environ.get('TUNNEL_SCRIPT')

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != '/tunnel':
            self.send_response(404)
            self.end_headers()
            return

        auth = self.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            self.send_response(401)
            self.end_headers()
            return
        token = auth.split(' ', 1)[1]
        if TRIGGER_TOKEN is None or token != TRIGGER_TOKEN:
            self.send_response(401)
            self.end_headers()
            return

        if not TUNNEL_SCRIPT:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'Missing TUNNEL_SCRIPT env')
            return

        try:
            proc = subprocess.run([TUNNEL_SCRIPT], capture_output=True, text=True, timeout=120)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())
            return

        output = proc.stdout + "\n" + proc.stderr
        m = re.search(r"Tunnel URL:\s*(https?://\S+)", output)
        if not m:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(output.encode())
            return

        url = m.group(1)
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(url.encode())

    def log_message(self, format, *args):
        # keep logs minimal
        print(format % args)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def main():
    server = ThreadedHTTPServer((HOST, PORT), Handler)
    print(f"Trigger API listening on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == '__main__':
    main()
