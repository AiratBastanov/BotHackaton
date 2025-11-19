import time
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

class DialogContext:
    """Класс для управления контекстом диалога одного пользователя"""
    
    def __init__(self, user_id: int, max_length: int = 10, timeout: int = 3600):
        self.user_id = user_id
        self.max_length = max_length
        self.timeout = timeout
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.messages: List[Dict[str, str]] = []
        self.user_data: Dict[str, Any] = {}
        
    def add_message(self, role: str, content: str) -> None:
        """Добавляет сообщение в историю диалога"""
        self.updated_at = datetime.now()
        
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        
        self.messages.append(message)
        
        # Ограничиваем длину истории
        if len(self.messages) > self.max_length:
            self.messages = self.messages[-self.max_length:]
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """Возвращает историю диалога"""
        return self.messages.copy()
    
    def clear_history(self) -> None:
        """Очищает историю диалога"""
        self.messages.clear()
        self.updated_at = datetime.now()
    
    def is_expired(self) -> bool:
        """Проверяет, истекла ли сессия"""
        expiry_time = self.updated_at + timedelta(seconds=self.timeout)
        return datetime.now() > expiry_time
    
    def get_user_info(self) -> Dict[str, Any]:
        """Возвращает информацию о пользователе"""
        return {
            'user_id': self.user_id,
            'message_count': len(self.messages),
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'is_expired': self.is_expired()
        }


class ContextManager:
    """Менеджер для управления контекстами всех пользователей"""
    
    def __init__(self, max_context_length: int = 10, session_timeout: int = 3600):
        self.max_context_length = max_context_length
        self.session_timeout = session_timeout
        self.contexts: Dict[int, DialogContext] = {}
        self.logger = logging.getLogger(__name__)
    
    def get_context(self, user_id: int) -> DialogContext:
        """Получает или создает контекст для пользователя"""
        if user_id not in self.contexts or self.contexts[user_id].is_expired():
            self.contexts[user_id] = DialogContext(
                user_id=user_id,
                max_length=self.max_context_length,
                timeout=self.session_timeout
            )
            self.logger.info(f"Создан новый контекст для пользователя {user_id}")
        
        return self.contexts[user_id]
    
    def add_user_message(self, user_id: int, message: str) -> None:
        """Добавляет сообщение пользователя в контекст"""
        context = self.get_context(user_id)
        context.add_message('user', message)
    
    def add_bot_message(self, user_id: int, message: str) -> None:
        """Добавляет сообщение бота в контекст"""
        context = self.get_context(user_id)
        context.add_message('assistant', message)
    
    def get_conversation_history(self, user_id: int) -> List[Dict[str, str]]:
        """Получает историю диалога пользователя"""
        context = self.get_context(user_id)
        return context.get_conversation_history()
    
    def clear_user_context(self, user_id: int) -> bool:
        """Очищает контекст пользователя"""
        if user_id in self.contexts:
            self.contexts[user_id].clear_history()
            self.logger.info(f"Контекст пользователя {user_id} очищен")
            return True
        return False
    
    def cleanup_expired_contexts(self) -> int:
        """Очищает истекшие контексты и возвращает количество удаленных"""
        expired_users = [
            user_id for user_id, context in self.contexts.items() 
            if context.is_expired()
        ]
        
        for user_id in expired_users:
            del self.contexts[user_id]
        
        if expired_users:
            self.logger.info(f"Очищено {len(expired_users)} истекших контекстов")
        
        return len(expired_users)
    
    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику менеджера контекстов"""
        active_contexts = sum(1 for ctx in self.contexts.values() if not ctx.is_expired())
        
        return {
            'total_contexts': len(self.contexts),
            'active_contexts': active_contexts,
            'expired_contexts': len(self.contexts) - active_contexts,
            'max_context_length': self.max_context_length,
            'session_timeout': self.session_timeout
        }