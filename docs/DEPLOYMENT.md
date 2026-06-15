# Deployment

## 1. Get a Telegram Bot Token

1. Open Telegram and search for [@BotFather](https://t.me/botfather)
2. Send `/newbot` and follow the prompts
3. Copy the API token (looks like `738456...:AAH...`)

## 2. Get Your Telegram User ID

Talk to [@userinfobot](https://t.me/userinfobot) — it will reply with your numeric user ID.

## 3. Create Config File

Create `~/.rem-opencode/config.json`:

```json
{
  "telegram_token": "738456...:AAH...",
  "allowed_user_id": 123456789,
  "opencode_url": "http://opencode:4096"
}
```

| Field | Description |
|---|---|
| `telegram_token` | Token from BotFather |
| `allowed_user_id` | Your Telegram numeric user ID |
| `opencode_url` | Internal Docker hostname (do not change) |

> ⚠️ This file contains secrets. It is in `.gitignore` and **must never be committed**.

## 4. Start the Stack

### First start (builds images)

```bash
./scripts/run.sh
```

This will:
1. Check that the config file exists
2. Build Docker images if they don't exist yet
3. Start both services

### Subsequent starts (no rebuild)

```bash
# Start without rebuilding
docker compose -f docker/compose.yml --project-directory . up -d

# Or restart
./scripts/restart.sh
```

### Stop

```bash
./scripts/stop.sh
```

## Avoiding Regular Rebuilds

Images are **only rebuilt** under these conditions:

- **First run**: `./scripts/run.sh` checks if images exist and builds them
- **Manual rebuild**: `docker compose -f docker/compose.yml --project-directory . build`
- **Explicit `--build` flag**: `docker compose -f docker/compose.yml --project-directory . up -d --build`

Normal restarts (`./scripts/restart.sh`, `docker compose restart`) do **not** trigger a rebuild.

The bot code is mounted as a volume (`./bot:/app/bot`), so Python changes take effect on container restart without rebuilding the image.

## Environment Variables (Optional)

Create a `.env` file in the project root for LLM API keys:

```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
OPENCODE_ZEN_API_KEY=...
OPENCODE_SERVER_PASSWORD=...
```

## Health Check

```bash
curl http://localhost:4096/global/health
```

Expected response: `{"healthy":true,"version":"1.16.2"}`
