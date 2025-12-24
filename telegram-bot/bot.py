import os
import time
import requests
import sys
import socket
import struct

TG_TOKEN = os.environ.get("TG_TOKEN")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID")
TRIGGER_TOKEN = os.environ.get("TRIGGER_TOKEN")
TRIGGER_URL = os.environ.get("TRIGGER_URL", "http://host.docker.internal:5055/tunnel")

if not TG_TOKEN or not TG_CHAT_ID or not TRIGGER_TOKEN:
    print("Missing required env vars: TG_TOKEN, TG_CHAT_ID, TRIGGER_TOKEN", file=sys.stderr)
    sys.exit(1)

API_BASE = f"https://api.telegram.org/bot{TG_TOKEN}"

def send_message(text):
    requests.post(f"{API_BASE}/sendMessage", json={"chat_id": TG_CHAT_ID, "text": text})

def handle_tunnel_command():
    try:
        headers = {"Authorization": f"Bearer {TRIGGER_TOKEN}"}

        def try_post(url):
            try:
                return requests.post(url, headers=headers, timeout=30)
            except requests.RequestException:
                return None

        # Try configured URL first
        resp = try_post(TRIGGER_URL)

        # If failed, try to discover docker gateway and retry automatically
        if resp is None or resp.status_code >= 500:
            gw = None
            try:
                # read /proc/net/route and find default gateway
                with open('/proc/net/route') as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 3 and parts[1] == '00000000':
                            gw_hex = parts[2]
                            gw = socket.inet_ntoa(struct.pack('<L', int(gw_hex, 16)))
                            break
            except Exception:
                gw = None

            if gw:
                gw_url = f"http://{gw}:5055/tunnel"
                resp = try_post(gw_url)

        if resp is None:
            send_message("Error calling trigger API: connection failed")
            return

        if resp.status_code == 200:
            send_message(f"Tunnel URL: {resp.text.strip()}")
        elif resp.status_code == 401:
            send_message("Trigger API: Unauthorized")
        else:
            send_message(f"Trigger API error: {resp.status_code} {resp.text}")
    except Exception as e:
        send_message(f"Error calling trigger API: {e}")

def main():
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
            r = requests.get(f"{API_BASE}/getUpdates", params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            for item in data.get("result", []):
                offset = item["update_id"] + 1
                message = item.get("message") or item.get("edited_message")
                if not message:
                    continue
                chat_id = str(message["chat"]["id"]) if message.get("chat") else None
                text = message.get("text", "")
                if chat_id != str(TG_CHAT_ID):
                    continue
                if text.strip().split()[0] == "/tunnel":
                    handle_tunnel_command()
        except Exception as e:
            print("Polling error:", e, file=sys.stderr)
            time.sleep(2)

if __name__ == '__main__':
    main()
