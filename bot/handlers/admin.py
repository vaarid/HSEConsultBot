"""
Обработчики команд администратора
"""
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.keyboards.main_menu import get_admin_keyboard, get_ai_provider_keyboard
from database.db import get_session
from database.crud import get_all_users, get_queries_stats, get_popular_categories, set_setting, get_setting
from database.models import User, UserRole
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()
router = Router()


def is_admin(user: User) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user.role == UserRole.ADMIN


@router.message(Command("admin"))
@router.message(F.text == "👤 Админ-панель")
async def cmd_admin(message: Message, db_user: User):
    """
    Обработчик команды /admin
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await message.answer("❌ У вас нет прав доступа к админ-панели.")
        return
    
    await message.answer(
        "👤 <b>Панель администратора</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, db_user: User):
    """
    Показать статистику
    
    Args:
        callback: Callback query
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    async with get_session() as session:
        # Общая статистика
        users = await get_all_users(session)
        stats = await get_queries_stats(session)
        categories = await get_popular_categories(session, limit=5)
    
    stats_text = "📊 <b>Статистика системы</b>\n\n"
    stats_text += f"👥 Всего пользователей: {len(users)}\n"
    stats_text += f"❓ Всего запросов: {stats['total_queries']}\n"
    stats_text += f"⏱ Среднее время ответа: {stats['avg_response_time']} сек\n\n"
    
    if categories:
        stats_text += "<b>Популярные категории:</b>\n"
        for category, count in categories:
            stats_text += f"  • {category}: {count}\n"
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery, db_user: User):
    """
    Показать список пользователей
    
    Args:
        callback: Callback query
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    async with get_session() as session:
        users = await get_all_users(session)
    
    users_text = "👥 <b>Пользователи системы</b>\n\n"
    
    # Группируем по ролям
    by_role = {}
    for user in users:
        role = user.role.value
        if role not in by_role:
            by_role[role] = []
        by_role[role].append(user)
    
    for role, role_users in by_role.items():
        users_text += f"<b>{role}:</b> {len(role_users)} чел.\n"
    
    users_text += f"\n<b>Всего:</b> {len(users)}"
    
    await callback.message.edit_text(
        users_text,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_ai")
async def admin_ai(callback: CallbackQuery, db_user: User):
    """
    Настройки AI провайдера
    
    Args:
        callback: Callback query
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    config = load_config()
    current_provider = config.app.ai_provider
    
    await callback.message.edit_text(
        f"🤖 <b>Настройки AI</b>\n\n"
        f"Текущий провайдер: <b>{current_provider}</b>\n\n"
        f"Выберите провайдера:",
        reply_markup=get_ai_provider_keyboard(current_provider),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ai_provider_"))
async def change_ai_provider(callback: CallbackQuery, db_user: User):
    """
    Изменить AI провайдера
    
    Args:
        callback: Callback query
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    provider = callback.data.split("_")[-1]  # openai или gigachat
    
    # Сохраняем в БД
    async with get_session() as session:
        await set_setting(
            session,
            key="ai_provider",
            value=provider,
            description="Текущий AI провайдер"
        )
    
    logger.info(f"AI провайдер изменен на {provider} пользователем {db_user.id}")
    
    await callback.answer(f"✅ AI провайдер изменен на {provider}", show_alert=True)
    
    # Обновляем клавиатуру
    await callback.message.edit_text(
        f"🤖 <b>Настройки AI</b>\n\n"
        f"Текущий провайдер: <b>{provider}</b>\n\n"
        f"✅ Провайдер успешно изменен!",
        reply_markup=get_ai_provider_keyboard(provider),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_kb")
async def admin_kb(callback: CallbackQuery, db_user: User):
    """
    Управление базой знаний
    
    Args:
        callback: Callback query
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📚 <b>База знаний</b>\n\n"
        "Функционал в разработке...\n"
        "Здесь будет управление документами базы знаний.",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, db_user: User):
    """
    Вернуться в главное меню админки
    
    Args:
        callback: Callback query
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👤 <b>Панель администратора</b>\n\n"
        "Выберите раздел:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(Command("rate_limits"))
async def cmd_rate_limits(message: Message, db_user: User):
    """
    Показать информацию о rate limits (только для администраторов)
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    from utils.rate_limiter import get_rate_limiter
    
    rate_limiter = get_rate_limiter()
    
    # Формируем информацию о лимитах
    limits_info = "⏱ <b>Настройки Rate Limits:</b>\n\n"
    
    for limit_type, limit in rate_limiter.limits.items():
        limits_info += f"<b>{limit.name}</b>\n"
        limits_info += f"├ Тип: <code>{limit_type}</code>\n"
        limits_info += f"├ Лимит: {limit.max_requests} запросов\n"
        limits_info += f"└ Окно: {limit.window_seconds // 60} мин ({limit.window_seconds} сек)\n\n"
    
    # Статистика использования
    total_users = len(rate_limiter.request_history)
    limits_info += f"📊 <b>Статистика:</b>\n"
    limits_info += f"└ Активных пользователей: {total_users}\n\n"
    
    limits_info += "💡 <b>Команды:</b>\n"
    limits_info += "• <code>/clear_rate_limit USER_ID</code> - очистить лимиты пользователя\n"
    limits_info += "• <code>/user_rate_limit USER_ID</code> - статистика пользователя"
    
    await message.answer(limits_info, parse_mode="HTML")


@router.message(Command("clear_rate_limit"))
async def cmd_clear_rate_limit(message: Message, db_user: User):
    """
    Очистить rate limits для пользователя (только для администраторов)
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    # Получаем USER_ID из команды
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите USER_ID:\n"
            "<code>/clear_rate_limit USER_ID</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат USER_ID. Должно быть число.")
        return
    
    from utils.rate_limiter import get_rate_limiter
    
    rate_limiter = get_rate_limiter()
    rate_limiter.clear_user_history(target_user_id)
    
    await message.answer(
        f"✅ Rate limits очищены для пользователя <code>{target_user_id}</code>",
        parse_mode="HTML"
    )


@router.message(Command("user_rate_limit"))
async def cmd_user_rate_limit(message: Message, db_user: User):
    """
    Показать статистику rate limits для пользователя (только для администраторов)
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    if not is_admin(db_user):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    # Получаем USER_ID из команды
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer(
            "❌ Укажите USER_ID:\n"
            "<code>/user_rate_limit USER_ID</code>",
            parse_mode="HTML"
        )
        return
    
    try:
        target_user_id = int(parts[1])
    except ValueError:
        await message.answer("❌ Неверный формат USER_ID. Должно быть число.")
        return
    
    from utils.rate_limiter import get_rate_limiter
    
    rate_limiter = get_rate_limiter()
    
    if target_user_id not in rate_limiter.request_history:
        await message.answer(
            f"ℹ️ Пользователь <code>{target_user_id}</code> не имеет истории запросов.",
            parse_mode="HTML"
        )
        return
    
    # Формируем статистику
    stats_text = f"📊 <b>Rate Limit статистика пользователя {target_user_id}:</b>\n\n"
    
    user_history = rate_limiter.request_history[target_user_id]
    
    for limit_type, limit in rate_limiter.limits.items():
        if limit_type in user_history and user_history[limit_type]:
            used = len([ts for ts in user_history[limit_type] 
                       if (datetime.now() - ts).total_seconds() < limit.window_seconds])
            remaining = rate_limiter.get_remaining_requests(target_user_id, limit_type)
            
            stats_text += f"<b>{limit.name}</b>\n"
            stats_text += f"├ Использовано: {used}/{limit.max_requests}\n"
            stats_text += f"└ Осталось: {remaining}\n\n"
    
    await message.answer(stats_text, parse_mode="HTML")
