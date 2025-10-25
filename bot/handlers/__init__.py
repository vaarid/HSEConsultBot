"""
Регистрация всех обработчиков
"""
from aiogram import Dispatcher

from bot.handlers import start, help, ask, ask_assistant, admin, stats, gdpr, greetings


def register_handlers(dp: Dispatcher):
    """
    Регистрация всех обработчиков бота
    
    Args:
        dp: Диспетчер
    """
    # Регистрируем роутеры в порядке приоритета
    dp.include_router(start.router)  # /start должен быть первым
    dp.include_router(help.router)
    dp.include_router(admin.router)  # Админские команды
    dp.include_router(stats.router)
    dp.include_router(gdpr.router)
    dp.include_router(greetings.router)  # Приветствия (высокий приоритет)
    dp.include_router(ask_assistant.router)  # Нейроассистент
    dp.include_router(ask.router)  # /ask и обработка текста должны быть в конце
