"""
Модуль настройки логирования
"""
import os
import sys
import logging
from pathlib import Path
from loguru import logger


class InterceptHandler(logging.Handler):
    """
    Перехватчик для стандартного logging в loguru
    """
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logger(
    log_level: str = None,
    log_file: str = None
) -> logger:
    """
    Настройка логирования приложения
    
    Args:
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
        log_file: Путь к файлу логов
        
    Returns:
        logger: Настроенный логгер
    """
    # Получение параметров из переменных окружения
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO")
    log_file = log_file or os.getenv("LOG_FILE", "logs/bot.log")
    
    # Создание директории для логов
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Удаление стандартного обработчика
    logger.remove()
    
    # Формат логов
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Добавление вывода в консоль
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Добавление записи в файл
    logger.add(
        log_file,
        format=log_format,
        level=log_level,
        rotation="10 MB",  # Ротация при достижении 10 MB
        retention="30 days",  # Хранение логов 30 дней
        compression="zip",  # Сжатие старых логов
        encoding="utf-8"
    )
    
    # Перехват стандартного logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Настройка логирования для библиотек
    for logger_name in ["aiogram", "sqlalchemy", "redis", "httpx"]:
        logging.getLogger(logger_name).handlers = [InterceptHandler()]
    
    logger.info(f"Логирование настроено: уровень={log_level}, файл={log_file}")
    
    return logger

