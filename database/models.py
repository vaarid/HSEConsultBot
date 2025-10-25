"""
Модели базы данных SQLAlchemy
"""
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import BigInteger, String, Text, Boolean, DateTime, Integer, ForeignKey, Enum, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class UserRole(PyEnum):
    """Роли пользователей"""
    ADMIN = "admin"
    SPECIALIST_OT_DOU = "specialist_ot_dou"
    SPECIALIST_OT_OTHER = "specialist_ot_other"
    EMPLOYEE = "employee"
    TRIAL = "trial"


class AIProvider(PyEnum):
    """AI провайдеры"""
    OPENAI = "openai"
    GIGACHAT = "gigachat"


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # Telegram User ID
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.TRIAL)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # OpenAI Assistant thread ID для каждого пользователя
    assistant_thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # ФЗ-152: Согласие на обработку персональных данных
    gdpr_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    gdpr_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Статистика
    total_requests: Mapped[int] = mapped_column(Integer, default=0)
    last_request_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="user", cascade="all, delete-orphan")
    queries: Mapped[list["Query"]] = relationship("Query", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class Message(Base):
    """Модель сообщения (история переписки)"""
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    
    role: Mapped[str] = mapped_column(String(50))  # user, assistant, system
    content: Mapped[str] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, user_id={self.user_id}, role={self.role})>"


class Query(Base):
    """Модель запроса пользователя (для статистики)"""
    __tablename__ = "queries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    
    # AI Provider и модель
    ai_provider: Mapped[AIProvider] = mapped_column(Enum(AIProvider))
    ai_model: Mapped[str] = mapped_column(String(100))
    
    # Метрики
    response_time: Mapped[float | None] = mapped_column(nullable=True)  # Время ответа в секундах
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # Категория вопроса (опционально, можно классифицировать AI)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # Использованные документы из базы знаний
    documents_used: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="queries")
    
    def __repr__(self):
        return f"<Query(id={self.id}, user_id={self.user_id}, category={self.category})>"


class SystemSettings(Base):
    """Модель системных настроек"""
    __tablename__ = "system_settings"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<SystemSettings(key={self.key}, value={self.value})>"


class Document(Base):
    """Модель документа из базы знаний"""
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Тип документа (закон, инструкция, шаблон и т.д.)
    doc_type: Mapped[str] = mapped_column(String(100))
    
    # Ссылка на документ или путь к файлу
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # OpenAI File ID (если файл загружен в OpenAI)
    openai_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    
    # Содержимое (для поиска)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Теги для категоризации
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    
    # Актуальность документа
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title}, doc_type={self.doc_type})>"


class AuditLog(Base):
    """Модель логов для ФЗ-152 (аудит операций с персональными данными)"""
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    
    action: Mapped[str] = mapped_column(String(100))  # login, query, data_access, data_delete и т.д.
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"
