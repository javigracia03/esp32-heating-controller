import os
import time
import requests
import sys

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
        resp = requests.post(TRIGGER_URL, headers=headers, timeout=30)
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
