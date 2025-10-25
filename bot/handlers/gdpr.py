"""
Обработчики для работы с персональными данными (ФЗ-152)
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.main_menu import get_confirmation_keyboard
from bot.states.conversation import GDPRStates
from database.db import get_session
from database.crud import delete_user_data, create_audit_log, get_user
from database.models import User
from utils.logger import setup_logger

logger = setup_logger()
router = Router()


@router.message(Command("gdpr"))
async def cmd_gdpr(message: Message, db_user: User):
    """
    Обработчик команды /gdpr - управление персональными данными
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    # Получаем свежие данные из БД для безопасности
    async with get_session() as session:
        fresh_user = await get_user(session, message.from_user.id)
        if not fresh_user:
            await message.answer("❌ Ошибка: пользователь не найден в базе данных.")
            return
        
        gdpr_text = f"""
🔒 <b>Управление персональными данными (ФЗ-152)</b>

<b>Ваши данные:</b>
• Telegram ID: {fresh_user.id}
• Имя пользователя: @{fresh_user.username or 'не указан'}
• Имя: {fresh_user.first_name or 'не указано'}
• Роль: {fresh_user.role.value}
• Дата регистрации: {fresh_user.created_at.strftime('%d.%m.%Y %H:%M')}
• Согласие принято: {'✅ Да' if fresh_user.gdpr_accepted else '❌ Нет'}

<b>Какие данные мы храним:</b>
• Информация о профиле (ID, имя, username)
• История ваших вопросов и ответов
• Статистика использования бота
• Логи действий (для безопасности)

<b>Как мы используем данные:</b>
• Для предоставления консультационных услуг
• Для улучшения качества ответов
• Для ведения статистики

<b>Ваши права:</b>
✅ Просмотр собранных данных
✅ Удаление всех данных (команда ниже)

⚠️ <b>Удаление данных</b>
Вы можете удалить все свои данные из системы.
После удаления вы не сможете использовать бота без повторной регистрации.

Для удаления данных отправьте: /delete_my_data
        """
        
        # Добавляем кнопку для повторного чтения соглашения
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        gdpr_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📄 Читать соглашение", callback_data="gdpr_read")]
        ])
        
        await message.answer(gdpr_text, parse_mode="HTML", reply_markup=gdpr_keyboard)


@router.message(Command("delete_my_data"))
async def cmd_delete_my_data(message: Message, state: FSMContext, db_user: User):
    """
    Запрос на удаление персональных данных
    
    Args:
        message: Сообщение
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await message.answer(
        "⚠️ <b>Подтверждение удаления данных</b>\n\n"
        "Вы уверены, что хотите удалить все свои данные?\n\n"
        "Будут удалены:\n"
        "• Ваш профиль\n"
        "• История вопросов и ответов\n"
        "• Вся статистика\n\n"
        "Это действие <b>необратимо</b>!",
        reply_markup=get_confirmation_keyboard("delete_data"),
        parse_mode="HTML"
    )
    await state.set_state(GDPRStates.waiting_for_delete_confirmation)


@router.callback_query(F.data == "confirm_delete_data")
async def confirm_delete_data(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Подтверждение удаления данных
    
    Args:
        callback: Callback query
        state: FSM состояние
        db_user: Пользователь из БД (может быть detached!)
    """
    # КРИТИЧЕСКИ ВАЖНО: Используем callback.from_user.id как источник истины!
    # db_user может быть detached от сессии и содержать устаревшие данные
    callback_user_id = callback.from_user.id
    callback_username = callback.from_user.username
    
    logger.warning(
        f"Запрос на удаление данных от пользователя {callback_user_id} "
        f"(@{callback_username}) через callback"
    )
    
    # Дополнительная проверка: сверяем с db_user (если он корректный)
    if hasattr(db_user, 'id') and db_user.id != callback_user_id:
        logger.error(
            f"SECURITY ALERT: Несоответствие user_id! "
            f"db_user.id={db_user.id}, callback.from_user.id={callback_user_id}"
        )
        await callback.answer("❌ Ошибка безопасности. Обратитесь к администратору.", show_alert=True)
        return
    
    # Используем ТОЛЬКО callback_user_id для удаления
    logger.warning(f"Начинается удаление данных пользователя {callback_user_id} (@{callback_username})")
    
    # Логируем удаление
    async with get_session() as session:
        await create_audit_log(
            session,
            user_id=callback_user_id,
            action="data_deletion_requested",
            details={
                "username": callback_username,
                "callback_user_id": callback_user_id,
                "db_user_id": db_user.id if hasattr(db_user, 'id') else None,
                "confirmed": True
            }
        )
        
        # Удаляем все данные пользователя - используем ТОЛЬКО callback_user_id
        await delete_user_data(session, callback_user_id)
    
    logger.warning(f"Пользователь {callback_user_id} (@{callback_username}) удалил все свои данные")
    
    await callback.message.edit_text(
        "✅ <b>Данные успешно удалены</b>\n\n"
        "Все ваши персональные данные были удалены из системы.\n\n"
        "Спасибо, что пользовались нашим ботом!\n"
        "Если захотите вернуться, отправьте /start",
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_delete_data")
async def cancel_delete_data(callback: CallbackQuery, state: FSMContext):
    """
    Отмена удаления данных
    
    Args:
        callback: Callback query
        state: FSM состояние
    """
    await callback.message.edit_text(
        "❌ Удаление данных отменено.\n\n"
        "Ваши данные сохранены."
    )
    
    await state.clear()
    await callback.answer()

