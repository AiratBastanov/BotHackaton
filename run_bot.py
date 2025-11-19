#!/usr/bin/env python3
from bot import CodeQueenBot
from ai_client import HuggingFaceClient
import asyncio

async def main():
    bot = CodeQueenBot()

    # Проверяем HuggingFace API
    client = HuggingFaceClient()
    if client.test_connection():
        bot.logger.info("✅ Соединение с Hugging Face API установлено")
    else:
        bot.logger.warning("⚠️ Проблемы с соединением к Hugging Face API")

    # Проверяем токен Telegram
    bot_info = await bot.application.bot.get_me()
    bot.logger.info(f"🤖 Бот @{bot_info.username} запущен успешно")

    # Запуск polling — ВАЖНО: Application.run_polling() САМА стартует event loop
    await bot.application.initialize()
    await bot.application.start()
    await bot.application.run_polling()

if __name__ == "__main__":
    print("🤖 Запуск CodeQueen Bot...")
    print("Для остановки нажмите Ctrl+C")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")