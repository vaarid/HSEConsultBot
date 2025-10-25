"""
Утилиты для защиты персональных данных (ФЗ-152)
"""

import re
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger()


# Паттерны для обнаружения персональных данных
PHONE_PATTERN = re.compile(r'(\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}')
EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
PASSPORT_PATTERN = re.compile(r'\b\d{4}\s?\d{6}\b')  # Серия и номер паспорта
SNILS_PATTERN = re.compile(r'\b\d{3}-\d{3}-\d{3}\s?\d{2}\b')  # СНИЛС
INN_PATTERN = re.compile(r'\b\d{10,12}\b')  # ИНН (10 или 12 цифр)


def anonymize_personal_data(text: str, log_detection: bool = True) -> tuple[str, bool]:
    """
    Анонимизирует персональные данные в тексте
    
    Args:
        text: Исходный текст
        log_detection: Логировать обнаружение ПД
        
    Returns:
        tuple[str, bool]: (Анонимизированный текст, Были ли обнаружены ПД)
    """
    original_text = text
    detected = False
    
    # Замена телефонов
    if PHONE_PATTERN.search(text):
        text = PHONE_PATTERN.sub('[ТЕЛЕФОН]', text)
        detected = True
    
    # Замена email
    if EMAIL_PATTERN.search(text):
        text = EMAIL_PATTERN.sub('[EMAIL]', text)
        detected = True
    
    # Замена паспортов
    if PASSPORT_PATTERN.search(text):
        text = PASSPORT_PATTERN.sub('[ПАСПОРТ]', text)
        detected = True
    
    # Замена СНИЛС
    if SNILS_PATTERN.search(text):
        text = SNILS_PATTERN.sub('[СНИЛС]', text)
        detected = True
    
    # Замена ИНН (только если 10 или 12 цифр подряд)
    # Будьте осторожны, чтобы не заменить другие числа
    
    if detected and log_detection:
        logger.warning(f"Обнаружены персональные данные в тексте пользователя. Анонимизировано.")
        logger.debug(f"Длина исходного текста: {len(original_text)}, после анонимизации: {len(text)}")
    
    return text, detected


def should_warn_about_personal_data(text: str) -> bool:
    """
    Проверяет, содержит ли текст персональные данные
    
    Args:
        text: Текст для проверки
        
    Returns:
        bool: True если обнаружены ПД
    """
    patterns = [
        PHONE_PATTERN,
        EMAIL_PATTERN,
        PASSPORT_PATTERN,
        SNILS_PATTERN
    ]
    
    return any(pattern.search(text) for pattern in patterns)


def get_privacy_warning() -> str:
    """
    Возвращает предупреждение о защите персональных данных
    
    Returns:
        str: Текст предупреждения
    """
    return """
⚠️ <b>Обнаружены персональные данные!</b>

В вашем вопросе содержатся данные, которые могут быть персональными (телефон, email, паспорт и т.д.).

🔒 <b>Для вашей безопасности:</b>
• Персональные данные были автоматически анонимизированы
• Они НЕ будут переданы в AI-сервисы
• Рекомендуем НЕ указывать личные данные в открытом виде

Ваш вопрос обработан с анонимизацией.
"""


def anonymize_user_info_for_logging(user_id: int, username: Optional[str] = None) -> str:
    """
    Создает анонимизированную строку для логирования
    
    Args:
        user_id: ID пользователя
        username: Username пользователя (опционально)
        
    Returns:
        str: Анонимизированная строка вида "user_xxx" или "user_xxx (@username)"
    """
    # Показываем только последние 3 цифры ID
    masked_id = f"***{str(user_id)[-3:]}"
    
    if username:
        return f"user_{masked_id} (@{username})"
    return f"user_{masked_id}"

