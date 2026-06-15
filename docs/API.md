# API Reference

The Telegram bot communicates with `opencode serve` via its HTTP API on port 4096.

## OpenCode HTTP API

### Create session

```http
POST /session
Content-Type: application/json
x-opencode-directory: %2F

{}
```

**Response** `200`:
```json
{
  "id": "ses_...",
  "slug": "...",
  "directory": "/"
}
```

### Send prompt (async, non-blocking)

```http
POST /session/{session_id}/prompt_async
Content-Type: application/json
x-opencode-directory: %2F

{
  "agent": "build",
  "model": { "modelID": "big-pickle", "providerID": "opencode" },
  "messageID": "msg_...",
  "parts": [
    { "id": "prt_...", "type": "text", "text": "user message" }
  ]
}
```

**Response** `204` — no body (message accepted for processing).

### Get messages (polling)

```http
GET /session/{session_id}/message?directory=%2F&limit=200
```

**Response** `200`:
```json
{
  "value": [
    { "info": { "id": "...", "role": "user" }, "parts": [...] },
    { "info": { "id": "...", "role": "assistant", "parentID": "...", "finish": "stop" }, "parts": [...] }
  ],
  "Count": 2
}
```

### Sync message (blocking — **not used by the bot**)

```http
POST /session/{session_id}/message
Content-Type: application/json

{
  "agent": "build",
  "parts": [{ "type": "text", "text": "..." }]
}
```

**Response** `200` — single assistant message object.

### Bot Client (`OpenCodeClient`)

The `bot/opencode_client.py` module exports:

```python
class OpenCodeClient:
    async def send_prompt(
        self,
        text: str,
        session_id: str | None = None,
        timeout: int = 300
    ) -> tuple[str, str]:
        """Send prompt → OpenCode. Returns (response_text, session_id)."""

    async def close(self) -> None:
        """Close the HTTP session."""
```

**Logic:**
1. If `session_id` is `None`, creates a new session via `POST /session`
2. Generates unique `messageID` and part `id` via `_generate_id()`
3. Sends via `POST /session/{id}/prompt_async` (returns 204 immediately)
4. Polls `GET /session/{id}/message` until the assistant's response is found
5. If the session returns 404 ("Session not found"), auto-creates a new session and retries once

### Helper: `_extract_response()`

```python
def _extract_response(messages: list, parent_message_id: str) -> str | None:
```

Scans message list for the last assistant message matching `parentID`. Returns concatenated text from all `type="text"` parts, or `None` if no response is ready yet.

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message |
| `/reset` | Clear conversation context (start a new session) |
| Any text | Send prompt to OpenCode |
