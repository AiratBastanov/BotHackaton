#!/usr/bin/env python3
import asyncio
from bot import CodeQueenBot
from ai_client import HuggingFaceClient


async def start_bot():
    bot = CodeQueenBot()
    client = HuggingFaceClient()

    # Проверяем соединение с HuggingFace
    if await client.test_connection():
        bot.logger.info("✅ Hugging Face API работает корректно")
    else:
        bot.logger.warning("⚠️ Проблемы с подключением к HF API")

    # Информация о боте
    me = await bot.application.bot.get_me()
    bot.logger.info(f"🤖 Бот @{me.username} готов к работе")

    # ВАЖНО: run_polling НАЧИНАЕТ event loop САМА
    await bot.application.initialize()
    await bot.application.start()
    await bot.application.run_polling()   # ← больше НИЧЕГО не вызываем вокруг неё
    await bot.application.stop()


def main():
    print("🤖 Запуск CodeQueen Bot...")
    asyncio.run(start_bot())   # ← единственный event loop


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")