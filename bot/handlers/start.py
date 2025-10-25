"""
Обработчик команды /start
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards.main_menu import get_main_keyboard, get_gdpr_keyboard
from bot.states.conversation import GDPRStates
from database.db import get_session
from database.crud import accept_gdpr, create_audit_log
from database.models import User
from utils.logger import setup_logger

logger = setup_logger()
router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, db_user: User):
    """
    Обработчик команды /start
    
    Args:
        message: Сообщение
        state: FSM состояние
        db_user: Пользователь из БД
    """
    # Проверяем, принял ли пользователь GDPR
    if not db_user.gdpr_accepted:
        await message.answer(
            "👋 Добро пожаловать в бот-консультант по охране труда и технике безопасности в ДОУ!\n\n"
            "Я помогу вам с вопросами по:\n"
            "✅ Трудовому законодательству РФ\n"
            "✅ Охране труда в детских садах\n"
            "✅ СанПиН и нормативным документам\n"
            "✅ Проведению инструктажей\n"
            "✅ СОУТ и расследованию несчастных случаев\n\n"
            "⚠️ <b>Согласие на обработку персональных данных (ФЗ-152)</b>\n\n"
            "Для работы бота необходимо ваше согласие на обработку персональных данных:\n"
            "• Telegram ID\n"
            "• Имя пользователя\n"
            "• История запросов\n\n"
            "Данные используются исключительно для функционирования бота и не передаются третьим лицам.\n"
            "Вы можете в любой момент удалить свои данные командой /gdpr",
            reply_markup=get_gdpr_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(GDPRStates.waiting_for_consent)
    else:
        # Пользователь уже принял согласие
        await message.answer(
            f"👋 С возвращением, {db_user.first_name or 'пользователь'}!\n\n"
            f"Ваша роль: <b>{db_user.role.value}</b>\n"
            f"Всего запросов: {db_user.total_requests}\n\n"
            "Задайте мне вопрос по охране труда или выберите действие из меню ниже 👇",
            reply_markup=get_main_keyboard(db_user.role),
            parse_mode="HTML"
        )


@router.callback_query(lambda c: c.data == "gdpr_accept")
async def process_gdpr_accept(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик принятия GDPR
    
    Args:
        callback: Callback query
        state: FSM состояние
        db_user: Пользователь из БД
    """
    async with get_session() as session:
        # Обновляем согласие в БД
        await accept_gdpr(session, db_user.id)
        
        # Логируем действие
        await create_audit_log(
            session,
            user_id=db_user.id,
            action="gdpr_accepted",
            details={"timestamp": str(callback.message.date)}
        )
    
    logger.info(f"Пользователь {db_user.id} принял согласие на обработку ПД")
    
    await callback.message.edit_text(
        "✅ Спасибо! Согласие на обработку персональных данных принято.\n\n"
        "Теперь вы можете пользоваться всеми функциями бота!"
    )
    
    await callback.message.answer(
        "Задайте мне вопрос по охране труда или выберите действие из меню 👇",
        reply_markup=get_main_keyboard(db_user.role)
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(lambda c: c.data == "gdpr_read")
async def process_gdpr_read(callback: CallbackQuery):
    """
    Обработчик просмотра полного соглашения
    
    Args:
        callback: Callback query
    """
    await callback.answer()
    
    agreement_text = """
📄 <b>СОГЛАШЕНИЕ ОБ ОБРАБОТКЕ ПЕРСОНАЛЬНЫХ ДАННЫХ</b>

<b>1. ОБЩИЕ ПОЛОЖЕНИЯ</b>

Настоящее Соглашение об обработке персональных данных (далее — Соглашение) разработано в соответствии с Федеральным законом от 27.07.2006 № 152-ФЗ «О персональных данных».

Используя Telegram-бот «HSEConsultBot» (далее — Бот), Пользователь даёт своё согласие на обработку персональных данных на условиях, изложенных в настоящем Соглашении.

<b>2. КАКИЕ ДАННЫЕ МЫ СОБИРАЕМ</b>

При использовании Бота мы собираем следующие данные:
• Telegram ID (уникальный идентификатор)
• Имя пользователя (username)
• Имя и фамилия (если указаны в профиле Telegram)
• История запросов к Боту
• Дата и время обращений
• Статистика использования

<b>3. ЦЕЛИ ОБРАБОТКИ ДАННЫХ</b>

Персональные данные обрабатываются для:
• Идентификации Пользователя
• Предоставления консультационных услуг по охране труда
• Сохранения истории диалога для контекста
• Улучшения качества ответов
• Ведения статистики использования
• Обеспечения безопасности системы

<b>4. ПРАВОВЫЕ ОСНОВАНИЯ</b>

Обработка персональных данных осуществляется на основании:
• Согласия субъекта персональных данных (ст. 6 ФЗ-152)
• Необходимости исполнения договора об оказании услуг

<b>5. СПОСОБЫ ОБРАБОТКИ</b>

Обработка данных осуществляется:
• С использованием средств автоматизации
• С применением мер защиты от несанкционированного доступа
• В защищённой базе данных PostgreSQL
• С использованием AI-сервисов для обработки запросов

<b>6. ПЕРЕДАЧА ТРЕТЬИМ ЛИЦАМ И АНОНИМИЗАЦИЯ</b>

⚠️ <b>ВАЖНО:</b> Ваши персональные данные (ID, имя, фамилия, username) НЕ передаются третьим лицам!

Для обработки ваших вопросов используются AI-сервисы, которым передаются:
✅ Только текст ваших вопросов и ответов (без идентификационных данных)
✅ История диалога (для контекста, анонимно)

НЕ передаются:
❌ Telegram ID
❌ Имя и фамилия
❌ Username
❌ Любые другие персональные данные

Ваши данные:
• НЕ передаются в рекламных или маркетинговых целях
• НЕ продаются третьим лицам
• Хранятся только в нашей защищённой базе данных

<b>7. СРОК ХРАНЕНИЯ</b>

Персональные данные хранятся:
• В течение всего периода использования Бота
• До момента запроса на удаление данных
• Логи действий — не более 1 года

<b>8. ПРАВА ПОЛЬЗОВАТЕЛЯ</b>

Вы имеете право:
✅ Получить информацию о хранимых данных
✅ Потребовать удаления всех данных
✅ Отозвать согласие в любой момент
✅ Обжаловать действия Оператора

<b>9. КАК РЕАЛИЗОВАТЬ ПРАВА</b>

Для реализации своих прав используйте:
• Команду /gdpr — просмотр и управление данными
• Команду /delete_my_data — полное удаление данных

<b>10. БЕЗОПАСНОСТЬ</b>

Мы применяем:
• Шифрование при передаче данных
• Защищённое хранение в базе данных
• Контроль доступа к системе
• Аудит действий пользователей

<b>11. ИЗМЕНЕНИЯ СОГЛАШЕНИЯ</b>

Оператор вправе вносить изменения в Соглашение.
Новая редакция вступает в силу с момента публикации.

<b>12. КОНТАКТНАЯ ИНФОРМАЦИЯ</b>

По вопросам обработки персональных данных:
• Используйте команду /help
• Или обратитесь к администратору бота

<b>13. СОГЛАСИЕ</b>

Нажимая кнопку «✅ Принимаю», вы:
• Подтверждаете, что ознакомились с настоящим Соглашением
• Даёте согласие на обработку персональных данных
• Понимаете свои права и способы их реализации

Дата вступления в силу: 17.10.2025
    """
    
    # Создаём клавиатуру только с кнопками принятия/отказа (без кнопки "Читать соглашение")
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    decision_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принимаю", callback_data="gdpr_accept")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="gdpr_decline")]
    ])
    
    await callback.message.answer(
        agreement_text,
        parse_mode="HTML",
        reply_markup=decision_keyboard
    )


@router.callback_query(lambda c: c.data == "gdpr_decline")
async def process_gdpr_decline(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик отказа от GDPR
    
    Args:
        callback: Callback query
        state: FSM состояние
    """
    await callback.message.edit_text(
        "❌ К сожалению, без согласия на обработку персональных данных использование бота невозможно.\n\n"
        "Если передумаете, отправьте /start снова."
    )
    
    await state.clear()
    await callback.answer()

