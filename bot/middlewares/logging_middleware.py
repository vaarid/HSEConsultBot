"""
Middleware для логирования сообщений
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from utils.logger import setup_logger

logger = setup_logger()


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования входящих сообщений
    """
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """
        Обработка входящего события
        
        Args:
            handler: Следующий обработчик
            event: Событие
            data: Данные для передачи обработчику
            
        Returns:
            Результат обработки
        """
        # Логируем только сообщения
        if isinstance(event, Message):
            message: Message = event
            user = message.from_user
            
            logger.info(
                f"Сообщение от пользователя {user.id} (@{user.username}): "
                f"{message.text[:50] if message.text else '[не текст]'}..."
            )
        
        # Продолжаем обработку
        return await handler(event, data)

