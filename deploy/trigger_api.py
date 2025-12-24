#!/usr/bin/env python3
"""
Simple trigger API that runs the tunnel script and returns the Tunnel URL.
Run as: python3 /opt/tunnel/trigger_api.py (systemd unit provided separately)
"""
import os
import re
import shlex
import subprocess
import threading
import errno
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
        # Respond immediately to the client with the tunnel URL so callers
        # (like Telegram) don't time out while we perform longer background work.
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        try:
            self.wfile.write(url.encode())
        except BrokenPipeError:
            # client disconnected before we could write; that's fine
            pass

        # Run docker-compose in background to pick up the new .env without
        # blocking the request handler.
        def run_compose_background():
            try:
                repo_dir = os.path.dirname(TUNNEL_SCRIPT) if TUNNEL_SCRIPT else None
                if not repo_dir:
                    print('No repo dir for TUNNEL_SCRIPT; skipping docker compose')
                    return

                svc_proc = subprocess.run(
                    ["docker", "compose", "config", "--services"],
                    cwd=repo_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                services = [s.strip() for s in svc_proc.stdout.splitlines() if s.strip()]
                services_to_update = [s for s in services if s != "telegram_bot"]
                if not services_to_update:
                    print("No services to update (only telegram_bot present); skipping docker compose step")
                    return

                cmd = ["docker", "compose", "up", "-d", "--build"] + services_to_update
                dc = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True, timeout=600)
                print("docker compose returncode:", dc.returncode)
                if dc.stdout:
                    print(dc.stdout)
                if dc.stderr:
                    print(dc.stderr)
            except Exception as e:
                # Avoid letting background exceptions crash the server
                print("docker compose invocation failed:", e)

        t = threading.Thread(target=run_compose_background, daemon=True)
        t.start()

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
