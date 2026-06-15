"""Use fresh aiohttp session for follow-up (not client._http)."""
import asyncio, aiohttp
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

    # Close the client's http session but NOT the opencode session
    await client.close()

    # Turn 2 with FRESH aiohttp session
    async with aiohttp.ClientSession() as http:
        msg_id = _generate_id("msg_")
        part_id = _generate_id("prt_")
        body = {
            "agent": "build",
            "model": {"modelID": "big-pickle", "providerID": "opencode"},
            "messageID": msg_id,
            "parts": [{"id": part_id, "type": "text", "text": "Say goodbye in one word"}],
        }
        resp = await http.post(f"{OPCODE}/session/{sid}/prompt_async", headers=HEADERS, json=body)
        print(f"prompt_async: {resp.status}")

        deadline = asyncio.get_event_loop().time() + 30
        interval = 2.0
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                print("TIMEOUT")
                break
            await asyncio.sleep(min(interval, remaining))
            async with http.get(f"{OPCODE}/session/{sid}/message?directory=%2F&limit=200") as r:
                data = await r.json()
            msgs = data if isinstance(data, list) else data.get("value", [])
            for m in msgs:
                info = m.get("info", {})
                pid = info.get("parentID", "")[:28]
                print(f"  role={info.get('role')} fin={info.get('finish')} parent={pid}")
            result = _extract_response(msgs, msg_id)
            if result is not None:
                print(f"EXTRACTED: {result!r}")
                break
            interval = min(interval * 1.5, 15.0)

asyncio.run(main())
