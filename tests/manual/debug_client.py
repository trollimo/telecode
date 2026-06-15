"""Debug: trace the full send_prompt flow for both turns."""
import asyncio, aiohttp, logging
from bot.config import Config
from bot.opencode_client import OpenCodeClient, _generate_id, _extract_response

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("debug")

OPCODE = "http://localhost:4096"
HEADERS = {"x-opencode-directory": "%2F"}

async def manual_send(http, sid, text, timeout=30):
    """Do what send_prompt does but with explicit http session."""
    msg_id = _generate_id("msg_")
    part_id = _generate_id("prt_")

    body = {
        "agent": "build",
        "model": {"modelID": "big-pickle", "providerID": "opencode"},
        "messageID": msg_id,
        "parts": [{"id": part_id, "type": "text", "text": text}],
    }
    async with http.post(f"{OPCODE}/session/{sid}/prompt_async", headers=HEADERS, json=body) as resp:
        log.info("prompt_async status=%s", resp.status)
        assert resp.status == 204

    deadline = asyncio.get_event_loop().time() + timeout
    interval = 2.0
    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            raise TimeoutError("poll timeout")
        await asyncio.sleep(min(interval, remaining))

        async with http.get(f"{OPCODE}/session/{sid}/message?directory=%2F&limit=200") as r:
            data = await r.json()
        msgs = data if isinstance(data, list) else data.get("value", [])

        # Debug: print all message parentIDs
        for m in msgs:
            info = m.get("info", {})
            log.debug("  msg role=%s parent=%s fin=%s", info.get("role"), info.get("parentID","")[:25], info.get("finish"))

        result = _extract_response(msgs, msg_id)
        if result is not None:
            log.info("EXTRACTED: %r", result)
            return result, sid

        interval = min(interval * 1.5, 15.0)


async def main():
    config = Config(telegram_token="test", allowed_user_id=1, opencode_url=OPCODE)

    # --- Turn 1: with OpenCodeClient ---
    client = OpenCodeClient(config)
    result1, sid = await client.send_prompt("Say hello in one word", timeout=30)
    print(f"TURN 1: {result1!r}  SID={sid}")
    await client.close()

    # --- Turn 2: reuse session via manual HTTP (same http session) ---
    async with aiohttp.ClientSession() as http:
        result2, sid2 = await manual_send(http, sid, "Say goodbye in one word", timeout=30)
        print(f"TURN 2a: {result2!r}  SID={sid2}")

    # --- Turn 3: reuse session via OpenCodeClient ---
    client2 = OpenCodeClient(config)
    result3, sid3 = await client2.send_prompt("Say yes in one word", session_id=sid, timeout=30)
    print(f"TURN 2b (client): {result3!r}  SID={sid3}")
    await client2.close()


asyncio.run(main())
