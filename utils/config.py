"""
Модуль для загрузки и управления конфигурацией приложения
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv


@dataclass
class TelegramConfig:
    """Конфигурация Telegram бота"""
    bot_token: str


@dataclass
class OpenAIConfig:
    """Конфигурация OpenAI"""
    api_key: str
    model: str = "gpt-4o-mini"
    max_tokens: int = 2000
    temperature: float = 0.7


@dataclass
class GigaChatConfig:
    """Конфигурация GigaChat"""
    api_key: str
    scope: str = "GIGACHAT_API_PERS"
    model: str = "GigaChat"


@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    host: str
    port: int
    database: str
    user: str
    password: str
    
    @property
    def url(self) -> str:
        """Формирование URL для подключения к БД"""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


@dataclass
class RedisConfig:
    """Конфигурация Redis"""
    host: str
    port: int
    db: int = 0
    password: Optional[str] = None
    
    @property
    def url(self) -> str:
        """Формирование URL для подключения к Redis"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"


@dataclass
class AdminConfig:
    """Конфигурация админ-панели"""
    secret_key: str
    user_ids: list[int]
    port: int = 8000


@dataclass
class SecurityConfig:
    """Конфигурация безопасности (ФЗ-152)"""
    encryption_key: str


@dataclass
class AppConfig:
    """Общая конфигурация приложения"""
    debug: bool = False
    log_level: str = "INFO"
    ai_provider: str = "openai"
    ai_timeout: int = 60
    max_history_length: int = 10
    enable_statistics: bool = True


@dataclass
class Config:
    """Главный класс конфигурации"""
    telegram: TelegramConfig
    openai: OpenAIConfig
    gigachat: GigaChatConfig
    database: DatabaseConfig
    redis: RedisConfig
    admin: AdminConfig
    security: SecurityConfig
    app: AppConfig


def load_config(env_file: str = ".env") -> Config:
    """
    Загрузка конфигурации из .env файла
    
    Args:
        env_file: Путь к .env файлу
        
    Returns:
        Config: Объект конфигурации
    """
    # Загрузка переменных окружения
    load_dotenv(env_file)
    
    # Telegram
    telegram = TelegramConfig(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "")
    )
    
    # OpenAI
    openai = OpenAIConfig(
        api_key=os.getenv("OPENAI_API_KEY", ""),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "2000")),
        temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    )
    
    # GigaChat
    gigachat = GigaChatConfig(
        api_key=os.getenv("GIGACHAT_API_KEY", ""),
        scope=os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS"),
        model=os.getenv("GIGACHAT_MODEL", "GigaChat")
    )
    
    # Database
    database = DatabaseConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "ot_bot_db"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres")
    )
    
    # Redis
    redis = RedisConfig(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD")
    )
    
    # Admin
    admin_ids_str = os.getenv("ADMIN_USER_IDS", "")
    admin_ids = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
    
    admin = AdminConfig(
        secret_key=os.getenv("ADMIN_SECRET_KEY", "change-me-in-production"),
        user_ids=admin_ids,
        port=int(os.getenv("ADMIN_PORT", "8000"))
    )
    
    # Security
    security = SecurityConfig(
        encryption_key=os.getenv("ENCRYPTION_KEY", "change-me-32-chars-min-length!")
    )
    
    # App
    app = AppConfig(
        debug=os.getenv("DEBUG", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        ai_provider=os.getenv("AI_PROVIDER", "openai"),
        ai_timeout=int(os.getenv("AI_TIMEOUT", "60")),
        max_history_length=int(os.getenv("MAX_HISTORY_LENGTH", "10")),
        enable_statistics=os.getenv("ENABLE_STATISTICS", "true").lower() == "true"
    )
    
    return Config(
        telegram=telegram,
        openai=openai,
        gigachat=gigachat,
        database=database,
        redis=redis,
        admin=admin,
        security=security,
        app=app
    )

