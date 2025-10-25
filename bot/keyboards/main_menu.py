"""
Клавиатуры для главного меню
"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database.models import UserRole


def get_main_keyboard(user_role: UserRole) -> ReplyKeyboardMarkup:
    """
    Получить главную клавиатуру в зависимости от роли пользователя
    
    Args:
        user_role: Роль пользователя
        
    Returns:
        ReplyKeyboardMarkup: Клавиатура
    """
    buttons = [
        [KeyboardButton(text="❓ Задать вопрос")],
        [KeyboardButton(text="📚 База знаний"), KeyboardButton(text="📄 Документы")],
        [KeyboardButton(text="📊 Моя статистика"), KeyboardButton(text="⚙️ Настройки")],
    ]
    
    # Для администраторов добавляем кнопку админ-панели
    if user_role == UserRole.ADMIN:
        buttons.append([KeyboardButton(text="👤 Админ-панель")])
    
    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        input_field_placeholder="Выберите действие или напишите вопрос..."
    )


def get_gdpr_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура для согласия на обработку ПД
    
    Returns:
        InlineKeyboardMarkup: Клавиатура
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Читать соглашение", callback_data="gdpr_read")],
        [InlineKeyboardButton(text="✅ Принимаю", callback_data="gdpr_accept")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="gdpr_decline")]
    ])
    return keyboard


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура админ-панели
    
    Returns:
        InlineKeyboardMarkup: Клавиатура
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🤖 Настройки AI", callback_data="admin_ai")],
        [InlineKeyboardButton(text="📚 База знаний", callback_data="admin_kb")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    return keyboard


def get_ai_provider_keyboard(current_provider: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора AI провайдера
    
    Args:
        current_provider: Текущий провайдер
        
    Returns:
        InlineKeyboardMarkup: Клавиатура
    """
    openai_text = "✅ OpenAI (активен)" if current_provider == "openai" else "OpenAI"
    gigachat_text = "✅ GigaChat (активен)" if current_provider == "gigachat" else "GigaChat"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=openai_text, callback_data="ai_provider_openai")],
        [InlineKeyboardButton(text=gigachat_text, callback_data="ai_provider_gigachat")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    return keyboard


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действия
    
    Args:
        action: Действие для подтверждения
        
    Returns:
        InlineKeyboardMarkup: Клавиатура
    """
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data=f"confirm_{action}")],
        [InlineKeyboardButton(text="❌ Нет", callback_data=f"cancel_{action}")]
    ])
    return keyboard

