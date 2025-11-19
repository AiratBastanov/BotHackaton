import logging
import sys
from pathlib import Path

def setup_logging(log_level: str = "INFO", log_file: str = "bot.log") -> None:
    """Настраивает логирование для приложения"""
    
    # Создаем папку для логов если её нет
    log_path = Path(log_file)
    log_path.parent.mkdir(exist_ok=True)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Хендлер для файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # Хендлер для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Очищаем существующие хендлеры
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Добавляем наши хендлеры
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Устанавливаем уровень логирования для внешних библиотек
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
    
    logging.info("Логирование настроено успешно")


class BotLogger:
    """Упрощенный логгер для бота"""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, user_id: int = None) -> None:
        """Логирует информационное сообщение"""
        if user_id:
            message = f"[User {user_id}] {message}"
        self.logger.info(message)
    
    def warning(self, message: str, user_id: int = None) -> None:
        """Логирует предупреждение"""
        if user_id:
            message = f"[User {user_id}] {message}"
        self.logger.warning(message)
    
    def error(self, message: str, user_id: int = None, exc_info: bool = False) -> None:
        """Логирует ошибку"""
        if user_id:
            message = f"[User {user_id}] {message}"
        self.logger.error(message, exc_info=exc_info)
    
    def debug(self, message: str, user_id: int = None) -> None:
        """Логирует отладочное сообщение"""
        if user_id:
            message = f"[User {user_id}] {message}"
        self.logger.debug(message)