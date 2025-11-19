import aiohttp
import logging
from config import Config
from typing import Dict, Any


class HuggingFaceClient:
    """Асинхронный AI-клиент для HuggingFace Inference API"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.api_url = Config.HUGGINGFACE_API_URL
        self.token = Config.HUGGINGFACE_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def test_connection(self) -> bool:
        """Проверка API"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json={"inputs": "Hello"},
                    headers=self.headers,
                    timeout=10
                ) as r:
                    return r.status in (200, 503)

        except Exception as e:
            self.logger.error(f"Ошибка HF соединения: {e}")
            return False

    async def generate_response(self, user_message: str, conversation_history: list) -> str:
        """Генерация ответа модели"""

        prompt = self._build_prompt(conversation_history, user_message)
        payload = {"inputs": prompt}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=self.headers,
                    timeout=30
                ) as r:
                    data = await r.json()

                    # Ошибка HF
                    if isinstance(data, dict) and "error" in data:
                        return "⚠️ Ошибка модели: " + data["error"]

                    # HF Router output
                    if isinstance(data, dict) and "generated_text" in data:
                        return data["generated_text"]

                    # Classical HF list output
                    if isinstance(data, list) and "generated_text" in data[0]:
                        return data[0]["generated_text"]

                    return "⚠️ Пустой ответ от модели."

        except Exception as e:
            self.logger.error(f"HF API error: {e}")
            return "⚠️ Ошибка подключения к ИИ."

    def _build_prompt(self, history: list, user_message: str) -> str:
        prompt = ""

        for msg in history:
            prompt += f"{msg['role'].title()}: {msg['content']}\n"

        prompt += f"User: {user_message}\nAI:"
        return prompt

class AIService:
    """Улучшенный сервис для работы с AI"""
    
    def __init__(self):
        self.client = HuggingFaceClient()
        self.logger = logging.getLogger(__name__)
        self.request_count = 0
        self.error_count = 0
    
    def contains_inappropriate_content(self, text: str) -> bool:
        """Проверяет текст на наличие нежелательного контента"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Проверка запрещенных слов
        inappropriate_words = any(bad_word in text_lower for bad_word in config.BAD_WORDS)
        
        # Дополнительные проверки
        too_many_caps = sum(1 for c in text if c.isupper()) > len(text) * 0.7  # 70% заглавных
        too_many_repeats = any(text_lower.count(word) > 5 for word in text_lower.split()[:10])
        
        return inappropriate_words or too_many_caps or too_many_repeats
    
    def process_message(self, user_id: int, message: str, context_manager: 'ContextManager') -> str:
        """
        Обрабатывает сообщение пользователя и генерирует ответ
        
        Args:
            user_id: ID пользователя
            message: Текст сообщения
            context_manager: Менеджер контекста
        
        Returns:
            Ответ бота
        """
        self.request_count += 1
        
        try:
            # Проверяем на нежелательный контент
            if self.contains_inappropriate_content(message):
                self.logger.warning(f"Обнаружен нежелательный контент от пользователя {user_id}")
                self.error_count += 1
                return config.MESSAGES['content_warning']
            
            # Добавляем сообщение пользователя в контекст
            context_manager.add_user_message(user_id, message)
            
            # Получаем историю диалога
            conversation_history = context_manager.get_conversation_history(user_id)
            
            # Генерируем ответ
            ai_response = self.client.generate_response(conversation_history)
            
            if ai_response:
                # Добавляем ответ бота в контекст
                context_manager.add_bot_message(user_id, ai_response)
                return ai_response
            else:
                self.error_count += 1
                return config.MESSAGES['error']
                
        except Exception as e:
            self.logger.error(f"Ошибка при обработке сообщения: {e}")
            self.error_count += 1
            return config.MESSAGES['error']
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику сервиса"""
        return {
            'total_requests': self.request_count,
            'error_count': self.error_count,
            'success_rate': ((self.request_count - self.error_count) / self.request_count * 100) 
                            if self.request_count > 0 else 100
        }