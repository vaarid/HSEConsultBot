"""
Обработчик статистики пользователя
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from database.db import get_session
from database.crud import get_user_queries, get_popular_categories
from database.models import User
from utils.logger import setup_logger

logger = setup_logger()
router = Router()


@router.message(Command("stats"))
@router.message(F.text == "📊 Моя статистика")
async def cmd_stats(message: Message, db_user: User):
    """
    Обработчик команды /stats - показать статистику пользователя
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    async with get_session() as session:
        # Получаем запросы пользователя
        queries = await get_user_queries(session, db_user.id, limit=100)
    
    if not queries:
        await message.answer(
            "📊 У вас пока нет статистики.\n\n"
            "Задайте первый вопрос, чтобы начать собирать статистику!"
        )
        return
    
    # Анализируем запросы
    total_queries = len(queries)
    avg_response_time = sum(q.response_time or 0 for q in queries) / total_queries if queries else 0
    
    # Категории
    categories = {}
    for q in queries:
        if q.category:
            categories[q.category] = categories.get(q.category, 0) + 1
    
    # Последние вопросы
    recent_queries = queries[:5]
    
    stats_text = f"📊 <b>Ваша статистика</b>\n\n"
    stats_text += f"👤 Пользователь: {db_user.first_name or 'Без имени'}\n"
    stats_text += f"🆔 ID: {db_user.id}\n"
    stats_text += f"📝 Роль: {db_user.role.value}\n\n"
    stats_text += f"❓ Всего запросов: {total_queries}\n"
    stats_text += f"⏱ Среднее время ответа: {avg_response_time:.2f} сек\n"
    stats_text += f"📅 Зарегистрирован: {db_user.created_at.strftime('%d.%m.%Y')}\n\n"
    
    if categories:
        stats_text += "<b>Популярные категории:</b>\n"
        sorted_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories[:5]:
            stats_text += f"  • {category}: {count}\n"
        stats_text += "\n"
    
    if recent_queries:
        stats_text += "<b>Последние вопросы:</b>\n"
        for i, q in enumerate(recent_queries, 1):
            question_short = q.question[:50] + "..." if len(q.question) > 50 else q.question
            stats_text += f"{i}. {question_short}\n"
    
    await message.answer(stats_text, parse_mode="HTML")

