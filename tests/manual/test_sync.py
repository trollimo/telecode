"""Test sync POST /session/{id}/message for follow-up."""
import asyncio, aiohttp
from bot.config import Config
from bot.opencode_client import OpenCodeClient, _generate_id

OPCODE = "http://localhost:4096"
HEADERS = {"x-opencode-directory": "%2F"}

async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url=OPCODE)
    client = OpenCodeClient(config)

    # Turn 1 via async client
    result, sid = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"TURN 1: {result!r}")

    # Turn 2 via SYNC endpoint
    async with aiohttp.ClientSession() as http:
        body = {
            "agent": "build",
            "model": {"modelID": "big-pickle", "providerID": "opencode"},
            "parts": [{"type": "text", "text": "Say goodbye in one word"}],
        }
        async with http.post(
            f"{OPCODE}/session/{sid}/message",
            headers=HEADERS,
            json=body,
            timeout=aiohttp.ClientTimeout(total=60),
        ) as resp:
            print(f"SYNC POST status: {resp.status}")
            data = await resp.json()
            print(f"SYNC POST response: {data}")

    await client.close()

asyncio.run(main())
