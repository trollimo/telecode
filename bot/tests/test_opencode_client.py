"""Tests for OpenCodeClient — talks directly to opencode serve API."""

import pytest

from bot.config import Config
from bot.opencode_client import OpenCodeClient


@pytest.fixture
def config() -> Config:
    return Config(telegram_token="t", allowed_user_id=1, opencode_url="http://localhost:9999")


@pytest.fixture
def client(config: Config) -> OpenCodeClient:
    return OpenCodeClient(config)


def _mock_response(mocker, status: int = 200, json_data: dict | None = None):
    """Build an aiohttp-like response mock supporting ``async with resp:``."""
    resp = mocker.AsyncMock()
    resp.status = status
    resp.json = mocker.AsyncMock(return_value=json_data or {})
    resp.text = mocker.AsyncMock(return_value="error body")
    resp.__aenter__ = mocker.AsyncMock(return_value=resp)
    resp.__aexit__ = mocker.AsyncMock(return_value=None)
    return resp


def _mock_session(mocker, post_responses: "list | None" = None, default_resp=None):
    """Build a session mock with ``post(url, ...)`` returning responses.

    If ``post_responses`` is given, each consecutive call returns the next
    response from the list (one-shot).  Otherwise ``default_resp`` is used
    for every call.
    """
    session = mocker.MagicMock()
    if post_responses:
        # Return responses sequentially
        iterator = iter(post_responses)
        session.post = mocker.MagicMock(side_effect=lambda *a, **kw: next(iterator))
    else:
        session.post = mocker.MagicMock(return_value=default_resp)
    session.closed = False
    return session


class TestOpenCodeClient:
    """Tests for OpenCodeClient using opencode serve API."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    SESSION_ID = "ses_test123"

    def _session_resp(self, mocker):
        """Response for POST /session → returns {id: ...}."""
        return _mock_response(mocker, status=200, json_data={"id": self.SESSION_ID})

    def _message_resp(self, mocker, text: str):
        """Response for POST /session/:id/message → returns parts."""
        return _mock_response(
            mocker,
            status=200,
            json_data={"parts": [{"type": "text", "text": text}]},
        )

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_send_prompt_success(self, mocker, client: OpenCodeClient) -> None:
        """Create session + send message → returns text from parts."""
        session_resp = self._session_resp(mocker)
        msg_resp = self._message_resp(mocker, "Hello from OpenCode")
        client._session = _mock_session(mocker, post_responses=[session_resp, msg_resp])

        result = await client.send_prompt("my task")
        assert result == "Hello from OpenCode"

        # Called POST /session then POST /session/:id/message
        assert client._session.post.call_count == 2

    @pytest.mark.asyncio
    async def test_send_prompt_no_text_parts(self, mocker, client: OpenCodeClient) -> None:
        """Response with no text parts returns empty string."""
        session_resp = self._session_resp(mocker)
        msg_resp = _mock_response(
            mocker, status=200, json_data={"parts": [{"type": "tool_use", "text": ""}]}
        )
        client._session = _mock_session(mocker, post_responses=[session_resp, msg_resp])

        result = await client.send_prompt("task")
        assert result == ""

    @pytest.mark.asyncio
    async def test_session_creation_fails(self, mocker, client: OpenCodeClient) -> None:
        """Non-200 on session creation raises RuntimeError."""
        err_resp = _mock_response(mocker, status=500)
        client._session = _mock_session(mocker, default_resp=err_resp)

        with pytest.raises(RuntimeError, match="500"):
            await client.send_prompt("fail")

    @pytest.mark.asyncio
    async def test_message_send_fails(self, mocker, client: OpenCodeClient) -> None:
        """Non-200 on message send raises RuntimeError."""
        session_resp = self._session_resp(mocker)
        err_resp = _mock_response(mocker, status=502)
        client._session = _mock_session(mocker, post_responses=[session_resp, err_resp])

        with pytest.raises(RuntimeError, match="502"):
            await client.send_prompt("fail")

    @pytest.mark.asyncio
    async def test_connection_error(self, mocker, client: OpenCodeClient) -> None:
        """aiohttp.ClientError raises ConnectionError."""
        session = mocker.MagicMock()
        session.post = mocker.MagicMock(
            side_effect=__import__("aiohttp").ClientError("connection refused")
        )
        session.closed = False
        client._session = session

        with pytest.raises(ConnectionError, match="connection refused"):
            await client.send_prompt("test")

    @pytest.mark.asyncio
    async def test_send_prompt_multi_text_parts(self, mocker, client: OpenCodeClient) -> None:
        """Multiple text parts are concatenated with newline."""
        session_resp = self._session_resp(mocker)
        msg_resp = _mock_response(
            mocker,
            status=200,
            json_data={
                "parts": [
                    {"type": "text", "text": "First part"},
                    {"type": "text", "text": "Second part"},
                    {"type": "tool_use", "text": "ignored"},
                ]
            },
        )
        client._session = _mock_session(mocker, post_responses=[session_resp, msg_resp])

        result = await client.send_prompt("task")
        assert result == "First part\nSecond part"

    @pytest.mark.asyncio
    async def test_close_session(self, client: OpenCodeClient) -> None:
        """close() cleans up the HTTP session."""
        mock_session = __import__("aiohttp").ClientSession()
        client._session = mock_session
        assert not client._session.closed

        await client.close()
        assert client._session.closed
