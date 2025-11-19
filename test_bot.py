import unittest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from config import config
from context_manager import ContextManager, DialogContext
from ai_client import AIService, HuggingFaceClient
from filters import ContentFilter, InputValidator


class TestContextManager(unittest.TestCase):
    """Тесты для менеджера контекста"""
    
    def setUp(self):
        self.context_manager = ContextManager(max_context_length=5, session_timeout=3600)
        self.user_id = 12345
    
    def test_create_context(self):
        """Тест создания контекста"""
        context = self.context_manager.get_context(self.user_id)
        self.assertIsInstance(context, DialogContext)
        self.assertEqual(context.user_id, self.user_id)
    
    def test_add_messages(self):
        """Тест добавления сообщений"""
        self.context_manager.add_user_message(self.user_id, "Привет")
        self.context_manager.add_bot_message(self.user_id, "Привет! Как дела?")
        
        history = self.context_manager.get_conversation_history(self.user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]['role'], 'user')
        self.assertEqual(history[0]['content'], 'Привет')
        self.assertEqual(history[1]['role'], 'assistant')
        self.assertEqual(history[1]['content'], 'Привет! Как дела?')
    
    def test_context_limits(self):
        """Тест ограничения длины контекста"""
        for i in range(10):
            self.context_manager.add_user_message(self.user_id, f"Сообщение {i}")
        
        history = self.context_manager.get_conversation_history(self.user_id)
        self.assertEqual(len(history), 5)  # Должно быть ограничено max_context_length
    
    def test_clear_context(self):
        """Тест очистки контекста"""
        self.context_manager.add_user_message(self.user_id, "Тестовое сообщение")
        self.context_manager.clear_user_context(self.user_id)
        
        history = self.context_manager.get_conversation_history(self.user_id)
        self.assertEqual(len(history), 0)


class TestContentFilter(unittest.TestCase):
    """Тесты для фильтра контента"""
    
    def setUp(self):
        self.filter = ContentFilter()
    
    def test_bad_words_detection(self):
        """Тест обнаружения запрещенных слов"""
        self.assertTrue(self.filter.contains_bad_words("ты глупый бот"))
        self.assertTrue(self.filter.contains_bad_words("ненавижу тебя"))
        self.assertFalse(self.filter.contains_bad_words("привет как дела"))
    
    def test_filter_message(self):
        """Тест фильтрации сообщений"""
        is_clean, result = self.filter.filter_message("нормальное сообщение")
        self.assertTrue(is_clean)
        self.assertEqual(result, "нормальное сообщение")
        
        is_clean, result = self.filter.filter_message("глупый идиот")
        self.assertFalse(is_clean)
        self.assertEqual(result, config.MESSAGES['content_warning'])


class TestInputValidator(unittest.TestCase):
    """Тесты для валидатора ввода"""
    
    def test_message_validation(self):
        """Тест валидации сообщений"""
        # Валидные сообщения
        is_valid, msg = InputValidator.is_valid_message("Привет!")
        self.assertTrue(is_valid)
        self.assertEqual(msg, "OK")
        
        # Невалидные сообщения
        is_valid, msg = InputValidator.is_valid_message("")
        self.assertFalse(is_valid)
        
        is_valid, msg = InputValidator.is_valid_message("   ")
        self.assertFalse(is_valid)
    
    def test_text_sanitization(self):
        """Тест очистки текста"""
        text = "   много    пробелов   "
        sanitized = InputValidator.sanitize_text(text)
        self.assertEqual(sanitized, "много пробелов")
        
        # Тест обрезки длинного текста
        long_text = "а" * 1500
        sanitized = InputValidator.sanitize_text(long_text)
        self.assertTrue(len(sanitized) <= 1003)  # 1000 + "..."

class TestAIService(unittest.TestCase):
    """Тесты для AI сервиса"""
    
    def setUp(self):
        self.ai_service = AIService()
        self.context_manager = ContextManager()
        self.user_id = 12345
    
    def test_inappropriate_content(self):
        """Тест проверки нежелательного контента"""
        self.assertTrue(self.ai_service.contains_inappropriate_content("глупый бот"))
        self.assertFalse(self.ai_service.contains_inappropriate_content("привет как дела"))
    
    @patch('ai_client.HuggingFaceClient.generate_response')
    def test_process_message(self, mock_generate):
        """Тест обработки сообщения"""
        # Мокаем ответ AI
        mock_generate.return_value = "Это тестовый ответ от AI"
        
        response = self.ai_service.process_message(
            self.user_id, 
            "Тестовое сообщение", 
            self.context_manager
        )
        
        self.assertEqual(response, "Это тестовый ответ от AI")
        mock_generate.assert_called_once()
    
    @patch('ai_client.HuggingFaceClient.generate_response')
    def test_process_message_with_bad_content(self, mock_generate):
        """Тест обработки сообщения с нежелательным контентом"""
        response = self.ai_service.process_message(
            self.user_id,
            "глупый идиот",
            self.context_manager
        )
        
        self.assertEqual(response, config.MESSAGES['content_warning'])
        mock_generate.assert_not_called()  # AI не должен вызываться


class TestHuggingFaceClient(unittest.TestCase):
    """Тесты для клиента Hugging Face"""
    
    def setUp(self):
        self.client = HuggingFaceClient()
    
    def test_build_prompt(self):
        """Тест построения промпта"""
        history = [
            {'role': 'user', 'content': 'Привет'},
            {'role': 'assistant', 'content': 'Привет! Как дела?'},
            {'role': 'user', 'content': 'Хорошо, а у тебя?'}
        ]
        
        prompt = self.client._build_prompt(history)
        self.assertIn("Пользователь: Привет", prompt)
        self.assertIn("Ассистент: Привет! Как дела?", prompt)
        self.assertIn("Пользователь: Хорошо, а у тебя?", prompt)
        self.assertIn("Ассистент:", prompt)
    
    def test_extract_generated_text(self):
        """Тест извлечения сгенерированного текста"""
        # Тест с правильным форматом ответа
        response_data = [{'generated_text': 'Тестовый ответ'}]
        text = self.client._extract_generated_text(response_data)
        self.assertEqual(text, 'Тестовый ответ')
        
        # Тест с пустым ответом
        text = self.client._extract_generated_text([])
        self.assertIsNone(text)


if __name__ == "__main__":
    # Запуск тестов
    unittest.main(verbosity=2)