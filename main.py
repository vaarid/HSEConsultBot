"""
Главный файл запуска Telegram бота для консультаций по Охране Труда в ДОУ
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.memory import MemoryStorage

from utils.logger import setup_logger
from utils.config import load_config
from database.db import init_db
from bot.handlers import register_handlers
from bot.middlewares.auth import AuthMiddleware
from bot.middlewares.logging_middleware import LoggingMiddleware


async def main():
    """Основная функция запуска бота"""
    
    # Настройка логирования
    logger = setup_logger()
    logger.info("Запуск бота...")
    
    # Загрузка конфигурации
    config = load_config()
    
    # Проверка обязательных переменных окружения
    if not config.telegram.bot_token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    # Инициализация базы данных
    try:
        await init_db()
        logger.info("База данных подключена успешно")
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return
    
    # Создание бота и диспетчера
    bot = Bot(token=config.telegram.bot_token)
    
    # Выбор хранилища (Redis или Memory)
    try:
        storage = RedisStorage.from_url(config.redis.url)
        logger.info("Используется Redis storage")
    except Exception as e:
        logger.warning(f"Не удалось подключиться к Redis: {e}. Используется Memory storage")
        storage = MemoryStorage()
    
    dp = Dispatcher(storage=storage)
    
    # Регистрация middlewares
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(AuthMiddleware())  # Добавляем для callback_query
    
    # Регистрация handlers
    register_handlers(dp)
    
    # Запуск polling
    logger.info("Бот запущен и готов к работе!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")

