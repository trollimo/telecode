"""Client for communicating with the OpenCode server API (opencode serve)."""

import logging

import aiohttp

from bot.config import Config

logger = logging.getLogger(__name__)


class OpenCodeClient:
    """HTTP client for the opencode server API.

    Uses ``opencode serve`` HTTP protocol:
      1. POST /session → create a new session
      2. POST /session/{id}/message → send a prompt and get response
    """

    def __init__(self, config: Config) -> None:
        self._base_url = config.opencode_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def send_prompt(self, text: str) -> str:
        """Send a text prompt to OpenCode and return the response.

        Creates a new session via ``POST /session``, then sends the prompt
        via ``POST /session/{id}/message`` and extracts the assistant's text reply.

        Args:
            text: The user's prompt.

        Returns:
            The assistant's text response.

        Raises:
            ConnectionError: If OpenCode is unreachable.
            RuntimeError: If the API returns an error status.
        """
        session = await self._get_session()

        try:
            # 1. Create a new session
            async with session.post(
                f"{self._base_url}/session",
                json={},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"OpenCode create session failed (HTTP {resp.status}): {body}"
                    )
                session_data = await resp.json()
                session_id = session_data["id"]

            logger.info("Created opencode session %s", session_id)

            # 2. Send the prompt and wait for the assistant's reply
            parts = [{"type": "text", "text": text}]
            async with session.post(
                f"{self._base_url}/session/{session_id}/message",
                json={"parts": parts},
                timeout=aiohttp.ClientTimeout(total=600),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    raise RuntimeError(
                        f"OpenCode send message failed (HTTP {resp.status}): {body}"
                    )
                message_data = await resp.json()

            # 3. Concatenate all text parts from the response
            response_parts = message_data.get("parts", [])
            text_parts = []
            for part in response_parts:
                if part.get("type") == "text":
                    text_parts.append(part.get("text", ""))

            result = "\n".join(text_parts).strip()
            logger.info("Session %s completed — response length: %s chars", session_id, len(result))
            return result

        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Cannot reach OpenCode at {self._base_url}: {e}"
            ) from e

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
