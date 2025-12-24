This directory contains a minimal Telegram polling bot.

Environment variables required:

- `TG_TOKEN` - bot token
- `TG_CHAT_ID` - allowed chat id
- `TRIGGER_TOKEN` - bearer token for trigger API
- `TRIGGER_URL` - http://host.docker.internal:5055/tunnel (default)

Build with `docker build -t telegram-bot .` and run with the env vars set.
