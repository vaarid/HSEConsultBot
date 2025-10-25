"""
Утилиты для аналитики и анонимизации данных
"""
import re
from typing import Dict, List, Any
from utils.logger import setup_logger

logger = setup_logger()


def anonymize_user_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Анонимизировать персональные данные пользователя
    
    Args:
        data: Словарь с данными пользователя
        
    Returns:
        Dict: Анонимизированные данные
    """
    anonymized = data.copy()
    
    # Анонимизируем username
    if 'username' in anonymized and anonymized['username']:
        anonymized['username'] = f"user_{anonymized.get('id', 'unknown')}"
    
    # Анонимизируем имя и фамилию
    if 'first_name' in anonymized and anonymized['first_name']:
        anonymized['first_name'] = "***"
    
    if 'last_name' in anonymized and anonymized['last_name']:
        anonymized['last_name'] = "***"
    
    return anonymized


def anonymize_query_text(text: str) -> str:
    """
    Анонимизировать текст запроса/ответа от персональных данных
    
    Args:
        text: Текст для анонимизации
        
    Returns:
        str: Анонимизированный текст
    """
    if not text:
        return text
    
    # Паттерны для поиска персональных данных
    patterns = {
        # ФИО (Иванов Иван Иванович)
        r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\b': '[ФИО]',
        # ФИ (Иванов Иван)
        r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+\b': '[ФИ]',
        # Телефоны
        r'\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}': '[ТЕЛЕФОН]',
        # Email
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b': '[EMAIL]',
        # Паспортные данные
        r'\b\d{4}\s?\d{6}\b': '[ПАСПОРТ]',
        # СНИЛС
        r'\b\d{3}-\d{3}-\d{3}\s\d{2}\b': '[СНИЛС]',
        # ИНН
        r'\b\d{10,12}\b': '[ИНН]',
        # Адреса (упрощенный паттерн)
        r'\bг\.\s*[А-ЯЁ][а-яё]+': '[ГОРОД]',
        r'\bул\.\s*[А-ЯЁ][а-яё]+': '[УЛИЦА]',
    }
    
    anonymized_text = text
    
    for pattern, replacement in patterns.items():
        anonymized_text = re.sub(pattern, replacement, anonymized_text, flags=re.IGNORECASE)
    
    return anonymized_text


def anonymize_queries_list(queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Анонимизировать список запросов
    
    Args:
        queries: Список запросов
        
    Returns:
        List[Dict]: Анонимизированные запросы
    """
    anonymized_queries = []
    
    for query in queries:
        anonymized_query = query.copy()
        
        # Анонимизируем текст вопроса и ответа
        if 'question' in anonymized_query:
            anonymized_query['question'] = anonymize_query_text(anonymized_query['question'])
        
        if 'answer' in anonymized_query:
            anonymized_query['answer'] = anonymize_query_text(anonymized_query['answer'])
        
        # Анонимизируем данные пользователя
        anonymized_query = anonymize_user_data(anonymized_query)
        
        anonymized_queries.append(anonymized_query)
    
    return anonymized_queries


def get_analytics_summary(queries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Получить сводку аналитики без персональных данных
    
    Args:
        queries: Список запросов
        
    Returns:
        Dict: Сводка аналитики
    """
    if not queries:
        return {
            "total_queries": 0,
            "avg_response_time": 0,
            "total_tokens": 0,
            "categories": {},
            "ai_providers": {}
        }
    
    # Общая статистика
    total_queries = len(queries)
    
    # Среднее время ответа
    response_times = [q.get('response_time', 0) for q in queries if q.get('response_time')]
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    # Общее количество токенов
    total_tokens = sum(q.get('tokens_used', 0) for q in queries if q.get('tokens_used'))
    
    # Статистика по категориям
    categories = {}
    for query in queries:
        category = query.get('category')
        if category:
            categories[category] = categories.get(category, 0) + 1
    
    # Статистика по AI провайдерам
    ai_providers = {}
    for query in queries:
        provider = query.get('ai_provider')
        if provider:
            ai_providers[provider] = ai_providers.get(provider, 0) + 1
    
    return {
        "total_queries": total_queries,
        "avg_response_time": round(avg_response_time, 2),
        "total_tokens": total_tokens,
        "categories": categories,
        "ai_providers": ai_providers
    }


def is_sensitive_data(text: str) -> bool:
    """
    Проверить, содержит ли текст чувствительные данные
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True если содержит чувствительные данные
    """
    if not text:
        return False
    
    # Паттерны чувствительных данных
    sensitive_patterns = [
        r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+',  # ФИО
        r'\+?[78][\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}',  # Телефон
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{4}\s?\d{6}\b',  # Паспорт
        r'\b\d{3}-\d{3}-\d{3}\s\d{2}\b',  # СНИЛС
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    
    return False


def create_analytics_report(queries: List[Dict[str, Any]], anonymize: bool = True) -> Dict[str, Any]:
    """
    Создать отчет аналитики
    
    Args:
        queries: Список запросов
        anonymize: Анонимизировать ли данные
        
    Returns:
        Dict: Отчет аналитики
    """
    if anonymize:
        queries = anonymize_queries_list(queries)
    
    summary = get_analytics_summary(queries)
    
    # Топ запросов (анонимизированные)
    top_queries = []
    for query in queries[:10]:  # Топ 10
        top_queries.append({
            "question": query.get('question', '')[:100] + "..." if len(query.get('question', '')) > 100 else query.get('question', ''),
            "category": query.get('category'),
            "response_time": query.get('response_time'),
            "created_at": query.get('created_at')
        })
    
    return {
        "summary": summary,
        "top_queries": top_queries,
        "anonymized": anonymize,
        "generated_at": "2025-01-01T00:00:00Z"  # В реальном приложении использовать datetime.now()
    }
