import asyncio
import logging
import time
from typing import Optional, Dict, Any
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
    CallbackContext
)

from config import config
from logging_config import setup_logging, BotLogger
from context_manager import ContextManager
from ai_client import AIService, HuggingFaceClient
from filters import content_filter, input_validator

class CodeQueenBot:
    """Улучшенный Telegram бот для хакатона 'Королева Кода'"""
    
    def __init__(self):
        # Настройка логирования
        setup_logging(log_level="INFO", log_file="logs/bot.log")
        self.logger = BotLogger("CodeQueenBot")
        
        # Статистика бота
        self.start_time = time.time()
        self.message_count = 0
        self.user_count = 0
        
        # Инициализация компонентов
        self.context_manager = ContextManager(
            max_context_length=config.MAX_CONTEXT_LENGTH,
            session_timeout=config.SESSION_TIMEOUT
        )
        self.ai_service = AIService()
        
        # Создаем приложение Telegram
        self.application = self._create_application()
        
        self.logger.info("CodeQueenBot инициализирован успешно")
    
    def _create_application(self) -> Application:
        """Создает и настраивает приложение Telegram"""
        
        application = Application.builder()\
            .token(config.TELEGRAM_BOT_TOKEN)\
            .build()
        
        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("about", self.about_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        application.add_handler(CommandHandler("status", self.status_command))
        application.add_handler(CommandHandler("stats", self.stats_command))
        
        # Добавляем обработчик текстовых сообщений
        application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message
            )
        )
        
        # Добавляем обработчик для нетестовых сообщений
        application.add_handler(
            MessageHandler(
                filters.ALL & ~filters.TEXT & ~filters.COMMAND,
                self.handle_unsupported_message
            )
        )
        
        # Добавляем обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        self.logger.info("Обработчики команд зарегистрированы")
        return application
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        self.message_count += 1
        self.user_count += 1
        
        self.logger.info(f"Команда /start от пользователя {user.id} ({user.first_name})")
        
        welcome_message = config.MESSAGES['welcome']
        
        await update.message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        # Добавляем приветственное сообщение в контекст
        self.context_manager.add_bot_message(user.id, welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help"""
        user = update.effective_user
        self.message_count += 1
        
        self.logger.info(f"Команда /help от пользователя {user.id}")
        
        help_message = config.MESSAGES['help']
        
        await update.message.reply_text(
            help_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    async def about_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /about"""
        user = update.effective_user
        self.message_count += 1
        
        self.logger.info(f"Команда /about от пользователя {user.id}")
        
        about_message = config.MESSAGES['about']
        
        await update.message.reply_text(
            about_message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /reset"""
        user = update.effective_user
        self.message_count += 1
        
        self.logger.info(f"Команда /reset от пользователя {user.id}")
        
        success = self.context_manager.clear_user_context(user.id)
        
        if success:
            await update.message.reply_text(config.MESSAGES['reset_success'])
        else:
            await update.message.reply_text("Контекст уже пуст!")
    
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /status - публичная версия статистики"""
        user = update.effective_user
        self.message_count += 1
        
        self.logger.info(f"Команда /status от пользователя {user.id}")
        
        # Проверяем соединение с AI
        client = HuggingFaceClient()
        ai_status = "🟢 Доступен" if client.test_connection() else "🔴 Недоступен"
        
        uptime = time.time() - self.start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        status_message = (
            "📊 **Статус бота**\n\n"
            f"• AI сервис: {ai_status}\n"
            f"• Время работы: {int(hours)}ч {int(minutes)}м {int(seconds)}с\n"
            f"• Активных диалогов: {self.context_manager.get_stats()['active_contexts']}\n"
            f"• Всего сообщений: {self.message_count}\n\n"
            "_Бот работает в штатном режиме_"
        )
        
        await update.message.reply_text(
            status_message,
            parse_mode='Markdown'
        )
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /stats (расширенная статистика)"""
        user = update.effective_user
        self.message_count += 1
        
        self.logger.info(f"Команда /stats от пользователя {user.id}")
        
        stats = self.context_manager.get_stats()
        user_context = self.context_manager.get_context(user.id)
        user_info = user_context.get_user_info()
        ai_stats = self.ai_service.get_stats()
        
        uptime = time.time() - self.start_time
        hours, remainder = divmod(uptime, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        stats_message = (
            "📈 **Расширенная статистика**\n\n"
            f"• Время работы: {int(hours)}ч {int(minutes)}м\n"
            f"• Всего пользователей: {self.user_count}\n"
            f"• Всего сообщений: {self.message_count}\n"
            f"• Активных диалогов: {stats['active_contexts']}\n"
            f"• AI запросов: {ai_stats['total_requests']}\n"
            f"• Успешных ответов: {ai_stats['success_rate']:.1f}%\n"
            f"• Ваших сообщений: {user_info['message_count']}\n"
            f"• Размер контекста: {stats['max_context_length']}\n\n"
            "_Статистика для мониторинга_"
        )
        
        await update.message.reply_text(
            stats_message,
            parse_mode='Markdown'
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстовых сообщений"""
        user = update.effective_user
        message_text = update.message.text
        self.message_count += 1
        
        self.logger.info(f"Сообщение от {user.id} ({user.first_name}): {message_text[:50]}...")
        
        # Валидация сообщения
        is_valid, validation_msg = input_validator.is_valid_message(message_text)
        if not is_valid:
            if "длинное" in validation_msg:
                await update.message.reply_text(config.MESSAGES['message_too_long'])
            else:
                await update.message.reply_text(config.MESSAGES['empty_message'])
            return
        
        # Очистка текста
        clean_text = input_validator.sanitize_text(message_text)
        
        # Проверка на нежелательный контент
        is_clean, filter_result = content_filter.filter_message(clean_text)
        if not is_clean:
            await update.message.reply_text(filter_result)
            return
        
        # Отправляем сообщение о обработке
        processing_msg = await update.message.reply_text(config.MESSAGES['processing'])
        
        try:
            # Обрабатываем сообщение через AI сервис (асинхронно)
            bot_response = await asyncio.get_event_loop().run_in_executor(
                None,
                self.ai_service.process_message,
                user.id,
                clean_text,
                self.context_manager
            )
            
            # Удаляем сообщение "обрабатываю"
            await processing_msg.delete()
            
            # Отправляем ответ
            if bot_response:
                await update.message.reply_text(bot_response)
            else:
                await update.message.reply_text(config.MESSAGES['error'])
                
        except asyncio.TimeoutError:
            self.logger.error(f"Таймаут при обработке сообщения от пользователя {user.id}")
            await processing_msg.delete()
            await update.message.reply_text(config.MESSAGES['api_timeout'])
            
        except Exception as e:
            self.logger.error(f"Ошибка при обработке сообщения: {e}", user_id=user.id, exc_info=True)
            
            # Удаляем сообщение "обрабатываю" в случае ошибки
            try:
                await processing_msg.delete()
            except:
                pass
            
            await update.message.reply_text(config.MESSAGES['error'])
    
    async def handle_unsupported_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик неподдерживаемых типов сообщений"""
        user = update.effective_user
        self.message_count += 1
        
        self.logger.info(f"Неподдерживаемое сообщение от пользователя {user.id}")
        
        await update.message.reply_text(
            "🤖 Я пока умею работать только с текстовыми сообщениями. "
            "Напишите мне текстом, и я с радостью помогу!"
        )
    
    async def error_handler(self, update: Update, context: CallbackContext) -> None:
        """Обработчик ошибок"""
        try:
            user_id = update.effective_user.id if update.effective_user else "unknown"
            self.logger.error(
                f"Исключение при обработке обновления: {context.error}", 
                user_id=user_id,
                exc_info=True
            )
            
            # Можно отправить сообщение пользователю об ошибке
            if update and update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "⚠️ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже."
                    )
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Ошибка в обработчике ошибок: {e}", exc_info=True)
    
    async def run_webhook(self, webhook_url: str = None, port: int = None) -> None:
        """Запускает бота в режиме webhook"""
        webhook_url = webhook_url or config.WEBHOOK_URL
        port = port or config.PORT
        
        if not webhook_url:
            self.logger.error("WEBHOOK_URL не указан в конфигурации")
            return
        
        self.logger.info(f"Запуск бота в режиме webhook: {webhook_url}:{port}")
        
        try:
            # Устанавливаем webhook
            await self.application.bot.set_webhook(
                url=webhook_url,
                drop_pending_updates=True,
                max_connections=40
            )
            
            self.logger.info(f"Webhook установлен: {webhook_url}")
            
        except Exception as e:
            self.logger.error(f"Ошибка при установке webhook: {e}")
            raise
    
    async def run_polling(self) -> None:
        """Запускает бота в режиме polling (для разработки)"""
        self.logger.info("Запуск бота в режиме polling...")
        
        try:
            # Очищаем вебхук если он был установлен
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            
            self.logger.info("Webhook очищен, запускаем polling...")
            
            # Запускаем polling
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            
        except Exception as e:
            self.logger.error(f"Ошибка при запуске polling: {e}")
            raise
    
    async def shutdown(self) -> None:
        """Корректное завершение работы бота"""
        self.logger.info("Завершение работы бота...")
        
        try:
            # Очищаем вебхук
            await self.application.bot.delete_webhook()
            self.logger.info("Webhook очищен")
        except Exception as e:
            self.logger.error(f"Ошибка при очистке webhook: {e}")
        
        # Останавливаем приложение
        await self.application.shutdown()
        
        self.logger.info("Бот завершил работу")


async def main_async():
    """Асинхронная основная функция запуска бота"""
    bot = CodeQueenBot()
    
    try:
        # Проверяем соединение с Hugging Face
        client = HuggingFaceClient()
        if client.test_connection():
            bot.logger.info("✅ Соединение с Hugging Face API установлено")
        else:
            bot.logger.warning("⚠️ Проблемы с соединением к Hugging Face API")
        
        # Проверяем токен бота (асинхронно)
        bot_info = await bot.application.bot.get_me()
        bot.logger.info(f"🤖 Бот @{bot_info.username} запущен успешно")
        
        # Запускаем бота в режиме polling (асинхронно)
        await bot.run_polling()
        
    except KeyboardInterrupt:
        bot.logger.info("Получен сигнал прерывания")
    except Exception as e:
        bot.logger.error(f"Критическая ошибка: {e}", exc_info=True)
    finally:
        await bot.shutdown()


def main():
    """Основная функция запуска бота"""
    # Запускаем асинхронную функцию
    asyncio.run(main_async())


if __name__ == "__main__":
    # Запускаем бота
    main()