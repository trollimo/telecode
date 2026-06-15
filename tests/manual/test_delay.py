"""Verify: delay between turns fixes rate limiting."""
import asyncio
from bot.config import Config
from bot.opencode_client import OpenCodeClient

OPCODE = "http://localhost:4096"

async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url=OPCODE)
    client = OpenCodeClient(config)

    # Turn 1
    result, sid = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"TURN 1: {result!r}  SID={sid}")

    # Wait for rate limit to cool down
    print("Waiting 30s for rate limit...")
    await asyncio.sleep(10)

    # Turn 2 — reuse session
    result2, sid2 = await client.send_prompt(
        "Say goodbye in one word", session_id=sid, timeout=60
    )
    print(f"TURN 2 (reuse after delay): {result2!r}  SID={sid2}")

    # Turn 3 — NEW session (no delay needed)
    print("Turn 3: new session, no delay...")
    result3, sid3 = await client.send_prompt("Say yes in one word", timeout=30)
    print(f"TURN 3 (new session): {result3!r}  SID={sid3}")

    await client.close()

asyncio.run(main())
