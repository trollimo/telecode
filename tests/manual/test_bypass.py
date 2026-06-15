"""Bypass send_prompt for turn 2 — call internal methods directly."""
import asyncio
from bot.config import Config
from bot.opencode_client import OpenCodeClient, _generate_id, _extract_response

OPCODE = "http://localhost:4096"
HEADERS = {"x-opencode-directory": "%2F"}

async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url=OPCODE)
    client = OpenCodeClient(config)

    # Turn 1 via client
    result, sid = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"TURN 1: {result!r}  SID={sid}")

    # Turn 2 via client INTERNAL methods (not send_prompt)
    http = await client._get_http()
    msg_id = _generate_id("msg_")
    part_id = _generate_id("prt_")
    await client._send_prompt_async(http, HEADERS, sid, msg_id, part_id, "Say goodbye in one word")
    result2 = await client._poll(http, sid, msg_id, timeout=30)
    print(f"TURN 2 (bypass): {result2!r}")

    await client.close()

asyncio.run(main())
