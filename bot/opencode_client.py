"""Client for communicating with the OpenCode server API (opencode serve).

Every message is sent via the non-blocking ``prompt_async`` endpoint
and the response is retrieved by polling ``GET /session/{id}/message``.
This avoids blocking (and timing out) when the session is busy with a
previously-running tool.

* **New session** (``session_id=None``)
    1. POST /session — create a new session
    2. POST /session/{id}/prompt_async — send prompt (returns 204)
    3. GET /session/{id}/message — poll for the assistant's response

* **Follow-up** (``session_id=<existing>``)
    1. POST /session/{id}/prompt_async — send prompt (returns 204)
    2. GET /session/{id}/message — poll for the assistant's response
"""

import asyncio
import logging
import uuid

import aiohttp

from bot.config import Config

logger = logging.getLogger(__name__)

_MESSAGE_PREFIX = "msg_"
_PART_PREFIX = "prt_"


def _generate_id(prefix: str) -> str:
    """Generate a unique identifier with a short hex suffix."""
    return prefix + uuid.uuid4().hex[:26]


class OpenCodeClient:
    """HTTP client for the opencode server API."""

    def __init__(self, config: Config) -> None:
        self._base_url = config.opencode_url.rstrip("/")
        self._http: aiohttp.ClientSession | None = None

    async def _get_http(self) -> aiohttp.ClientSession:
        if self._http is None or self._http.closed:
            self._http = aiohttp.ClientSession()
        return self._http

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def send_prompt(
        self, text: str, session_id: str | None = None, timeout: int = 300
    ) -> tuple[str, str]:
        """Send a text prompt to OpenCode and return the response.

        If *session_id* is provided the message is sent as a follow-up
        into an **existing** session (multi-turn).  Otherwise a
        brand-new session is created.

        Returns:
            ``(response_text, session_id)``.

        Raises:
            ConnectionError: If OpenCode is unreachable.
            RuntimeError: If the API returns an error status, or the
                response does not arrive within *timeout* seconds.
        """
        http = await self._get_http()
        headers = {"x-opencode-directory": "%2F"}

        try:
            if not session_id:
                session_id = await self._create_session(http, headers)
            else:
                logger.info("Follow-up in session %s", session_id)

            return await self._send_and_poll(
                http, headers, session_id, text, timeout
            )

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Cannot reach OpenCode at {self._base_url}: {e}"
            ) from e

    async def _send_and_poll(
        self,
        http: aiohttp.ClientSession,
        headers: dict,
        session_id: str,
        text: str,
        timeout: int,
        _retried: bool = False,
    ) -> tuple[str, str]:
        """Send a message via prompt_async and poll for the response."""
        msg_id = _generate_id(_MESSAGE_PREFIX)
        part_id = _generate_id(_PART_PREFIX)

        try:
            await self._send_prompt_async(
                http, headers, session_id, msg_id, part_id, text
            )
        except RuntimeError as e:
            err_str = str(e)
            # If the session no longer exists, create a new one and
            # retry exactly once (avoids losing the user's message).
            if not _retried and "Session not found" in err_str:
                logger.warning(
                    "Session %s not found, creating a new one", session_id
                )
                new_sid = await self._create_session(http, headers)
                return await self._send_and_poll(
                    http, headers, new_sid, text, timeout, _retried=True
                )
            raise

        text_result = await self._poll(http, session_id, msg_id, timeout)
        return text_result, session_id

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._http and not self._http.closed:
            await self._http.close()

    # ------------------------------------------------------------------
    # Async flow (new sessions)
    # ------------------------------------------------------------------

    async def _create_session(
        self, http: aiohttp.ClientSession, headers: dict
    ) -> str:
        """POST /session → return session ID."""
        async with http.post(
            f"{self._base_url}/session",
            headers=headers,
            json={},
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(
                    f"OpenCode create session failed (HTTP {resp.status}): {body}"
                )
            data = await resp.json()
            sid = data["id"]
            logger.info("Created session %s", sid)
            return sid

    async def _send_prompt_async(
        self,
        http: aiohttp.ClientSession,
        headers: dict,
        session_id: str,
        message_id: str,
        part_id: str,
        text: str,
    ) -> None:
        """POST /session/{id}/prompt_async — returns 204 on success."""
        body = {
            "agent": "build",
            "model": {"modelID": "big-pickle", "providerID": "opencode"},
            "messageID": message_id,
            "parts": [{"id": part_id, "type": "text", "text": text}],
        }
        async with http.post(
            f"{self._base_url}/session/{session_id}/prompt_async",
            headers=headers,
            json=body,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 204:
                body_text = await resp.text()
                raise RuntimeError(
                    f"OpenCode prompt_async failed "
                    f"(HTTP {resp.status}): {body_text}"
                )
            logger.info("Sent prompt_async to session %s", session_id)

    async def _poll(
        self,
        http: aiohttp.ClientSession,
        session_id: str,
        message_id: str,
        timeout: int,
    ) -> str:
        """Poll GET /session/{id}/message until we have assistant text."""
        deadline = asyncio.get_event_loop().time() + timeout
        interval = 2.0

        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                raise RuntimeError(
                    f"OpenCode did not respond within {timeout}s "
                    f"(session {session_id})"
                )

            await asyncio.sleep(min(interval, remaining))

            messages = await self._get_messages(http, session_id)
            result = _extract_response(messages, message_id)
            if result is not None:
                logger.info(
                    "Session %s response — %s chars", session_id, len(result)
                )
                return result

            interval = min(interval * 1.5, 15.0)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    async def _get_messages(
        self, http: aiohttp.ClientSession, session_id: str
    ) -> list:
        """Fetch all messages for a session.

        Unwraps the ``{"value": [...], "Count": N}`` envelope if present.
        """
        url = (
            f"{self._base_url}/session/{session_id}"
            f"/message?directory=%2F&limit=200"
        )
        async with http.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(
                    f"OpenCode get messages failed (HTTP {resp.status}): {body}"
                )
            data = await resp.json()

        if isinstance(data, dict) and "value" in data:
            return data["value"]
        if isinstance(data, list):
            return data
        return []


# ── standalone helper (also used by tests) ─────────────────────────────


def _extract_response(messages: list, parent_message_id: str) -> str | None:
    """Extract the assistant's text reply for a given user message.

    Scans *messages* for the **last** assistant message whose
    ``parentID`` equals *parent_message_id* that contains any text
    parts.

    Finished messages (``info.finish == "stop"``) are preferred, but
    in-progress messages that already contain text (e.g. an assistant
    question) are also accepted.

    Returns:
        * ``None`` — no assistant text found yet (keep polling).
        * ``""`` — assistant responded but without text parts.
        * ``"text"`` — concatenated text from all text parts.
    """
    finished_with_text = None
    in_progress_with_text = None
    finished_no_text = None

    for msg in messages:
        info = msg.get("info", {})
        if info.get("role") != "assistant":
            continue
        if info.get("parentID") != parent_message_id:
            continue

        parts = msg.get("parts", [])
        has_text = any(
            p.get("type") == "text" and p.get("text")
            for p in parts
        )
        is_finished = info.get("finish") == "stop"

        if is_finished and has_text:
            finished_with_text = msg
        elif is_finished and not has_text:
            finished_no_text = msg
        elif has_text:
            in_progress_with_text = msg

    chosen = finished_with_text or in_progress_with_text or finished_no_text
    if chosen is None:
        return None

    text_fragments = [
        p.get("text", "")
        for p in chosen.get("parts", [])
        if p.get("type") == "text" and p.get("text")
    ]
    return "\n".join(text_fragments).strip()
