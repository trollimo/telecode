"""Debug: trace client internals for multi-turn."""
import asyncio, logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from bot.config import Config
from bot.opencode_client import OpenCodeClient

OPCODE = "http://localhost:4096"

async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url=OPCODE)
    client = OpenCodeClient(config)

    result, sid = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"\n=== TURN 1: {result!r}  SID={sid} ===\n")

    result2, sid2 = await client.send_prompt(
        "Say goodbye in one word", session_id=sid, timeout=30
    )
    print(f"\n=== TURN 2: {result2!r}  SID={sid2} ===\n")

    await client.close()

asyncio.run(main())
