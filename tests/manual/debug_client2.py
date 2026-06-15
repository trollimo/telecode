"""Debug: reuse client without close() between turns."""
import asyncio
from bot.config import Config
from bot.opencode_client import OpenCodeClient

OPCODE = "http://localhost:4096"

async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url=OPCODE)
    client = OpenCodeClient(config)

    # Turn 1 — creates new session
    result, sid = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"TURN 1: {result!r}  SID={sid}")

    # Turn 2 — reuse same session via SAME client (no close)
    result2, sid2 = await client.send_prompt(
        "Say goodbye in one word", session_id=sid, timeout=30
    )
    print(f"TURN 2 (no close): {result2!r}  SID={sid2}")

    await client.close()
    print("ALL OK")

asyncio.run(main())
