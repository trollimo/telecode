"""Simple test: new session for each turn."""
import asyncio
from bot.config import Config
from bot.opencode_client import OpenCodeClient

async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url="http://localhost:4096")
    client = OpenCodeClient(config)

    # Turn 1
    r, s = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"TURN 1 (new session): {r!r}")

    # Turn 2 — BRAND NEW session
    r2, s2 = await client.send_prompt("Say goodbye in one word", timeout=30)
    print(f"TURN 2 (new session): {r2!r}")

    # Turn 3 — reuse session from Turn 1
    r3, s3 = await client.send_prompt("Say yes in one word", session_id=s, timeout=30)
    print(f"TURN 3 (reuse T1): {r3!r}")

    await client.close()

asyncio.run(main())
