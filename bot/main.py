"""Telegram bot entrypoint — bridges Telegram messages to OpenCode."""

import asyncio
import logging
import signal

from telegram.ext import ApplicationBuilder

from bot.config import load_config
from bot.handlers import BotHandlers
from bot.opencode_client import OpenCodeClient

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the Telegram bot and connect to OpenCode."""
    config = load_config()

    opencode_client = OpenCodeClient(config)
    handlers = BotHandlers(config, opencode_client)

    app = ApplicationBuilder().token(config.telegram_token).build()
    handlers.register(app)

    # Graceful shutdown via signal
    stop_event = asyncio.Event()

    def _shutdown() -> None:
        logger.info("Shutdown signal received, stopping...")
        stop_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _shutdown)
        except NotImplementedError:
            # Windows does not support add_signal_handler
            pass

    # Start the application
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    logger.info("Bot started. Polling for messages...")

    try:
        await stop_event.wait()
    finally:
        logger.info("Stopping...")
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await opencode_client.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
