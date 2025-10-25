"""
Модуль для работы с базой данных
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from contextlib import asynccontextmanager

from database.models import Base
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()

# Глобальные переменные для engine и session maker
engine = None
async_session_maker = None

"""
async def init_db():
    """
    Инициализация базы данных и создание таблиц
    """
    global engine, async_session_maker
    
    config = load_config()
    
    # Создание engine
    engine = create_async_engine(
        config.database.url,
        echo=config.app.debug,
        poolclass=NullPool if config.app.debug else None,
        pool_size=10,
        max_overflow=20
    )
    
    # Создание session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Создание всех таблиц
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("База данных инициализирована")
"""
async def init_db():
    """
    Инициализация базы данных и создание таблиц
    """
    global engine, async_session_maker
    
    config = load_config()
    db_url = config.database.url

    # --- Автоисправление схемы подключения под asyncpg ---
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(
        db_url,
        echo=config.app.debug,
        poolclass=NullPool if config.app.debug else None,
        pool_size=10,
        max_overflow=20
    )
    
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("База данных инициализирована")

async def close_db():
    """
    Закрытие соединения с базой данных
    """
    global engine
    
    if engine:
        await engine.dispose()
        logger.info("Соединение с базой данных закрыто")


@asynccontextmanager
async def get_session() -> AsyncSession:
    """
    Контекстный менеджер для получения сессии БД
    
    Yields:
        AsyncSession: Сессия базы данных
    """
    if async_session_maker is None:
        await init_db()
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

