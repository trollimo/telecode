"""Tests for message handlers — multi-turn sessions."""

import pytest
from unittest.mock import AsyncMock

from bot.config import Config
from bot.handlers import BotHandlers


SESSION_ID = "ses_test123"


def make_update(user_id: int, text: str = "test"):
    """Build a fake Update with a message and an auto-reply mock.

    Returns (update_mock, reply_mock) tuple so tests can assert
    on reply calls.
    """
    reply_mock = AsyncMock()
    msg = AsyncMock()
    msg.text = text
    msg.reply_text = reply_mock

    user = AsyncMock()
    user.id = user_id

    update = AsyncMock()
    update.effective_user = user
    update.message = msg
    setattr(update, "message", msg)

    return update, reply_mock


def make_handlers(mocker, send_prompt_return="response from OpenCode", **kwargs):
    """Build BotHandlers with a mocked OpenCodeClient.

    ``send_prompt`` returns ``(text, session_id)`` by default.
    Override with ``send_prompt_return=(text, sid)`` or set
    ``send_prompt_side_effect`` for exceptions.
    """
    mock_client = mocker.AsyncMock()
    side_effect = kwargs.pop("send_prompt_side_effect", None)

    if side_effect is not None:
        mock_client.send_prompt = mocker.AsyncMock(side_effect=side_effect)
    else:
        ret = kwargs.get("send_prompt_return", send_prompt_return)
        if isinstance(ret, tuple):
            mock_client.send_prompt = mocker.AsyncMock(return_value=ret)
        else:
            mock_client.send_prompt = mocker.AsyncMock(
                return_value=(ret, SESSION_ID)
            )

    config = Config(telegram_token="tok", allowed_user_id=123)
    return BotHandlers(config, mock_client), mock_client


class TestHandleMessage:
    """Tests for handle_message()."""

    @pytest.mark.asyncio
    async def test_authorized_user_prompt_flow(self, mocker) -> None:
        """An authorized user's message triggers the OpenCode client."""
        handlers, mock_client = make_handlers(mocker)

        update, reply_mock = make_update(user_id=123, text="hello world")
        await handlers.handle_message(update, mocker.MagicMock())

        mock_client.send_prompt.assert_awaited_once_with(
            "hello world", session_id=None
        )
        reply_mock.assert_any_call("⏳ Отправляю задачу в OpenCode...")
        reply_mock.assert_any_call("response from OpenCode")

    @pytest.mark.asyncio
    async def test_session_persisted_across_messages(self, mocker) -> None:
        """Session ID is stored and reused on the next message."""
        handlers, mock_client = make_handlers(mocker)

        # First message — session_id=None → returns ses_first
        mock_client.send_prompt = mocker.AsyncMock(
            return_value=("first reply", "ses_first")
        )
        update1, _ = make_update(user_id=123, text="first")
        await handlers.handle_message(update1, mocker.MagicMock())
        mock_client.send_prompt.assert_awaited_with("first", session_id=None)

        # Second message — should reuse ses_first
        mock_client.send_prompt = mocker.AsyncMock(
            return_value=("second reply", "ses_second")
        )
        update2, _ = make_update(user_id=123, text="second")
        await handlers.handle_message(update2, mocker.MagicMock())
        mock_client.send_prompt.assert_awaited_with("second", session_id="ses_first")

    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self, mocker) -> None:
        """An unauthorized user gets a rejection message."""
        handlers, mock_client = make_handlers(mocker)

        update, reply_mock = make_update(user_id=999, text="hello")
        await handlers.handle_message(update, mocker.MagicMock())

        mock_client.send_prompt.assert_not_called()
        reply_mock.assert_called_once_with(
            "Извините, у вас нет доступа к этому боту."
        )

    @pytest.mark.asyncio
    async def test_empty_text_is_ignored(self, mocker) -> None:
        """Empty or whitespace-only text does not trigger OpenCode."""
        handlers, mock_client = make_handlers(mocker)

        update, reply_mock = make_update(user_id=123, text="   ")
        await handlers.handle_message(update, mocker.MagicMock())

        mock_client.send_prompt.assert_not_called()
        reply_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_opencode_error_shown_to_user(self, mocker) -> None:
        """When OpenCode raises, user sees an error message."""
        handlers, _ = make_handlers(
            mocker, send_prompt_side_effect=ConnectionError("refused")
        )

        update, reply_mock = make_update(user_id=123, text="do something")
        await handlers.handle_message(update, mocker.MagicMock())

        reply_mock.assert_any_call("⏳ Отправляю задачу в OpenCode...")
        reply_mock.assert_any_call("❌ Ошибка при обработке запроса: refused")

    @pytest.mark.asyncio
    async def test_long_response_truncated(self, mocker) -> None:
        """Responses longer than 4000 chars are truncated."""
        long_response = "x" * 5000
        handlers, mock_client = make_handlers(mocker)
        mock_client.send_prompt = mocker.AsyncMock(
            return_value=(long_response, "ses_abc")
        )

        update, reply_mock = make_update(user_id=123, text="long task")
        await handlers.handle_message(update, mocker.MagicMock())

        # The reply should be at most 4000 + suffix length
        call_args = [
            c for c in reply_mock.call_args_list
            if c[0][0] != "⏳ Отправляю задачу в OpenCode..."
        ]
        assert call_args
        replied = call_args[0][0][0]
        assert len(replied) <= 4040
        assert replied.endswith("... (ответ обрезан до 4000 символов)")


class TestResetCommand:
    """Tests for /reset command."""

    @pytest.mark.asyncio
    async def test_reset_clears_session(self, mocker) -> None:
        """/reset clears the stored session and confirms."""
        handlers, mock_client = make_handlers(mocker)

        # Establish a session first
        mock_client.send_prompt = mocker.AsyncMock(
            return_value=("reply", "ses_active")
        )
        update1, _ = make_update(user_id=123, text="hello")
        await handlers.handle_message(update1, mocker.MagicMock())
        assert handlers._sessions.get(123) == "ses_active"

        # /reset clears it
        update2, reply_mock = make_update(user_id=123)
        await handlers.reset(update2, mocker.MagicMock())

        assert 123 not in handlers._sessions
        reply_mock.assert_called_once_with("✅ Контекст разговора сброшен.")

    @pytest.mark.asyncio
    async def test_reset_without_active_session(self, mocker) -> None:
        """/reset without an active session shows an info message."""
        handlers, _ = make_handlers(mocker)
        assert not handlers._sessions

        update, reply_mock = make_update(user_id=123)
        await handlers.reset(update, mocker.MagicMock())

        reply_mock.assert_called_once_with(
            "Нет активного разговора для сброса."
        )
