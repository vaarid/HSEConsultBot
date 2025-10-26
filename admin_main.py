"""
Главный файл запуска админ-панели для Amvera
"""
import asyncio
import logging
import os
from utils.logger import setup_logger
from utils.config import load_config
from database.db import init_db
from admin.web_app import app

async def startup():
    """Инициализация при запуске"""
    logger = setup_logger()
    logger.info("Запуск админ-панели...")
    
    # Загрузка конфигурации
    config = load_config()
    
    # Проверка обязательных переменных окружения
    if not config.admin.secret_key or config.admin.secret_key == "change-me-in-production":
        logger.error("ADMIN_SECRET_KEY не установлен или использует значение по умолчанию!")
        return False
    
    # Инициализация базы данных
    try:
        await init_db()
        logger.info("База данных подключена успешно")
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return False
    
    logger.info("Админ-панель запущена и готова к работе!")
    return True

if __name__ == "__main__":
    # Настройка логирования
    logger = setup_logger()
    
    # Запуск инициализации
    try:
        success = asyncio.run(startup())
        if not success:
            logger.error("Не удалось инициализировать админ-панель")
            exit(1)
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {e}")
        exit(1)
    
    # Получение порта из переменной окружения (для Amvera)
    port = int(os.getenv("PORT", 8000))
    
    # Запуск сервера
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
