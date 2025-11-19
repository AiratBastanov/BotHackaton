import re
import logging
from typing import List, Set
from config import config

class ContentFilter:
    """Класс для фильтрации нежелательного контента"""
    
    def __init__(self):
        self.bad_words = set(config.BAD_WORDS)
        self.logger = logging.getLogger(__name__)
        
        # Регулярные выражения для более сложных проверок
        self.patterns = [
            re.compile(r'\b(?:[a-z]*[x]{2,}[a-z]*)\b', re.IGNORECASE),  # Маскированный мат (xx)
            re.compile(r'\b(?:[a-z]*[0-9]{2,}[a-z]*)\b', re.IGNORECASE),  # Замена букв цифрами
        ]
    
    def contains_bad_words(self, text: str) -> bool:
        """Проверяет текст на наличие запрещенных слов"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Простая проверка по словам
        for bad_word in self.bad_words:
            if bad_word in text_lower:
                return True
        
        # Проверка по регулярным выражениям
        for pattern in self.patterns:
            if pattern.search(text):
                return True
        
        return False
    
    def filter_message(self, text: str) -> tuple[bool, str]:
        """
        Фильтрует сообщение и возвращает результат
        
        Returns:
            (is_clean, filtered_text_or_warning)
        """
        if self.contains_bad_words(text):
            self.logger.warning(f"Обнаружен нежелательный контент: {text}")
            return False, config.MESSAGES['content_warning']
        
        return True, text
    
    def add_custom_words(self, words: List[str]) -> None:
        """Добавляет пользовательские слова в фильтр"""
        self.bad_words.update(word.lower() for word in words)
        self.logger.info(f"Добавлено {len(words)} пользовательских слов в фильтр")


class InputValidator:
    """Класс для валидации пользовательского ввода"""
    
    @staticmethod
    def is_valid_message(text: str) -> tuple[bool, str]:
        """Проверяет валидность сообщения"""
        if not text or not text.strip():
            return False, "Пустое сообщение"
        
        if len(text.strip()) < 1:
            return False, "Слишком короткое сообщение"
        
        if len(text) > 1000:
            return False, "Сообщение слишком длинное"
        
        # Проверка на повторяющиеся символы (спам)
        if re.search(r'(.)\1{10,}', text):  # 10+ одинаковых символов подряд
            return False, "Сообщение содержит слишком много повторяющихся символов"
        
        return True, "OK"
    
    @staticmethod
    def sanitize_text(text: str) -> str:
        """Очищает текст от потенциально опасных символов"""
        # Убираем крайние пробелы
        text = text.strip()
        
        # Заменяем множественные пробелы на один
        text = re.sub(r'\s+', ' ', text)
        
        # Обрезаем до разумной длины
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        return text


# Создаем экземпляры фильтров
content_filter = ContentFilter()
input_validator = InputValidator()