"""Telegram message handlers — multi-turn OpenCode sessions."""

import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import Config
from bot.opencode_client import OpenCodeClient

logger = logging.getLogger(__name__)


class BotHandlers:
    """Wires Telegram handlers to bot logic.

    Each authorised user gets a persistent OpenCode session so that
    follow-up messages continue the same conversation (multi-turn).
    """

    def __init__(self, config: Config, opencode_client: OpenCodeClient) -> None:
        self._config = config
        self._client = opencode_client
        # user_id → active OpenCode session_id
        self._sessions: dict[int, str] = {}

    @staticmethod
    async def start(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "Привет! Я бот для связи с OpenCode.\n\n"
            "Просто напиши задачу, и я передам её в OpenCode.\n"
            "Бот запоминает контекст разговора — можно уточнять и "
            "задавать follow-up вопросы.\n"
            "/reset — начать новый разговор (сбросить контекст)."
        )

    async def reset(self, update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset — clear the user's session."""
        user_id = update.effective_user.id if update.effective_user else None
        if user_id and user_id in self._sessions:
            del self._sessions[user_id]
            await update.message.reply_text("✅ Контекст разговора сброшен.")
        else:
            await update.message.reply_text("Нет активного разговора для сброса.")

    async def handle_message(
        self, update: Update, _context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle incoming text messages.

        Only processes messages from the configured allowed user.
        Reuses the user's active OpenCode session when possible.
        """
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != self._config.allowed_user_id:
            logger.warning("Unauthorized access attempt from user %s", user_id)
            if update.message:
                await update.message.reply_text(
                    "Извините, у вас нет доступа к этому боту."
                )
            return

        user_text = update.message.text.strip()
        if not user_text:
            return

        session_id = self._sessions.get(user_id)
        await update.message.reply_text("⏳ Отправляю задачу в OpenCode...")

        try:
            result, session_id = await self._client.send_prompt(
                user_text, session_id=session_id
            )

            # Persist session for follow-up messages
            self._sessions[user_id] = session_id

            # Telegram has a 4096 char limit per message
            if len(result) > 4000:
                result = result[:4000] + "\n\n... (ответ обрезан до 4000 символов)"

            if result:
                await update.message.reply_text(result)
            else:
                logger.info("Empty response from OpenCode for user %s", user_id)

        except Exception as e:
            logger.exception("Failed to process prompt via OpenCode")
            await update.message.reply_text(
                f"❌ Ошибка при обработке запроса: {e}"
            )
            # Keep the session alive on error too — user may retry

    def register(self, app) -> None:
        """Register all handlers on the Application."""
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("reset", self.reset))
        app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
