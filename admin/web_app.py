"""
Веб-интерфейс администратора (FastAPI)
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import HTMLResponse
from typing import List, Dict
import secrets

from database.db import get_session, init_db
from database.crud import (
    get_all_users, get_queries_stats, get_popular_categories,
    get_all_settings, set_setting, get_user_queries
)
from utils.analytics import anonymize_queries_list, create_analytics_report
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()

app = FastAPI(
    title="OT Bot Admin Panel",
    description="Панель администратора для бота по охране труда",
    version="1.0.0"
)

security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """
    Проверка учетных данных администратора
    
    Args:
        credentials: HTTP Basic credentials
        
    Raises:
        HTTPException: Если credentials неверные
    """
    config = load_config()
    correct_username = "admin"
    correct_password = config.admin.secret_key[:20]  # Используем часть secret key как пароль
    
    is_correct_username = secrets.compare_digest(credentials.username.encode("utf8"), correct_username.encode("utf8"))
    is_correct_password = secrets.compare_digest(credentials.password.encode("utf8"), correct_password.encode("utf8"))
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    await init_db()
    logger.info("Админ-панель запущена")


@app.get("/", response_class=HTMLResponse)
async def root(username: str = Depends(verify_admin)):
    """
    Главная страница админ-панели
    
    Args:
        username: Имя пользователя (из verify_admin)
        
    Returns:
        HTMLResponse: HTML страница
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Админ-панель OT Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            h1 { color: #333; }
            .card {
                background: white;
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .nav {
                background: #2c3e50;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            .nav a {
                color: white;
                text-decoration: none;
                margin: 0 15px;
                padding: 8px 15px;
                border-radius: 4px;
            }
            .nav a:hover {
                background: #34495e;
            }
        </style>
    </head>
    <body>
        <h1>🛡️ Админ-панель OT Bot</h1>
        
        <div class="nav">
            <a href="/stats">📊 Статистика</a>
            <a href="/analytics">📈 Аналитика</a>
            <a href="/users">👥 Пользователи</a>
            <a href="/settings">⚙️ Настройки</a>
            <a href="/docs">📖 API Docs</a>
        </div>
        
        <div class="card">
            <h2>Добро пожаловать, администратор!</h2>
            <p>Используйте навигацию выше для управления ботом.</p>
            <p><strong>API документация:</strong> <a href="/docs">/docs</a></p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/stats")
async def get_stats(username: str = Depends(verify_admin)) -> Dict:
    """
    Получить статистику системы
    
    Args:
        username: Имя пользователя
        
    Returns:
        Dict: Статистика
    """
    async with get_session() as session:
        users = await get_all_users(session)
        stats = await get_queries_stats(session)
        categories = await get_popular_categories(session, limit=10)
    
    return {
        "total_users": len(users),
        "total_queries": stats["total_queries"],
        "avg_response_time": stats["avg_response_time"],
        "popular_categories": [{"category": cat, "count": cnt} for cat, cnt in categories]
    }


@app.get("/stats", response_class=HTMLResponse)
async def stats_page(username: str = Depends(verify_admin)):
    """
    Страница статистики
    
    Args:
        username: Имя пользователя
        
    Returns:
        HTMLResponse: HTML страница
    """
    async with get_session() as session:
        users = await get_all_users(session)
        stats = await get_queries_stats(session)
        categories = await get_popular_categories(session, limit=10)
    
    categories_html = ""
    for cat, cnt in categories:
        categories_html += f"<tr><td>{cat}</td><td>{cnt}</td></tr>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Статистика - OT Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            .stat-box {{ display: inline-block; padding: 20px; margin: 10px; background: #e3f2fd; border-radius: 8px; }}
        </style>
    </head>
    <body>
        <h1>📊 Статистика системы</h1>
        <a href="/">← Назад</a>
        
        <div class="card">
            <h2>Общая статистика</h2>
            <div class="stat-box">
                <h3>👥 Пользователей</h3>
                <p style="font-size: 2em; margin: 0;">{len(users)}</p>
            </div>
            <div class="stat-box">
                <h3>❓ Запросов</h3>
                <p style="font-size: 2em; margin: 0;">{stats['total_queries']}</p>
            </div>
            <div class="stat-box">
                <h3>⏱ Среднее время</h3>
                <p style="font-size: 2em; margin: 0;">{stats['avg_response_time']} сек</p>
            </div>
        </div>
        
        <div class="card">
            <h2>Популярные категории</h2>
            <table>
                <thead>
                    <tr>
                        <th>Категория</th>
                        <th>Количество</th>
                    </tr>
                </thead>
                <tbody>
                    {categories_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/users")
async def get_users_api(username: str = Depends(verify_admin)) -> List[Dict]:
    """
    Получить список пользователей
    
    Args:
        username: Имя пользователя
        
    Returns:
        List[Dict]: Список пользователей
    """
    async with get_session() as session:
        users = await get_all_users(session)
    
    return [
        {
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "role": user.role.value,
            "is_active": user.is_active,
            "total_requests": user.total_requests,
            "created_at": user.created_at.isoformat()
        }
        for user in users
    ]


@app.get("/api/queries")
async def get_queries_api(
    username: str = Depends(verify_admin),
    limit: int = 50,
    user_id: int = None
) -> List[Dict]:
    """
    Получить список запросов
    
    Args:
        username: Имя пользователя
        limit: Лимит записей
        user_id: ID пользователя (опционально)
        
    Returns:
        List[Dict]: Список запросов
    """
    async with get_session() as session:
        if user_id:
            queries = await get_user_queries(session, user_id, limit)
        else:
            # Получаем все запросы (нужно добавить функцию в CRUD)
            from sqlalchemy import select, desc
            from database.models import Query
            result = await session.execute(
                select(Query)
                .order_by(desc(Query.created_at))
                .limit(limit)
            )
            queries = list(result.scalars().all())
    
    return [
        {
            "id": query.id,
            "user_id": query.user_id,
            "question": query.question[:100] + "..." if len(query.question) > 100 else query.question,
            "answer": query.answer[:200] + "..." if len(query.answer) > 200 else query.answer,
            "ai_provider": query.ai_provider.value,
            "ai_model": query.ai_model,
            "response_time": query.response_time,
            "tokens_used": query.tokens_used,
            "category": query.category,
            "created_at": query.created_at.isoformat()
        }
        for query in queries
    ]


@app.get("/api/analytics/detailed")
async def get_detailed_analytics(username: str = Depends(verify_admin)) -> Dict:
    """
    Получить детальную аналитику
    
    Args:
        username: Имя пользователя
        
    Returns:
        Dict: Детальная аналитика
    """
    from sqlalchemy import select, func, desc
    from database.models import Query, User, AIProvider
    from datetime import datetime, timedelta
    
    async with get_session() as session:
        # Общая статистика
        total_queries_result = await session.execute(select(func.count(Query.id)))
        total_queries = total_queries_result.scalar()
        
        # Статистика по AI провайдерам
        ai_stats_result = await session.execute(
            select(Query.ai_provider, func.count(Query.id).label('count'))
            .group_by(Query.ai_provider)
        )
        ai_stats = {provider.value: count for provider, count in ai_stats_result.all()}
        
        # Статистика по времени ответа
        avg_time_result = await session.execute(select(func.avg(Query.response_time)))
        avg_response_time = avg_time_result.scalar() or 0
        
        # Статистика по токенам
        total_tokens_result = await session.execute(select(func.sum(Query.tokens_used)))
        total_tokens = total_tokens_result.scalar() or 0
        
        # Запросы за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        week_queries_result = await session.execute(
            select(func.count(Query.id))
            .where(Query.created_at >= week_ago)
        )
        week_queries = week_queries_result.scalar()
        
        # Топ пользователей по количеству запросов
        top_users_result = await session.execute(
            select(User.id, User.username, User.total_requests)
            .order_by(desc(User.total_requests))
            .limit(10)
        )
        top_users = [
            {"id": user_id, "username": username, "requests": requests}
            for user_id, username, requests in top_users_result.all()
        ]
        
        # Статистика по категориям
        categories_result = await session.execute(
            select(Query.category, func.count(Query.id).label('count'))
            .where(Query.category.isnot(None))
            .group_by(Query.category)
            .order_by(desc('count'))
            .limit(10)
        )
        categories = [{"category": cat, "count": cnt} for cat, cnt in categories_result.all()]
        
        return {
            "total_queries": total_queries,
            "week_queries": week_queries,
            "avg_response_time": round(avg_response_time, 2),
            "total_tokens": total_tokens,
            "ai_providers": ai_stats,
            "top_users": top_users,
            "categories": categories
        }


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(username: str = Depends(verify_admin)):
    """
    Страница детальной аналитики
    
    Args:
        username: Имя пользователя
        
    Returns:
        HTMLResponse: HTML страница
    """
    async with get_session() as session:
        analytics = await get_detailed_analytics(username)
    
    # Формируем HTML для топ пользователей
    top_users_html = ""
    for user in analytics["top_users"][:5]:
        username_display = user["username"] or f"ID: {user['id']}"
        top_users_html += f"<tr><td>{username_display}</td><td>{user['requests']}</td></tr>"
    
    # Формируем HTML для категорий
    categories_html = ""
    for cat in analytics["categories"]:
        categories_html += f"<tr><td>{cat['category']}</td><td>{cat['count']}</td></tr>"
    
    # Формируем HTML для AI провайдеров
    ai_providers_html = ""
    for provider, count in analytics["ai_providers"].items():
        ai_providers_html += f"<tr><td>{provider}</td><td>{count}</td></tr>"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Детальная аналитика - OT Bot</title>
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 1400px; margin: 0 auto; padding: 20px; }}
            .card {{ background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #f8f9fa; }}
            .stat-box {{ display: inline-block; padding: 20px; margin: 10px; background: #e3f2fd; border-radius: 8px; min-width: 150px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        </style>
    </head>
    <body>
        <h1>📈 Детальная аналитика</h1>
        <a href="/">← Назад</a>
        
        <div class="card">
            <h2>Общие показатели</h2>
            <div class="stat-box">
                <h3>📊 Всего запросов</h3>
                <p style="font-size: 2em; margin: 0;">{analytics['total_queries']}</p>
            </div>
            <div class="stat-box">
                <h3>📅 За неделю</h3>
                <p style="font-size: 2em; margin: 0;">{analytics['week_queries']}</p>
            </div>
            <div class="stat-box">
                <h3>⏱ Среднее время</h3>
                <p style="font-size: 2em; margin: 0;">{analytics['avg_response_time']} сек</p>
            </div>
            <div class="stat-box">
                <h3>🔤 Токенов</h3>
                <p style="font-size: 2em; margin: 0;">{analytics['total_tokens']:,}</p>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h3>Топ пользователей</h3>
                <table>
                    <thead>
                        <tr><th>Пользователь</th><th>Запросов</th></tr>
                    </thead>
                    <tbody>
                        {top_users_html}
                    </tbody>
                </table>
            </div>
            
            <div class="card">
                <h3>AI провайдеры</h3>
                <table>
                    <thead>
                        <tr><th>Провайдер</th><th>Запросов</th></tr>
                    </thead>
                    <tbody>
                        {ai_providers_html}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="card">
            <h3>Популярные категории</h3>
            <table>
                <thead>
                    <tr><th>Категория</th><th>Количество</th></tr>
                </thead>
                <tbody>
                    {categories_html}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/api/analytics/anonymized")
async def get_anonymized_analytics(username: str = Depends(verify_admin)) -> Dict:
    """
    Получить анонимизированную аналитику
    
    Args:
        username: Имя пользователя
        
    Returns:
        Dict: Анонимизированная аналитика
    """
    from sqlalchemy import select, desc
    from database.models import Query
    
    async with get_session() as session:
        # Получаем все запросы
        result = await session.execute(
            select(Query)
            .order_by(desc(Query.created_at))
            .limit(1000)  # Ограничиваем для производительности
        )
        queries = list(result.scalars().all())
    
    # Конвертируем в словари
    queries_data = [
        {
            "id": query.id,
            "user_id": query.user_id,
            "question": query.question,
            "answer": query.answer,
            "ai_provider": query.ai_provider.value,
            "ai_model": query.ai_model,
            "response_time": query.response_time,
            "tokens_used": query.tokens_used,
            "category": query.category,
            "created_at": query.created_at.isoformat()
        }
        for query in queries
    ]
    
    # Создаем анонимизированный отчет
    report = create_analytics_report(queries_data, anonymize=True)
    
    return report


@app.get("/api/export/queries")
async def export_queries(
    username: str = Depends(verify_admin),
    format: str = "json",
    anonymize: bool = True
) -> Dict:
    """
    Экспорт запросов
    
    Args:
        username: Имя пользователя
        format: Формат экспорта (json, csv)
        anonymize: Анонимизировать данные
        
    Returns:
        Dict: Экспортированные данные
    """
    from sqlalchemy import select, desc
    from database.models import Query
    import csv
    import io
    
    async with get_session() as session:
        result = await session.execute(
            select(Query)
            .order_by(desc(Query.created_at))
            .limit(5000)  # Ограничение для экспорта
        )
        queries = list(result.scalars().all())
    
    # Конвертируем в словари
    queries_data = [
        {
            "id": query.id,
            "user_id": query.user_id,
            "question": query.question,
            "answer": query.answer,
            "ai_provider": query.ai_provider.value,
            "ai_model": query.ai_model,
            "response_time": query.response_time,
            "tokens_used": query.tokens_used,
            "category": query.category,
            "created_at": query.created_at.isoformat()
        }
        for query in queries
    ]
    
    if anonymize:
        queries_data = anonymize_queries_list(queries_data)
    
    if format == "csv":
        # Создаем CSV
        output = io.StringIO()
        if queries_data:
            writer = csv.DictWriter(output, fieldnames=queries_data[0].keys())
            writer.writeheader()
            writer.writerows(queries_data)
        
        return {
            "format": "csv",
            "data": output.getvalue(),
            "anonymized": anonymize,
            "count": len(queries_data)
        }
    else:
        return {
            "format": "json",
            "data": queries_data,
            "anonymized": anonymize,
            "count": len(queries_data)
        }


@app.post("/api/settings/{key}")
async def update_setting(key: str, value: str, username: str = Depends(verify_admin)) -> Dict:
    """
    Обновить настройку
    
    Args:
        key: Ключ настройки
        value: Значение
        username: Имя пользователя
        
    Returns:
        Dict: Результат
    """
    async with get_session() as session:
        await set_setting(session, key, value)
    
    logger.info(f"Настройка {key} обновлена на {value}")
    return {"status": "success", "key": key, "value": value}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

