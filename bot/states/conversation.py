"""
FSM состояния для разговора с ботом
"""
from aiogram.fsm.state import State, StatesGroup


class ConversationStates(StatesGroup):
    """
    Состояния для ведения диалога
    """
    waiting_for_question = State()  # Ожидание вопроса от пользователя
    processing = State()  # Обработка запроса


class GDPRStates(StatesGroup):
    """
    Состояния для работы с GDPR
    """
    waiting_for_consent = State()  # Ожидание согласия на обработку ПД
    waiting_for_delete_confirmation = State()  # Подтверждение удаления данных

