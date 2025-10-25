"""
Rate Limiter для защиты от спама и чрезмерного использования
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from dataclasses import dataclass
from utils.logger import setup_logger

logger = setup_logger()


@dataclass
class RateLimit:
    """Настройки rate limit"""
    max_requests: int  # Максимальное количество запросов
    window_seconds: int  # Временное окно в секундах
    name: str  # Название лимита


class RateLimiter:
    """
    Класс для управления rate limiting
    
    Хранит историю запросов пользователей в памяти и проверяет лимиты
    """
    
    def __init__(self):
        # История запросов: {user_id: {limit_name: [timestamp1, timestamp2, ...]}}
        self.request_history: Dict[int, Dict[str, list[datetime]]] = {}
        
        # Настройки лимитов для разных типов запросов
        self.limits = {
            # Обычные вопросы - 10 запросов в минуту
            "question": RateLimit(
                max_requests=10,
                window_seconds=60,
                name="обычные вопросы"
            ),
            
            # Вопросы к ассистенту - 5 запросов в минуту (более ресурсоемкие)
            "assistant_question": RateLimit(
                max_requests=5,
                window_seconds=60,
                name="вопросы к нейроассистенту"
            ),
            
            # Расширенные ответы - 3 запроса в минуту
            "expand_answer": RateLimit(
                max_requests=3,
                window_seconds=60,
                name="расширенные ответы"
            ),
            
            # Глобальный лимит - 20 запросов за 5 минут
            "global": RateLimit(
                max_requests=20,
                window_seconds=300,
                name="все запросы"
            )
        }
        
        logger.info("Rate Limiter инициализирован")
    
    def check_rate_limit(
        self,
        user_id: int,
        limit_type: str = "question",
        check_global: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Проверить, не превышен ли rate limit
        
        Args:
            user_id: ID пользователя
            limit_type: Тип лимита (question, assistant_question, expand_answer)
            check_global: Проверять ли глобальный лимит
            
        Returns:
            tuple[bool, Optional[str]]: (разрешён ли запрос, сообщение об ошибке)
        """
        # Проверяем специфичный лимит
        allowed, message = self._check_specific_limit(user_id, limit_type)
        if not allowed:
            return False, message
        
        # Проверяем глобальный лимит
        if check_global:
            allowed, message = self._check_specific_limit(user_id, "global")
            if not allowed:
                return False, message
        
        return True, None
    
    def _check_specific_limit(
        self,
        user_id: int,
        limit_type: str
    ) -> tuple[bool, Optional[str]]:
        """
        Проверить конкретный лимит
        
        Args:
            user_id: ID пользователя
            limit_type: Тип лимита
            
        Returns:
            tuple[bool, Optional[str]]: (разрешён ли запрос, сообщение об ошибке)
        """
        if limit_type not in self.limits:
            logger.warning(f"Неизвестный тип лимита: {limit_type}")
            return True, None
        
        limit = self.limits[limit_type]
        now = datetime.now()
        
        # Инициализируем историю для пользователя
        if user_id not in self.request_history:
            self.request_history[user_id] = {}
        
        if limit_type not in self.request_history[user_id]:
            self.request_history[user_id][limit_type] = []
        
        # Получаем историю запросов
        history = self.request_history[user_id][limit_type]
        
        # Очищаем устаревшие записи
        cutoff_time = now - timedelta(seconds=limit.window_seconds)
        history[:] = [ts for ts in history if ts > cutoff_time]
        
        # Проверяем лимит
        if len(history) >= limit.max_requests:
            # Вычисляем время до следующего доступного запроса
            oldest_request = history[0]
            wait_until = oldest_request + timedelta(seconds=limit.window_seconds)
            wait_seconds = int((wait_until - now).total_seconds()) + 1
            
            message = (
                f"⏱ <b>Превышен лимит запросов!</b>\n\n"
                f"Тип: {limit.name}\n"
                f"Лимит: {limit.max_requests} запросов за {limit.window_seconds // 60} мин.\n"
                f"Попробуйте через: {wait_seconds} сек."
            )
            
            logger.warning(
                f"Rate limit exceeded: user_id={user_id}, "
                f"limit_type={limit_type}, wait={wait_seconds}s"
            )
            
            return False, message
        
        return True, None
    
    def record_request(
        self,
        user_id: int,
        limit_type: str = "question",
        record_global: bool = True
    ):
        """
        Записать запрос в историю
        
        Args:
            user_id: ID пользователя
            limit_type: Тип лимита
            record_global: Записывать ли в глобальную историю
        """
        now = datetime.now()
        
        # Инициализируем историю для пользователя
        if user_id not in self.request_history:
            self.request_history[user_id] = {}
        
        # Записываем в специфичную историю
        if limit_type not in self.request_history[user_id]:
            self.request_history[user_id][limit_type] = []
        
        self.request_history[user_id][limit_type].append(now)
        
        # Записываем в глобальную историю
        if record_global:
            if "global" not in self.request_history[user_id]:
                self.request_history[user_id]["global"] = []
            self.request_history[user_id]["global"].append(now)
        
        logger.debug(f"Request recorded: user_id={user_id}, limit_type={limit_type}")
    
    def get_remaining_requests(
        self,
        user_id: int,
        limit_type: str = "question"
    ) -> int:
        """
        Получить количество оставшихся запросов
        
        Args:
            user_id: ID пользователя
            limit_type: Тип лимита
            
        Returns:
            int: Количество оставшихся запросов
        """
        if limit_type not in self.limits:
            return 0
        
        limit = self.limits[limit_type]
        
        if user_id not in self.request_history:
            return limit.max_requests
        
        if limit_type not in self.request_history[user_id]:
            return limit.max_requests
        
        # Очищаем устаревшие записи
        now = datetime.now()
        cutoff_time = now - timedelta(seconds=limit.window_seconds)
        history = self.request_history[user_id][limit_type]
        history[:] = [ts for ts in history if ts > cutoff_time]
        
        remaining = limit.max_requests - len(history)
        return max(0, remaining)
    
    def clear_user_history(self, user_id: int):
        """
        Очистить историю пользователя (для администраторов)
        
        Args:
            user_id: ID пользователя
        """
        if user_id in self.request_history:
            del self.request_history[user_id]
            logger.info(f"Cleared rate limit history for user {user_id}")
    
    def cleanup_old_history(self, days: int = 1):
        """
        Очистить старую историю (для периодической очистки памяти)
        
        Args:
            days: Удалить историю старше N дней
        """
        now = datetime.now()
        cutoff_time = now - timedelta(days=days)
        
        users_to_remove = []
        
        for user_id, user_history in self.request_history.items():
            # Очищаем старые записи для каждого типа лимита
            for limit_type, history in user_history.items():
                history[:] = [ts for ts in history if ts > cutoff_time]
            
            # Если вся история пустая, помечаем пользователя для удаления
            if all(len(history) == 0 for history in user_history.values()):
                users_to_remove.append(user_id)
        
        # Удаляем пользователей с пустой историей
        for user_id in users_to_remove:
            del self.request_history[user_id]
        
        if users_to_remove:
            logger.info(f"Cleaned up rate limit history for {len(users_to_remove)} users")


# Глобальный экземпляр rate limiter
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Получить глобальный экземпляр rate limiter
    
    Returns:
        RateLimiter: Экземпляр rate limiter
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


