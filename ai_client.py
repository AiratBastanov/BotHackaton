import requests
import logging
import json
import time
from typing import List, Dict, Any, Optional
from cachetools import TTLCache
from config import config

class HuggingFaceClient:
    """Улучшенный клиент для работы с Hugging Face API с кэшированием и повторными попытками"""
    
    def __init__(self):
        # ИСПРАВЛЕНО: новый endpoint
        self.api_url = config.HUGGINGFACE_API_URL
        self.headers = {
            "Authorization": f"Bearer {config.HUGGINGFACE_TOKEN}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
        
        # Кэш для повторяющихся запросов (TTL 5 минут)
        self.cache = TTLCache(maxsize=100, ttl=300)
        
        # Настройки для генерации текста
        self.generation_params = {
            "max_length": 200,
            "min_length": 20,
            "temperature": 0.8,
            "top_p": 0.9,
            "repetition_penalty": 1.1,
            "do_sample": True,
            "return_full_text": False,
            "num_return_sequences": 1
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        # Таймаут для запросов
        self.timeout = config.REQUEST_TIMEOUT
    
    def generate_response(self, conversation_history: List[Dict[str, str]]) -> Optional[str]:
        """
        Генерирует ответ на основе истории диалога с повторными попытками
        
        Args:
            conversation_history: История диалога в формате [{'role': 'user', 'content': '...'}, ...]
        
        Returns:
            Сгенерированный текст или None в случае ошибки
        """
        # Создаем ключ кэша на основе истории
        cache_key = str(hash(str(conversation_history)))
        
        # Проверяем кэш
        if cache_key in self.cache:
            self.logger.info("Используем кэшированный ответ")
            return self.cache[cache_key]
        
        for attempt in range(config.MAX_RETRIES):
            try:
                # Формируем промпт из истории диалога
                prompt = self._build_prompt(conversation_history)
                
                if not prompt:
                    return "Привет! Как я могу вам помочь?"
                
                payload = {
                    "inputs": prompt,
                    "parameters": self.generation_params
                }
                
                self.logger.info(f"Попытка {attempt + 1}: Отправка запроса к Hugging Face API")
                
                response = self.session.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = self._extract_generated_text(result)
                    
                    if generated_text:
                        # Очищаем и форматируем ответ
                        cleaned_text = self._clean_response(generated_text)
                        self.logger.info(f"Успешный ответ от AI: {cleaned_text[:100]}...")
                        
                        # Сохраняем в кэш
                        self.cache[cache_key] = cleaned_text
                        return cleaned_text
                    else:
                        self.logger.warning("Пустой ответ от модели")
                        if attempt == config.MAX_RETRIES - 1:
                            return "Извините, не удалось сгенерировать ответ. Попробуйте еще раз."
                
                elif response.status_code == 503:
                    # Модель загружается
                    wait_time = (attempt + 1) * 5  # Увеличиваем время ожидания
                    self.logger.warning(f"Модель загружается, ждем {wait_time} секунд...")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code == 429:
                    # Слишком много запросов
                    self.logger.warning("Превышен лимит запросов, ждем...")
                    time.sleep(10)
                    continue
                
                else:
                    self.logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                    if attempt == config.MAX_RETRIES - 1:
                        return None
                        
            except requests.exceptions.Timeout:
                self.logger.error(f"Таймаут при запросе к Hugging Face API (попытка {attempt + 1})")
                if attempt == config.MAX_RETRIES - 1:
                    return config.MESSAGES['api_timeout']
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Ошибка сети (попытка {attempt + 1}): {e}")
                if attempt == config.MAX_RETRIES - 1:
                    return None
                    
            except Exception as e:
                self.logger.error(f"Неожиданная ошибка (попытка {attempt + 1}): {e}")
                if attempt == config.MAX_RETRIES - 1:
                    return None
        
        return None
    
    def _build_prompt(self, conversation_history: List[Dict[str, str]]) -> str:
        """Строит промпт из истории диалога"""
        if not conversation_history:
            return "Ты полезный AI-ассистент. Начни разговор приветствием."
        
        # Берем только последние сообщения для промпта (учитываем ограничения токенов)
        recent_history = conversation_history[-6:]  # Немного больше для лучшего контекста
        
        prompt_parts = ["Ты - полезный AI-ассистент для Telegram бота. Веди естественную беседу."]
        
        for msg in recent_history:
            if msg['role'] == 'user':
                prompt_parts.append(f"Пользователь: {msg['content']}")
            elif msg['role'] == 'assistant':
                prompt_parts.append(f"Ассистент: {msg['content']}")
        
        # Добавляем текущий запрос ассистента
        prompt_parts.append("Ассистент:")
        
        return "\n".join(prompt_parts)
    
    def _extract_generated_text(self, response_data: Any) -> Optional[str]:
        """Извлекает сгенерированный текст из ответа API"""
        try:
            # Обрабатываем разные форматы ответа Hugging Face API
            if isinstance(response_data, list):
                for item in response_data:
                    if isinstance(item, dict):
                        if 'generated_text' in item:
                            text = item['generated_text']
                            # Убираем повторяющийся промпт если есть
                            if 'Ассистент:' in text:
                                text = text.split('Ассистент:')[-1].strip()
                            return text
            
            elif isinstance(response_data, dict):
                if 'generated_text' in response_data:
                    return response_data['generated_text']
                elif 'text' in response_data:
                    return response_data['text']
            
            self.logger.warning(f"Неизвестный формат ответа: {response_data}")
            return None
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении текста: {e}")
            return None
    
    def _clean_response(self, text: str) -> str:
        """Очищает и форматирует ответ от модели"""
        if not text:
            return text
        
        # Убираем лишние пробелы
        text = ' '.join(text.split())
        
        # Обрезаем слишком длинные ответы
        if len(text) > 1000:
            text = text[:1000] + "..."
        
        # Убедимся, что ответ заканчивается нормально
        if text and text[-1] not in ['.', '!', '?', ':', ')', ']', '}']:
            text += '.'
        
        return text.strip()
    
    def test_connection(self) -> bool:
        """Проверяет соединение с Hugging Face API"""
        try:
            # Используем легкий запрос для проверки
            test_payload = {
                "inputs": "Тестовое сообщение",
                "parameters": {"max_length": 10, "min_length": 1}
            }
            
            response = self.session.post(
                self.api_url,
                json=test_payload,
                timeout=10
            )
            
            # 200 - OK, 503 - модель загружается (но API работает)
            return response.status_code in [200, 503, 422]  # 422 - ошибка валидации, но соединение есть
            
        except Exception as e:
            self.logger.error(f"Ошибка при тесте соединения: {e}")
            return False


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