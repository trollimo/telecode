"""Tests for message handlers."""

import pytest
from unittest.mock import AsyncMock

from bot.config import Config
from bot.handlers import BotHandlers


def make_update(user_id: int, text: str = "test") -> dict:
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

    # Needed by handler interface
    setattr(update, "message", msg)

    return update, reply_mock


class TestHandleMessage:
    """Tests for handle_message()."""

    @pytest.mark.asyncio
    async def test_authorized_user_prompt_flow(self, mocker) -> None:
        """An authorized user's message triggers the OpenCode client."""
        mock_client = mocker.AsyncMock()
        mock_client.send_prompt = mocker.AsyncMock(return_value="response from OpenCode")
        config = Config(telegram_token="tok", allowed_user_id=123)
        handlers = BotHandlers(config, mock_client)

        update, reply_mock = make_update(user_id=123, text="hello world")
        context = mocker.MagicMock()

        await handlers.handle_message(update, context)

        mock_client.send_prompt.assert_awaited_once_with("hello world")
        reply_mock.assert_any_call("⏳ Отправляю задачу в OpenCode...")
        reply_mock.assert_any_call("response from OpenCode")

    @pytest.mark.asyncio
    async def test_unauthorized_user_rejected(self, mocker) -> None:
        """An unauthorized user gets a rejection message."""
        mock_client = mocker.AsyncMock()
        config = Config(telegram_token="tok", allowed_user_id=123)
        handlers = BotHandlers(config, mock_client)

        update, reply_mock = make_update(user_id=999, text="hello")
        context = mocker.MagicMock()

        await handlers.handle_message(update, context)

        mock_client.send_prompt.assert_not_called()
        reply_mock.assert_called_once_with(
            "Извините, у вас нет доступа к этому боту."
        )

    @pytest.mark.asyncio
    async def test_empty_text_is_ignored(self, mocker) -> None:
        """Empty or whitespace-only text does not trigger OpenCode."""
        mock_client = mocker.AsyncMock()
        config = Config(telegram_token="tok", allowed_user_id=123)
        handlers = BotHandlers(config, mock_client)

        update, reply_mock = make_update(user_id=123, text="   ")
        context = mocker.MagicMock()

        await handlers.handle_message(update, context)

        mock_client.send_prompt.assert_not_called()
        reply_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_opencode_error_shown_to_user(self, mocker) -> None:
        """When OpenCode raises, user sees an error message."""
        mock_client = mocker.AsyncMock()
        mock_client.send_prompt = mocker.AsyncMock(side_effect=ConnectionError("refused"))
        config = Config(telegram_token="tok", allowed_user_id=123)
        handlers = BotHandlers(config, mock_client)

        update, reply_mock = make_update(user_id=123, text="do something")
        context = mocker.MagicMock()

        await handlers.handle_message(update, context)

        reply_mock.assert_any_call("⏳ Отправляю задачу в OpenCode...")
        reply_mock.assert_any_call("❌ Ошибка при обработке запроса: refused")

    @pytest.mark.asyncio
    async def test_long_response_truncated(self, mocker) -> None:
        """Responses longer than 4000 chars are truncated."""
        long_response = "x" * 5000
        mock_client = mocker.AsyncMock()
        mock_client.send_prompt = mocker.AsyncMock(return_value=long_response)
        config = Config(telegram_token="tok", allowed_user_id=123)
        handlers = BotHandlers(config, mock_client)

        update, reply_mock = make_update(user_id=123, text="long task")
        context = mocker.MagicMock()

        await handlers.handle_message(update, context)

        # The reply should be at most 4000 + len("\n\n... (ответ обрезан до 4000 символов)")
        call_args = [
            c for c in reply_mock.call_args_list
            if c[0][0] != "⏳ Отправляю задачу в OpenCode..."
        ]
        assert call_args
        replied = call_args[0][0][0]
        assert len(replied) <= 4040
        assert replied.endswith("... (ответ обрезан до 4000 символов)")
