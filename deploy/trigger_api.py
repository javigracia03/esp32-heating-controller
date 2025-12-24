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

HOST = os.environ.get('TRIGGER_HOST', '127.0.0.1')
PORT = int(os.environ.get('TRIGGER_PORT', '5055'))

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
            # Allow TUNNEL_SCRIPT to include args; run from the script's directory so
            # a relative `.env` in the repo root is found by the script.
            cmd = shlex.split(TUNNEL_SCRIPT)
            cwd = os.path.dirname(cmd[0]) if cmd and os.path.isabs(cmd[0]) else None
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=cwd)
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
        # After the tunnel script updates the repo .env, trigger docker-compose
        # to pick up the new environment for the telegram bot.
        try:
            repo_dir = os.path.dirname(TUNNEL_SCRIPT) if TUNNEL_SCRIPT else None
            if repo_dir:
                # run docker compose to rebuild/recreate all services so they pick up the new .env
                dc = subprocess.run(
                    ["docker", "compose", "up", "-d", "--build"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                # log compose output for debugging
                print("docker compose returncode:", dc.returncode)
                if dc.stdout:
                    print(dc.stdout)
                if dc.stderr:
                    print(dc.stderr)
        except Exception as e:
            print("docker compose invocation failed:", e)
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
