"""
CRUD операции для работы с базой данных
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User, Message, Query, Document, SystemSettings, AuditLog, UserRole, AIProvider


# ==================== USER OPERATIONS ====================

async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    """Получить пользователя по ID"""
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def create_user(
    session: AsyncSession,
    user_id: int,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    role: UserRole = UserRole.TRIAL
) -> User:
    """Создать нового пользователя"""
    user = User(
        id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=role
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_user_role(session: AsyncSession, user_id: int, role: UserRole) -> Optional[User]:
    """Обновить роль пользователя"""
    await session.execute(
        update(User).where(User.id == user_id).values(role=role)
    )
    await session.commit()
    return await get_user(session, user_id)


async def accept_gdpr(session: AsyncSession, user_id: int) -> Optional[User]:
    """Принять согласие на обработку ПД"""
    await session.execute(
        update(User).where(User.id == user_id).values(
            gdpr_accepted=True,
            gdpr_accepted_at=datetime.now()
        )
    )
    await session.commit()
    return await get_user(session, user_id)


async def increment_user_requests(session: AsyncSession, user_id: int):
    """Увеличить счетчик запросов пользователя"""
    await session.execute(
        update(User).where(User.id == user_id).values(
            total_requests=User.total_requests + 1,
            last_request_at=datetime.now()
        )
    )
    await session.commit()


async def set_user_thread_id(session: AsyncSession, user_id: int, thread_id: str) -> Optional[User]:
    """Установить thread ID для пользователя"""
    await session.execute(
        update(User).where(User.id == user_id).values(assistant_thread_id=thread_id)
    )
    await session.commit()
    return await get_user(session, user_id)


async def block_user(session: AsyncSession, user_id: int, blocked: bool = True):
    """Заблокировать/разблокировать пользователя"""
    await session.execute(
        update(User).where(User.id == user_id).values(is_blocked=blocked)
    )
    await session.commit()


async def delete_user_data(session: AsyncSession, user_id: int):
    """Удалить все данные пользователя (GDPR)"""
    from utils.logger import setup_logger
    logger = setup_logger()
    
    # Проверяем, что пользователь существует
    user = await get_user(session, user_id)
    if not user:
        logger.warning(f"Попытка удалить несуществующего пользователя: {user_id}")
        return
    
    logger.info(f"Удаление данных пользователя: {user_id} (@{user.username})")
    
    # Удаляем пользователя (messages и queries удалятся автоматически через CASCADE)
    result = await session.execute(delete(User).where(User.id == user_id))
    await session.commit()
    
    logger.info(f"Удалено строк: {result.rowcount}, user_id: {user_id}")


async def get_all_users(session: AsyncSession, role: Optional[UserRole] = None) -> List[User]:
    """Получить всех пользователей (с опциональной фильтрацией по роли)"""
    query = select(User)
    if role:
        query = query.where(User.role == role)
    result = await session.execute(query.order_by(User.created_at.desc()))
    return list(result.scalars().all())


# ==================== MESSAGE OPERATIONS ====================

async def create_message(
    session: AsyncSession,
    user_id: int,
    role: str,
    content: str
) -> Message:
    """Создать новое сообщение в истории"""
    message = Message(user_id=user_id, role=role, content=content)
    session.add(message)
    await session.commit()
    await session.refresh(message)
    return message


async def get_user_messages(
    session: AsyncSession,
    user_id: int,
    limit: int = 10
) -> List[Message]:
    """Получить последние сообщения пользователя"""
    result = await session.execute(
        select(Message)
        .where(Message.user_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = list(result.scalars().all())
    return list(reversed(messages))  # Возвращаем в хронологическом порядке


async def clear_user_messages(session: AsyncSession, user_id: int):
    """Очистить историю сообщений пользователя"""
    await session.execute(delete(Message).where(Message.user_id == user_id))
    await session.commit()


# ==================== QUERY OPERATIONS ====================

async def create_query(
    session: AsyncSession,
    user_id: int,
    question: str,
    answer: str,
    ai_provider: AIProvider,
    ai_model: str,
    response_time: Optional[float] = None,
    tokens_used: Optional[int] = None,
    category: Optional[str] = None,
    documents_used: Optional[dict] = None
) -> Query:
    """Создать запись о запросе"""
    query = Query(
        user_id=user_id,
        question=question,
        answer=answer,
        ai_provider=ai_provider,
        ai_model=ai_model,
        response_time=response_time,
        tokens_used=tokens_used,
        category=category,
        documents_used=documents_used
    )
    session.add(query)
    await session.commit()
    await session.refresh(query)
    return query


async def get_user_queries(
    session: AsyncSession,
    user_id: int,
    limit: int = 20
) -> List[Query]:
    """Получить запросы пользователя"""
    result = await session.execute(
        select(Query)
        .where(Query.user_id == user_id)
        .order_by(Query.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_popular_categories(session: AsyncSession, limit: int = 10) -> List[tuple]:
    """Получить популярные категории вопросов"""
    result = await session.execute(
        select(Query.category, func.count(Query.id).label('count'))
        .where(Query.category.isnot(None))
        .group_by(Query.category)
        .order_by(desc('count'))
        .limit(limit)
    )
    return list(result.all())


async def get_queries_stats(session: AsyncSession) -> dict:
    """Получить статистику по запросам"""
    total_result = await session.execute(select(func.count(Query.id)))
    total_queries = total_result.scalar()
    
    avg_time_result = await session.execute(select(func.avg(Query.response_time)))
    avg_response_time = avg_time_result.scalar() or 0
    
    return {
        "total_queries": total_queries,
        "avg_response_time": round(avg_response_time, 2)
    }


# ==================== DOCUMENT OPERATIONS ====================

async def create_document(
    session: AsyncSession,
    title: str,
    doc_type: str,
    description: Optional[str] = None,
    url: Optional[str] = None,
    file_path: Optional[str] = None,
    content: Optional[str] = None,
    tags: Optional[list] = None
) -> Document:
    """Создать документ в базе знаний"""
    document = Document(
        title=title,
        description=description,
        doc_type=doc_type,
        url=url,
        file_path=file_path,
        content=content,
        tags=tags
    )
    session.add(document)
    await session.commit()
    await session.refresh(document)
    return document


async def get_document(session: AsyncSession, doc_id: int) -> Optional[Document]:
    """Получить документ по ID"""
    result = await session.execute(
        select(Document).where(Document.id == doc_id)
    )
    return result.scalar_one_or_none()


async def search_documents(
    session: AsyncSession,
    query: str,
    doc_type: Optional[str] = None,
    limit: int = 10
) -> List[Document]:
    """Поиск документов по тексту"""
    stmt = select(Document).where(
        Document.is_active == True,
        Document.content.ilike(f"%{query}%")
    )
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    
    result = await session.execute(stmt.limit(limit))
    return list(result.scalars().all())


async def get_all_documents(
    session: AsyncSession,
    doc_type: Optional[str] = None,
    active_only: bool = True
) -> List[Document]:
    """Получить все документы"""
    query = select(Document)
    if active_only:
        query = query.where(Document.is_active == True)
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    
    result = await session.execute(query.order_by(Document.created_at.desc()))
    return list(result.scalars().all())


async def update_document(
    session: AsyncSession,
    doc_id: int,
    **kwargs
) -> Optional[Document]:
    """Обновить документ"""
    await session.execute(
        update(Document).where(Document.id == doc_id).values(**kwargs)
    )
    await session.commit()
    return await get_document(session, doc_id)


async def delete_document(session: AsyncSession, doc_id: int):
    """Удалить документ"""
    await session.execute(delete(Document).where(Document.id == doc_id))
    await session.commit()


# ==================== SYSTEM SETTINGS OPERATIONS ====================

async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
    """Получить значение настройки"""
    result = await session.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(
    session: AsyncSession,
    key: str,
    value: str,
    description: Optional[str] = None
):
    """Установить значение настройки"""
    # Проверяем, существует ли настройка
    existing = await session.execute(
        select(SystemSettings).where(SystemSettings.key == key)
    )
    setting = existing.scalar_one_or_none()
    
    if setting:
        # Обновляем существующую
        await session.execute(
            update(SystemSettings)
            .where(SystemSettings.key == key)
            .values(value=value, description=description)
        )
    else:
        # Создаем новую
        new_setting = SystemSettings(key=key, value=value, description=description)
        session.add(new_setting)
    
    await session.commit()


async def get_all_settings(session: AsyncSession) -> List[SystemSettings]:
    """Получить все настройки"""
    result = await session.execute(select(SystemSettings))
    return list(result.scalars().all())


# ==================== AUDIT LOG OPERATIONS ====================

async def create_audit_log(
    session: AsyncSession,
    user_id: Optional[int],
    action: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> AuditLog:
    """Создать запись в журнале аудита"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    session.add(log)
    await session.commit()
    await session.refresh(log)
    return log


async def get_user_audit_logs(
    session: AsyncSession,
    user_id: int,
    limit: int = 50
) -> List[AuditLog]:
    """Получить логи пользователя"""
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

