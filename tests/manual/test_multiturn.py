"""End-to-end multi-turn test against running OpenCode server."""
import asyncio
from bot.config import Config
from bot.opencode_client import OpenCodeClient


async def main():
    config = Config(
        telegram_token="test", allowed_user_id=1,
        opencode_url="http://localhost:4096",
    )
    client = OpenCodeClient(config)

    # Turn 1 — creates a new session
    result, sid = await client.send_prompt("Say hello in one word", timeout=30)
    assert result == "Hello", f"Expected 'Hello', got {result!r}"
    print(f"TURN 1: {result!r}  SID={sid}")

    # Turn 2 — reuses the same session
    result2, sid2 = await client.send_prompt(
        "Say goodbye in one word", session_id=sid, timeout=30
    )
    assert sid == sid2, f"Session changed: {sid} != {sid2}"
    assert result2 == "Goodbye", f"Expected 'Goodbye', got {result2!r}"
    print(f"TURN 2: {result2!r}  SID={sid2} (reused ✓)")

    print("\nALL OK — multi-turn works!")
    await client.close()


asyncio.run(main())
