"""
Middleware для авторизации и проверки прав пользователей
"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from database.db import get_session
from database.crud import get_user, create_user
from database.models import UserRole
from utils.logger import setup_logger

logger = setup_logger()


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки и создания пользователей
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
        # Получаем пользователя из события
        user = None
        message = None
        
        if isinstance(event, Message):
            message = event
            user = message.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            message = event.message
        
        if not user:
            return await handler(event, data)
        
        # Работаем с БД
        async with get_session() as session:
            # Проверяем, существует ли пользователь
            db_user = await get_user(session, user.id)
            
            if not db_user:
                # Создаем нового пользователя
                logger.info(f"Создание нового пользователя: {user.id} (@{user.username})")
                db_user = await create_user(
                    session,
                    user_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name,
                    role=UserRole.TRIAL  # По умолчанию пробная роль
                )
            
            # Проверяем, не заблокирован ли пользователь
            if db_user.is_blocked:
                logger.warning(f"Заблокированный пользователь попытался отправить сообщение: {user.id}")
                if message:
                    await message.answer(
                        "❌ Ваш аккаунт заблокирован. Обратитесь к администратору."
                    )
                return
            
            # Проверяем согласие на обработку ПД (ФЗ-152)
            # Для CallbackQuery разрешаем обработку кнопок GDPR
            if isinstance(event, CallbackQuery):
                # Разрешаем callback для GDPR кнопок
                if event.data not in ["gdpr_accept", "gdpr_decline", "gdpr_read"]:
                    if not db_user.gdpr_accepted:
                        await event.answer(
                            "⚠️ Сначала примите согласие на обработку персональных данных",
                            show_alert=True
                        )
                        return
            elif isinstance(event, Message):
                # Для сообщений проверяем GDPR, кроме команды /start
                if not db_user.gdpr_accepted and message.text != "/start":
                    await message.answer(
                        "⚠️ Для продолжения работы необходимо принять согласие на обработку персональных данных.\n"
                        "Отправьте команду /start"
                    )
                    return
            
            # Добавляем пользователя в data для использования в handlers
            data["db_user"] = db_user
        
        # Продолжаем обработку
        return await handler(event, data)

