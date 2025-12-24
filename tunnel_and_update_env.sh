#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env}"
LOCAL_SERVICE_URL="${2:-http://localhost:8080}"   # what your server listens on locally
API_PATH="${3:-/api}"                              # keep /api like your current .env

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "ERROR: cloudflared not found. Install it first."
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: $ENV_FILE not found"
  exit 1
fi

echo "Starting quick tunnel to: $LOCAL_SERVICE_URL"
echo "Reading tunnel URL..."

# Start tunnel and capture logs
TMP_LOG="$(mktemp)"
cleanup() {
  rm -f "$TMP_LOG"
}
trap cleanup EXIT

# Drop any existing quick tunnels started by this script
# (targets processes started with the same cloudflared quick-tunnel args)
EXISTING_PIDS=$(pgrep -f "cloudflared tunnel --no-autoupdate --url" || true)
if [[ -n "$EXISTING_PIDS" ]]; then
  echo "Stopping existing cloudflared quick tunnels: $EXISTING_PIDS"
  for pid in $EXISTING_PIDS; do
    kill "$pid" >/dev/null 2>&1 || true
  done
  # give time for ports to be released
  sleep 1
fi

# Run cloudflared in background
# --no-autoupdate avoids some environments hanging on update checks
cloudflared tunnel --no-autoupdate --url "$LOCAL_SERVICE_URL" >"$TMP_LOG" 2>&1 &
TUNNEL_PID=$!

# Wait until URL appears in logs
TUNNEL_URL=""
for _ in {1..60}; do
  if grep -qE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TMP_LOG"; then
    TUNNEL_URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TMP_LOG" | head -n1)"
    break
  fi
  sleep 1
done

if [[ -z "$TUNNEL_URL" ]]; then
  echo "ERROR: Could not detect trycloudflare.com URL. Tunnel logs:"
  cat "$TMP_LOG" || true
  kill "$TUNNEL_PID" >/dev/null 2>&1 || true
  exit 1
fi

PUBLIC_API_URL="${TUNNEL_URL}${API_PATH}"

echo "Tunnel URL: $TUNNEL_URL"
echo "Public API: $PUBLIC_API_URL"
echo "Tunnel PID: $TUNNEL_PID"
echo

# Backup env
cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d_%H%M%S)"

# Update WEB_ORIGINS and VITE_API_BASE (replace whole line if exists, else append)
update_kv () {
  local key="$1"
  local val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    # portable sed (GNU). On macOS server, use gsed; but you're on Ubuntu.
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

# Do not include the API path in WEB_ORIGINS (frontend origin should be root URL)
update_kv "WEB_ORIGINS" "$TUNNEL_URL"
# Keep VITE_API_BASE pointing to the public API URL (including API path)
update_kv "VITE_API_BASE" "$PUBLIC_API_URL"

echo "Updated $ENV_FILE:"
grep -E '^(WEB_ORIGINS|VITE_API_BASE)=' "$ENV_FILE"
echo
echo "Tunnel is running in background (PID $TUNNEL_PID)."
echo "To stop it: kill $TUNNEL_PID"
echo "To watch tunnel logs: tail -f $TMP_LOG"
