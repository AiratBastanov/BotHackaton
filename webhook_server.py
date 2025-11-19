import os
import logging
from aiohttp import web
from bot import CodeQueenBot

async def create_app():
    """Создает aiohttp приложение для вебхука"""
    app = web.Application()
    
    # Инициализируем бота
    bot = CodeQueenBot()
    app['bot'] = bot
    
    # Добавляем роуты
    app.router.add_post('/webhook', handle_webhook)
    app.router.add_get('/health', health_check)
    
    return app


async def handle_webhook(request):
    """Обработчик вебхука от Telegram"""
    bot = request.app['bot']
    
    try:
        # Получаем обновление от Telegram
        data = await request.json()
        update = Update.de_json(data, bot.application.bot)
        
        # Обрабатываем обновление
        await bot.application.process_update(update)
        
        return web.Response(status=200, text='OK')
    
    except Exception as e:
        logging.error(f"Ошибка обработки вебхука: {e}")
        return web.Response(status=500, text='Internal Server Error')


async def health_check(request):
    """Проверка здоровья приложения"""
    return web.Response(status=200, text='OK')


if __name__ == "__main__":
    # Для запуска через python webhook_server.py
    import asyncio
    
    async def main():
        app = await create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(runner, '0.0.0.0', 8443)
        await site.start()
        
        print("Вебхук сервер запущен на порту 8443")
        
        # Бесконечный цикл
        await asyncio.Event().wait()
    
    asyncio.run(main())