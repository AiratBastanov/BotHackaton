import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import Config
from ai_client import HuggingFaceClient
from context_manager import ContextManager
from filters import content_filter
from logging_config import setup_logging


class CodeQueenBot:
    """Telegram бот с AI-интеграцией"""

    def __init__(self):
        setup_logging()
        self.logger = logging.getLogger("bot")

        self.ai = HuggingFaceClient()
        self.context_manager = ContextManager()

        self.application = (
            Application.builder()
            .token(Config.TELEGRAM_BOT_TOKEN)
            .build()
        )

        self._register_handlers()

    def _register_handlers(self):
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("about", self.cmd_about))
        self.application.add_handler(CommandHandler("reset", self.cmd_reset))

        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            )
        )

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Привет! Я CodeQueen 🤖\nЗадай мне любой вопрос!"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "/start – приветствие\n"
            "/about – о боте\n"
            "/reset – сброс диалога\n"
            "/help – помощь"
        )

    async def cmd_about(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "CodeQueen Bot — Telegram бот с AI.\n"
            "Работаю на HuggingFace Inference API."
        )

    async def cmd_reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.message.from_user.id
        self.context_manager.reset_context(uid)
        await update.message.reply_text("Контекст очищен 🔄")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_text = update.message.text
        user_id = update.message.from_user.id

        # Фильтрация мата
        is_clean, msg = content_filter.filter_message(user_text)
        if not is_clean:
            await update.message.reply_text(msg)
            return

        # История
        history = self.context_manager.get_context(user_id)

        # AI ответ
        ai_reply = await self.ai.generate_response(
            user_message=user_text,
            conversation_history=history
        )

        # Сохраняем
        self.context_manager.append_to_context(
            user_id, user_text, ai_reply
        )

        await update.message.reply_text(ai_reply)