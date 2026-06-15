"""Tests for OpenCodeClient — async flow (prompt_async + polling)."""

import pytest

from bot.config import Config
from bot.opencode_client import OpenCodeClient, _extract_response


@pytest.fixture
def config() -> Config:
    return Config(telegram_token="t", allowed_user_id=1, opencode_url="http://localhost:9999")


@pytest.fixture
def client(config: Config) -> OpenCodeClient:
    return OpenCodeClient(config)


# ── helpers ────────────────────────────────────────────────────────────


def _mock_response(mocker, status: int = 200, json_data: dict | None = None):
    """Build an aiohttp-like response mock supporting ``async with resp:``."""
    resp = mocker.AsyncMock()
    resp.status = status
    resp.json = mocker.AsyncMock(return_value=json_data or {})
    resp.text = mocker.AsyncMock(return_value="error body")
    resp.__aenter__ = mocker.AsyncMock(return_value=resp)
    resp.__aexit__ = mocker.AsyncMock(return_value=None)
    return resp


def _user_message(parent_id: str = "msg_parent") -> dict:
    """User message dict (as returned by GET /session/{id}/message)."""
    return {
        "info": {"id": parent_id, "role": "user"},
        "parts": [{"id": "prt_u1", "type": "text", "text": "hello"}],
    }


def _assistant_message(
    parent_id: str,
    finish: str | None = "stop",
    text_parts: list[str] | None = None,
) -> dict:
    """Assistant message dict."""
    parts = [{"id": "prt_ss1", "type": "step-start"}]
    if text_parts:
        for i, t in enumerate(text_parts):
            parts.append({"id": f"prt_a{i}", "type": "text", "text": t})
    parts.append({"id": "prt_sf1", "type": "step-finish"})

    info: dict = {
        "id": "msg_assistant",
        "role": "assistant",
        "parentID": parent_id,
        "agent": "build",
    }
    if finish:
        info["finish"] = finish

    return {"info": info, "parts": parts}


def _messages_envelope(messages: list) -> dict:
    """Wrap messages in the server's response envelope."""
    return {"value": messages, "Count": len(messages)}


# ── _extract_response unit tests ───────────────────────────────────────


class TestExtractResponse:
    """Tests for the standalone _extract_response() function."""

    def test_no_assistant_messages(self):
        """Only user messages → None (keep polling)."""
        assert _extract_response([_user_message("m1")], "m1") is None

    def test_assistant_not_finished_no_text(self):
        """In-progress assistant without text parts → None."""
        msgs = [_user_message("m1"), _assistant_message("m1", finish=None)]
        assert _extract_response(msgs, "m1") is None

    def test_assistant_finished_with_text(self):
        """Finished assistant with text parts → returns text."""
        msgs = [_user_message("m1"), _assistant_message("m1", text_parts=["Hello"])]
        assert _extract_response(msgs, "m1") == "Hello"

    def test_assistant_in_progress_with_text(self):
        """In-progress assistant that already has text (e.g. a question)."""
        msgs = [
            _user_message("m1"),
            _assistant_message("m1", finish=None, text_parts=["Which file?"]),
        ]
        assert _extract_response(msgs, "m1") == "Which file?"

    def test_finished_takes_precedence_over_in_progress(self):
        """Finished message preferred over in-progress with text."""
        msgs = [
            _user_message("m1"),
            _assistant_message("m1", finish=None, text_parts=["In progress"]),
            _assistant_message("m1", finish="stop", text_parts=["Final"]),
        ]
        assert _extract_response(msgs, "m1") == "Final"

    def test_multiple_text_parts_joined(self):
        """Multiple text parts joined by newline."""
        msgs = [
            _user_message("m1"),
            _assistant_message("m1", text_parts=["First", "Second"]),
        ]
        assert _extract_response(msgs, "m1") == "First\nSecond"

    def test_finished_empty_text_returns_empty(self):
        """Finished assistant with no text parts → empty string."""
        msgs = [_user_message("m1"), _assistant_message("m1", text_parts=[])]
        assert _extract_response(msgs, "m1") == ""

    def test_ignores_unrelated_parent(self):
        """Only messages matching parentID are considered."""
        msgs = [
            _user_message("m1"),
            _assistant_message("m1", text_parts=["Correct"]),
            _assistant_message("other_parent", text_parts=["Wrong"]),
        ]
        assert _extract_response(msgs, "m1") == "Correct"

    def test_takes_last_completed_message(self):
        """Multiple finished messages → last one wins."""
        msgs = [
            _user_message("m1"),
            _assistant_message("m1", text_parts=["First"]),
            _assistant_message("m1", text_parts=["Final"]),
        ]
        assert _extract_response(msgs, "m1") == "Final"

    def test_ignores_reasoning_parts(self):
        """Only type='text' parts are included, not reasoning."""
        msgs = [
            _user_message("m1"),
            {
                "info": {
                    "id": "msg_a1",
                    "role": "assistant",
                    "parentID": "m1",
                    "finish": "stop",
                },
                "parts": [
                    {"id": "p1", "type": "step-start"},
                    {"id": "p2", "type": "reasoning", "text": "thinking..."},
                    {"id": "p3", "type": "text", "text": "Hello"},
                    {"id": "p4", "type": "step-finish"},
                ],
            },
        ]
        assert _extract_response(msgs, "m1") == "Hello"

    def test_returns_none_for_different_parent(self):
        """Messages for unrelated parent → None."""
        assert _extract_response(
            [_assistant_message("other", text_parts=["Hi"])], "my_msg"
        ) is None


# ── OpenCodeClient integration tests ───────────────────────────────────


class TestOpenCodeClient:
    """Integration tests for OpenCodeClient with mocked HTTP."""

    SESSION_ID = "ses_test123"

    # ------------------------------------------------------------------
    # success path (new session)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_send_prompt_success(self, mocker, client: OpenCodeClient) -> None:
        """Happy path: new session → prompt_async 204 → poll → response."""
        mocker.patch("bot.opencode_client.asyncio.sleep", return_value=None)
        mocker.patch(
            "bot.opencode_client._generate_id",
            side_effect=["msg_parent", "prt_parent"],
        )

        session_resp = _mock_response(
            mocker, status=200, json_data={"id": self.SESSION_ID}
        )
        prompt_resp = _mock_response(mocker, status=204)
        poll_empty = _mock_response(
            mocker,
            status=200,
            json_data=_messages_envelope([_user_message("msg_parent")]),
        )
        poll_done = _mock_response(
            mocker,
            status=200,
            json_data=_messages_envelope([
                _user_message("msg_parent"),
                _assistant_message("msg_parent", text_parts=["Hello"]),
            ]),
        )

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(side_effect=[session_resp, prompt_resp])
        mock_http.get = mocker.MagicMock(side_effect=[poll_empty, poll_done])
        client._http = mock_http

        result, sid = await client.send_prompt("my task")
        assert result == "Hello"
        assert sid == self.SESSION_ID
        assert mock_http.post.call_count == 2
        assert mock_http.get.call_count == 2

    # ------------------------------------------------------------------
    # reuse existing session
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_reuse_existing_session(self, mocker, client: OpenCodeClient) -> None:
        """Follow-up: session_id → prompt_async + poll (no session creation)."""
        mocker.patch("bot.opencode_client.asyncio.sleep", return_value=None)
        mocker.patch(
            "bot.opencode_client._generate_id",
            side_effect=["msg_parent", "prt_parent"],
        )

        prompt_resp = _mock_response(mocker, status=204)
        poll_done = _mock_response(
            mocker,
            status=200,
            json_data=_messages_envelope([
                _user_message("msg_parent"),
                _assistant_message("msg_parent", text_parts=["Reply"]),
            ]),
        )

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(return_value=prompt_resp)
        mock_http.get = mocker.MagicMock(return_value=poll_done)
        client._http = mock_http

        result, sid = await client.send_prompt("follow-up", session_id="ses_existing")
        assert result == "Reply"
        assert sid == "ses_existing"
        mock_http.post.assert_called_once()  # prompt_async only
        mock_http.get.assert_called_once()  # poll once → got result

    # ------------------------------------------------------------------
    # error: session creation fails
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_session_creation_fails(self, mocker, client: OpenCodeClient) -> None:
        """Non-200 on POST /session raises RuntimeError."""
        err_resp = _mock_response(mocker, status=500)
        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(return_value=err_resp)
        client._http = mock_http

        with pytest.raises(RuntimeError, match="500"):
            await client.send_prompt("fail")

    # ------------------------------------------------------------------
    # error: prompt_async fails
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_prompt_async_fails(self, mocker, client: OpenCodeClient) -> None:
        """Non-204 on prompt_async raises RuntimeError."""
        session_resp = _mock_response(
            mocker, status=200, json_data={"id": self.SESSION_ID}
        )
        err_resp = _mock_response(mocker, status=502)

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(side_effect=[session_resp, err_resp])
        client._http = mock_http

        with pytest.raises(RuntimeError, match="502"):
            await client.send_prompt("fail")

    # ------------------------------------------------------------------
    # error: connection error
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connection_error(self, mocker, client: OpenCodeClient) -> None:
        """aiohttp.ClientError raises ConnectionError."""
        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(
            side_effect=__import__("aiohttp").ClientError("connection refused")
        )
        client._http = mock_http

        with pytest.raises(ConnectionError, match="connection refused"):
            await client.send_prompt("test")

    # ------------------------------------------------------------------
    # error: polling timeout
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_poll_timeout(self, mocker, client: OpenCodeClient) -> None:
        """Timeout waiting for assistant response."""
        mocker.patch("bot.opencode_client.asyncio.sleep", return_value=None)
        mocker.patch(
            "bot.opencode_client._generate_id",
            side_effect=["msg_parent", "prt_parent"],
        )

        session_resp = _mock_response(
            mocker, status=200, json_data={"id": self.SESSION_ID}
        )
        prompt_resp = _mock_response(mocker, status=204)
        poll_resp = _mock_response(
            mocker,
            status=200,
            json_data=_messages_envelope([_user_message("msg_parent")]),
        )

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(side_effect=[session_resp, prompt_resp])
        mock_http.get = mocker.MagicMock(return_value=poll_resp)
        client._http = mock_http

        with pytest.raises(RuntimeError, match="did not respond within"):
            await client.send_prompt("test", timeout=1)

    # ------------------------------------------------------------------
    # error: get messages fails
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_messages_fails(self, mocker, client: OpenCodeClient) -> None:
        """Non-200 on polling raises RuntimeError."""
        session_resp = _mock_response(
            mocker, status=200, json_data={"id": self.SESSION_ID}
        )
        prompt_resp = _mock_response(mocker, status=204)
        poll_err = _mock_response(mocker, status=500)

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(side_effect=[session_resp, prompt_resp])
        mock_http.get = mocker.MagicMock(return_value=poll_err)
        client._http = mock_http

        with pytest.raises(RuntimeError, match="500"):
            await client.send_prompt("test", timeout=5)

    # ------------------------------------------------------------------
    # response with multiple text parts
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multi_text_parts(self, mocker, client: OpenCodeClient) -> None:
        """Multiple text parts in assistant response are concatenated."""
        mocker.patch("bot.opencode_client.asyncio.sleep", return_value=None)
        mocker.patch(
            "bot.opencode_client._generate_id",
            side_effect=["msg_parent", "prt_parent"],
        )

        session_resp = _mock_response(
            mocker, status=200, json_data={"id": self.SESSION_ID}
        )
        prompt_resp = _mock_response(mocker, status=204)
        poll_resp = _mock_response(
            mocker,
            status=200,
            json_data=_messages_envelope([
                _user_message("msg_parent"),
                _assistant_message("msg_parent", text_parts=["Part A", "Part B"]),
            ]),
        )

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(side_effect=[session_resp, prompt_resp])
        mock_http.get = mocker.MagicMock(return_value=poll_resp)
        client._http = mock_http

        result, sid = await client.send_prompt("task")
        assert result == "Part A\nPart B"
        assert sid == self.SESSION_ID

    # ------------------------------------------------------------------
    # close
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_close_session(self, client: OpenCodeClient) -> None:
        """close() cleans up the HTTP session."""
        mock_http = __import__("aiohttp").ClientSession()
        client._http = mock_http
        assert not client._http.closed

        await client.close()
        assert client._http.closed

    # ------------------------------------------------------------------
    # sync follow-up: error path
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_sync_follow_up_fails(
        self, mocker, client: OpenCodeClient
    ) -> None:
        """Non-204 from prompt_async on follow-up raises RuntimeError."""
        mocker.patch(
            "bot.opencode_client._generate_id",
            side_effect=["msg_parent", "prt_parent"],
        )

        err_resp = _mock_response(mocker, status=502)

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.post = mocker.MagicMock(return_value=err_resp)
        client._http = mock_http

        with pytest.raises(RuntimeError, match="502"):
            await client.send_prompt("fail", session_id="ses_existing")

    # ------------------------------------------------------------------
    # session-not-found → auto-retry with new session
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_stale_session_auto_retry(
        self, mocker, client: OpenCodeClient
    ) -> None:
        """Session not found → creates new session and retries once."""
        mocker.patch("bot.opencode_client.asyncio.sleep", return_value=None)
        mocker.patch(
            "bot.opencode_client._generate_id",
            side_effect=[
                "msg_old", "prt_old",       # first attempt (fails)
                "msg_new", "prt_new",       # second attempt (succeeds)
            ],
        )

        # First prompt_async → 404 "Session not found"
        not_found_resp = _mock_response(
            mocker,
            status=404,
            json_data={
                "name": "NotFoundError",
                "data": {"message": "Session not found: ses_dead"},
            },
        )
        not_found_resp.text = mocker.AsyncMock(
            return_value='{"name":"NotFoundError","data":{"message":"Session not found: ses_dead"}}'
        )

        # Session creation for the retry
        new_session_resp = _mock_response(
            mocker, status=200, json_data={"id": "ses_new123"}
        )

        # Second prompt_async → 204
        ok_resp = _mock_response(mocker, status=204)

        # Poll returns assistant answer
        poll_resp = _mock_response(
            mocker,
            status=200,
            json_data=_messages_envelope([
                _user_message("msg_new"),
                _assistant_message("msg_new", text_parts=["Recovered"]),
            ]),
        )

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        # post: prompt_async(404) → create_session(200) → prompt_async(204)
        mock_http.post = mocker.MagicMock(
            side_effect=[not_found_resp, new_session_resp, ok_resp]
        )
        mock_http.get = mocker.MagicMock(return_value=poll_resp)
        client._http = mock_http

        result, sid = await client.send_prompt("retry", session_id="ses_dead")
        assert result == "Recovered"
        assert sid == "ses_new123"
        # 3 POST calls: prompt_async(fail) → create_session → prompt_async(ok)
        assert mock_http.post.call_count == 3
        assert mock_http.get.call_count == 1

    # ------------------------------------------------------------------
    # _get_messages behaviour (used internally by poll)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_messages_with_envelope(
        self, mocker, client: OpenCodeClient
    ) -> None:
        """_get_messages unwraps {value: [...], Count: N} envelope."""
        msgs = [_user_message("m1")]
        envelope = _messages_envelope(msgs)

        get_resp = _mock_response(mocker, status=200, json_data=envelope)

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.get = mocker.MagicMock(return_value=get_resp)
        client._http = mock_http

        result = await client._get_messages(mock_http, "ses_test")
        assert result == msgs

    @pytest.mark.asyncio
    async def test_get_messages_list_direct(
        self, mocker, client: OpenCodeClient
    ) -> None:
        """_get_messages passes through a bare list."""
        msgs = [_user_message("m1"), _assistant_message("m1", text_parts=["Hi"])]

        get_resp = _mock_response(mocker, status=200, json_data=msgs)

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.get = mocker.MagicMock(return_value=get_resp)
        client._http = mock_http

        result = await client._get_messages(mock_http, "ses_test")
        assert result == msgs

    @pytest.mark.asyncio
    async def test_get_messages_http_error(
        self, mocker, client: OpenCodeClient
    ) -> None:
        """Non-200 from GET raises RuntimeError."""
        err_resp = _mock_response(mocker, status=500)

        mock_http = mocker.MagicMock()
        mock_http.closed = False
        mock_http.get = mocker.MagicMock(return_value=err_resp)
        client._http = mock_http

        with pytest.raises(RuntimeError, match="500"):
            await client._get_messages(mock_http, "ses_test")
