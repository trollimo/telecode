"""Telegram message handlers."""

import logging

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from bot.config import Config
from bot.opencode_client import OpenCodeClient

logger = logging.getLogger(__name__)


class BotHandlers:
    """Wires Telegram handlers to bot logic."""

    def __init__(self, config: Config, opencode_client: OpenCodeClient) -> None:
        self._config = config
        self._opencode_client = opencode_client

    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "Привет! Я бот для связи с OpenCode.\n"
            "Просто напиши мне задачу, и я передам её в OpenCode."
        )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages.

        Only processes messages from the configured allowed user.
        Sends the text to OpenCode and returns the response.
        """
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != self._config.allowed_user_id:
            logger.warning("Unauthorized access attempt from user %s", user_id)
            await update.message.reply_text("Извините, у вас нет доступа к этому боту.")
            return

        user_text = update.message.text.strip()
        if not user_text:
            return

        await update.message.reply_text("⏳ Отправляю задачу в OpenCode...")

        try:
            result = await self._opencode_client.send_prompt(user_text)
            # Telegram has a 4096 char limit per message
            if len(result) > 4000:
                result = result[:4000] + "\n\n... (ответ обрезан до 4000 символов)"
            await update.message.reply_text(result)
        except Exception as e:
            logger.exception("Failed to process prompt via OpenCode")
            await update.message.reply_text(f"❌ Ошибка при обработке запроса: {e}")

    def register(self, app) -> None:
        """Register all handlers on the Application."""
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
