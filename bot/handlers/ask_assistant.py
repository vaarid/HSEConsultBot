"""
Обработчик вопросов с использованием OpenAI Assistant API (нейроассистент)
"""
import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states.conversation import ConversationStates
from database.db import get_session
from database.crud import (
    create_message, increment_user_requests,
    create_query, create_audit_log, set_user_thread_id, get_setting,
    get_user_messages
)
from database.models import User, AIProvider
from ai.assistant_client import OpenAIAssistantClient
from services.knowledge_base import get_knowledge_base
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()
router = Router()


# Глобальный клиент ассистента
assistant_client: OpenAIAssistantClient = None


async def get_assistant_client() -> OpenAIAssistantClient:
    """
    Получить или создать клиента ассистента
    
    Returns:
        OpenAIAssistantClient: Клиент ассистента
    """
    global assistant_client
    
    if assistant_client is None:
        config = load_config()
        assistant_client = OpenAIAssistantClient(config.openai)
        
        # Получаем ID ассистента из настроек или создаем нового
        async with get_session() as session:
            assistant_id = await get_setting(session, "openai_assistant_id")
        
        if assistant_id:
            await assistant_client.get_or_create_assistant(assistant_id)
        else:
            # Создаем нового ассистента
            new_assistant_id = await assistant_client.create_assistant()
            # Сохраняем ID в настройках
            async with get_session() as session:
                from database.crud import set_setting
                await set_setting(
                    session,
                    key="openai_assistant_id",
                    value=new_assistant_id,
                    description="OpenAI Assistant ID"
                )
    
    return assistant_client


@router.message(Command("ask_assistant"))
async def cmd_ask_assistant(message: Message, state: FSMContext, db_user: User):
    """
    Обработчик команды /ask_assistant - задать вопрос нейроассистенту
    
    Args:
        message: Сообщение
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await message.answer(
        "🤖 <b>Режим нейроассистента</b>\n\n"
        "Задайте ваш вопрос по охране труда. Я использую OpenAI Assistant API "
        "с доступом к базе знаний и специализированными инструкциями.\n\n"
        "Ваши вопросы и ответы сохраняются в отдельном потоке (thread), "
        "что позволяет мне помнить контекст предыдущих обращений.",
        parse_mode="HTML"
    )
    await state.set_state(ConversationStates.waiting_for_question)


@router.message(lambda message: message.text and message.text.startswith('?'))
async def process_assistant_question(message: Message, state: FSMContext, db_user: User):
    """
    Обработка вопроса к нейроассистенту (вопросы, начинающиеся с '?')
    
    Args:
        message: Сообщение с вопросом
        state: FSM состояние
        db_user: Пользователь из БД
    """
    # Проверяем rate limit для вопросов к ассистенту
    from utils.rate_limiter import get_rate_limiter
    
    rate_limiter = get_rate_limiter()
    allowed, error_message = rate_limiter.check_rate_limit(db_user.id, "assistant_question")
    
    if not allowed:
        await message.answer(error_message, parse_mode="HTML")
        return
    
    # Записываем запрос
    rate_limiter.record_request(db_user.id, "assistant_question")
    
    question = message.text[1:].strip()  # Убираем '?' в начале
    
    if not question or len(question) < 5:
        await message.answer("❌ Вопрос слишком короткий. Пожалуйста, сформулируйте вопрос подробнее.")
        return
    
    # Проверяем на наличие персональных данных и анонимизируем
    from utils.privacy import anonymize_personal_data, should_warn_about_personal_data, get_privacy_warning
    
    anonymized_question, has_personal_data = anonymize_personal_data(question, log_detection=True)
    
    # Если обнаружены ПД, предупреждаем пользователя
    if has_personal_data:
        await message.answer(get_privacy_warning(), parse_mode="HTML")
        logger.warning(f"Пользователь {db_user.id} указал персональные данные в вопросе ассистенту. Применена анонимизация.")
    
    # Используем анонимизированный вопрос для обработки
    question_for_processing = anonymized_question if has_personal_data else question
    
    # Отправляем уведомление о обработке
    processing_msg = await message.answer("🔍 Ищу ответ в базе знаний и обращаюсь к нейроассистенту...")
    
    try:
        # 1. Получаем контекст диалога для улучшения поиска в FAQ
        async with get_session() as session:
            history = await get_user_messages(session, db_user.id, limit=3)
        
        # 2. Формируем контекстный запрос для поиска в FAQ
        context_query = question
        if history:
            # Добавляем последние сообщения для контекста
            recent_context = []
            for msg in history[-2:]:  # Последние 2 сообщения
                if msg.role == "user":
                    recent_context.append(f"Предыдущий вопрос: {msg.content}")
                elif msg.role == "assistant":
                    # Берем только начало ответа для контекста
                    answer_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                    recent_context.append(f"Предыдущий ответ: {answer_preview}")
            
            if recent_context:
                context_query = f"{' '.join(recent_context)} Текущий вопрос: {question}"
                logger.debug(f"Контекстный запрос для FAQ: {context_query}")
        
        # 3. Проверяем базу знаний FAQ с учетом контекста
        kb = get_knowledge_base()
        faq_answer = await kb.get_answer_with_validation(context_query, check_urls=True)
        
        if faq_answer and faq_answer['similarity_score'] >= 0.5:
            # Нашли релевантный ответ в FAQ
            logger.info(f"Найден ответ в FAQ: {faq_answer['question']} ({faq_answer['similarity_score']:.2%})")
            
            # Показываем ответ из FAQ
            faq_formatted = kb.format_answer_for_user(faq_answer)
            
            # Создаём кнопки для расширенного ответа и оценки
            question_hash = hash(question) % 1000000
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🤖 Получить расширенный ответ от нейроассистента",
                    callback_data=f"expand_assistant:{db_user.id}:{question_hash}"
                )],
                [
                    InlineKeyboardButton(
                        text="👍 Полезно",
                        callback_data=f"rate_assistant_helpful:{question_hash}"
                    ),
                    InlineKeyboardButton(
                        text="👎 Не то",
                        callback_data=f"rate_assistant_unhelpful:{question_hash}"
                    )
                ]
            ])
            
            await message.answer(faq_formatted, parse_mode="HTML", reply_markup=keyboard)
            
            # Удаляем сообщение о обработке
            await processing_msg.delete()
            
            # Сохраняем контекст FAQ в state для последующего использования
            await state.update_data(
                last_question=question,
                question_for_ai=question_for_processing,  # Анонимизированная версия для AI
                question_hash=question_hash,
                faq_context={
                    'question': faq_answer['question'],
                    'answer': faq_answer['answer'],
                    'legal_reference': faq_answer['legal_reference'],
                    'legal_url': faq_answer['legal_url'],
                    'similarity_score': faq_answer['similarity_score']
                }
            )
            
            logger.info(f"Ответ из FAQ показан, ожидается запрос расширенного ответа от ассистента")
            return
        
        # 4. Ответ в FAQ не найден - сразу обращаемся к ассистенту
        # Получаем клиента ассистента
        client = await get_assistant_client()
        
        # 5. Проверяем, есть ли у пользователя thread
        thread_id = db_user.assistant_thread_id
        
        # 6. Засекаем время
        start_time = time.time()
        
        # 7. Отправляем вопрос ассистенту (используем анонимизированную версию)
        response = await client.ask_assistant(
            question=question_for_processing,
            thread_id=thread_id
        )
        
        # Время ответа
        response_time = time.time() - start_time
        
        # Сохраняем thread_id для пользователя, если он новый
        if not thread_id:
            async with get_session() as session:
                await set_user_thread_id(session, db_user.id, response["thread_id"])
        
        answer = response["content"]
        
        # Сохранение в БД
        async with get_session() as session:
            # Сохраняем сообщения в историю
            await create_message(session, db_user.id, "user", question)
            await create_message(session, db_user.id, "assistant", answer)
            
            # Увеличиваем счетчик запросов
            await increment_user_requests(session, db_user.id)
            
            # Сохраняем запрос в статистику
            await create_query(
                session,
                user_id=db_user.id,
                question=question,
                answer=answer,
                ai_provider=AIProvider.OPENAI,
                ai_model=response["model"],
                response_time=response_time,
                tokens_used=response.get("tokens_used"),
                category="assistant_query"
            )
            
            # Логируем в аудит
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="assistant_question_asked",
                details={
                    "assistant_id": response["assistant_id"],
                    "thread_id": response["thread_id"],
                    "response_time": response_time,
                    "tokens": response.get("tokens_used")
                }
            )
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        # Создаём кнопки для оценки ответа ассистента
        question_hash = hash(question) % 1000000
        assistant_rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍 Полезно",
                    callback_data=f"rate_assistant_ai_helpful:{question_hash}"
                ),
                InlineKeyboardButton(
                    text="👎 Не то",
                    callback_data=f"rate_assistant_ai_unhelpful:{question_hash}"
                )
            ]
        ])
        
        # Отправляем ответ
        max_length = 4000
        prefix_text = "🤖 <b>Ответ нейроассистента:</b>\n\n"
        
        if len(answer) <= max_length:
            await message.answer(f"{prefix_text}{answer}", parse_mode="HTML", reply_markup=assistant_rating_keyboard)
        else:
            # Разбиваем на части
            parts = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
            for i, part in enumerate(parts):
                prefix = prefix_text if i == 0 else ""
                # Кнопки только на последней части
                keyboard = assistant_rating_keyboard if i == len(parts) - 1 else None
                await message.answer(f"{prefix}{part}", parse_mode="HTML", reply_markup=keyboard)
        
        # Сохраняем контекст для оценки
        await state.update_data(
            last_assistant_question=question,
            last_assistant_answer=answer,
            question_hash=question_hash
        )
        
        logger.info(
            f"Вопрос обработан через Assistant: user_id={db_user.id}, "
            f"time={response_time:.2f}s, tokens={response.get('tokens_used')}"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса через Assistant: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при обработке вашего вопроса через нейроассистента.\n"
            "Пожалуйста, попробуйте позже или используйте обычный режим (без '?' в начале)."
        )
    
    await state.clear()


@router.message(Command("reset_thread"))
async def cmd_reset_thread(message: Message, db_user: User):
    """
    Сбросить thread пользователя (начать новый диалог)
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    if db_user.assistant_thread_id:
        # Удаляем старый thread
        try:
            client = await get_assistant_client()
            await client.delete_thread(db_user.assistant_thread_id)
        except Exception as e:
            logger.warning(f"Не удалось удалить thread: {e}")
        
        # Удаляем thread_id из БД
        async with get_session() as session:
            await set_user_thread_id(session, db_user.id, None)
        
        await message.answer(
            "✅ История диалога с нейроассистентом сброшена.\n"
            "Следующий вопрос начнет новый диалог."
        )
    else:
        await message.answer("ℹ️ У вас еще нет активного диалога с нейроассистентом.")


@router.message(Command("assistant_info"))
async def cmd_assistant_info(message: Message, db_user: User):
    """
    Показать информацию о нейроассистенте
    
    Args:
        message: Сообщение
        db_user: Пользователь из БД
    """
    try:
        client = await get_assistant_client()
        info = await client.get_assistant_info()
        
        info_text = f"""
🤖 <b>Информация о нейроассистенте</b>

<b>ID:</b> <code>{info['id']}</code>
<b>Название:</b> {info['name']}
<b>Модель:</b> {info['model']}
<b>Инструменты:</b> {', '.join(info['tools'])}

<b>Ваш Thread ID:</b> <code>{db_user.assistant_thread_id or 'Не создан'}</code>

<b>Как использовать:</b>
• Начните вопрос с символа <code>?</code> (например: <code>? Какие инструктажи нужны в ДОУ?</code>)
• Используйте команду /ask_assistant
• История диалога сохраняется в вашем thread
• Чтобы начать новый диалог: /reset_thread
        """
        
        await message.answer(info_text, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации об ассистенте: {e}")
        await message.answer(
            "❌ Не удалось получить информацию о нейроассистенте. "
            "Возможно, он еще не создан."
        )


@router.callback_query(F.data.startswith("expand_assistant:"))
async def process_expand_assistant_answer(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик запроса расширенного ответа от нейроассистента
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer()
    
    # Проверяем rate limit для расширенных ответов
    from utils.rate_limiter import get_rate_limiter
    
    rate_limiter = get_rate_limiter()
    allowed, error_message = rate_limiter.check_rate_limit(db_user.id, "expand_answer")
    
    if not allowed:
        await callback.message.answer(error_message, parse_mode="HTML")
        return
    
    # Записываем запрос
    rate_limiter.record_request(db_user.id, "expand_answer")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_question')
    question_for_ai = data.get('question_for_ai', question)  # Используем анонимизированную версию, если есть
    faq_context_data = data.get('faq_context')
    
    if not question or not faq_context_data:
        await callback.message.answer("❌ Не удалось получить контекст вопроса. Попробуйте задать вопрос заново.")
        return
    
    # Отправляем уведомление о обработке
    processing_msg = await callback.message.answer("🤖 Готовлю расширенный ответ от нейроассистента...")
    
    try:
        # Формируем контекст для ассистента
        faq_context = f"""
Релевантная информация из базы знаний:
Вопрос: {faq_context_data['question']}
Ответ: {faq_context_data['answer']}
Правовая база: {faq_context_data['legal_reference']}
Ссылка: {faq_context_data['legal_url']}
"""
        
        # Получаем клиента ассистента
        client = await get_assistant_client()
        
        # Проверяем, есть ли у пользователя thread
        thread_id = db_user.assistant_thread_id
        
        # Засекаем время
        start_time = time.time()
        
        # Формируем расширенный вопрос с контекстом из FAQ (используем анонимизированную версию)
        enhanced_question = f"""{faq_context}

Вопрос пользователя: {question_for_ai}

Пожалуйста, дополни и расширь ответ из базы знаний, предоставь дополнительные детали, практические рекомендации или разъяснения."""
        
        # Отправляем вопрос ассистенту
        response = await client.ask_assistant(
            question=enhanced_question,
            thread_id=thread_id
        )
        
        # Время ответа
        response_time = time.time() - start_time
        
        # Сохраняем thread_id для пользователя, если он новый
        if not thread_id:
            async with get_session() as session:
                await set_user_thread_id(session, db_user.id, response["thread_id"])
        
        answer = response["content"]
        
        # Сохранение в БД
        async with get_session() as session:
            # Сохраняем сообщения в историю
            await create_message(session, db_user.id, "user", question)
            await create_message(session, db_user.id, "assistant", answer)
            
            # Увеличиваем счетчик запросов
            await increment_user_requests(session, db_user.id)
            
            # Сохраняем запрос в статистику
            await create_query(
                session,
                user_id=db_user.id,
                question=question,
                answer=answer,
                ai_provider=AIProvider.OPENAI,
                ai_model=response["model"],
                response_time=response_time,
                tokens_used=response.get("tokens_used"),
                category="assistant_expand"
            )
            
            # Логируем в аудит
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="assistant_expand_answer",
                details={
                    "assistant_id": response["assistant_id"],
                    "thread_id": response["thread_id"],
                    "response_time": response_time,
                    "tokens": response.get("tokens_used")
                }
            )
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        # Создаём кнопки для оценки расширенного ответа ассистента
        question_hash = hash(question_for_ai) % 1000000
        assistant_rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍 Полезно",
                    callback_data=f"rate_assistant_ai_helpful:{question_hash}"
                ),
                InlineKeyboardButton(
                    text="👎 Не то",
                    callback_data=f"rate_assistant_ai_unhelpful:{question_hash}"
                )
            ]
        ])
        
        # Отправляем ответ
        max_length = 4000
        prefix_text = "🤖 <b>Расширенный ответ от нейроассистента:</b>\n\n"
        
        if len(answer) <= max_length - len(prefix_text):
            await callback.message.answer(f"{prefix_text}{answer}", parse_mode="HTML", reply_markup=assistant_rating_keyboard)
        else:
            # Разбиваем на части
            parts = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
            for i, part in enumerate(parts):
                prefix = prefix_text if i == 0 else ""
                # Кнопки только на последней части
                keyboard = assistant_rating_keyboard if i == len(parts) - 1 else None
                await callback.message.answer(f"{prefix}{part}", parse_mode="HTML", reply_markup=keyboard)
        
        # Информация об использовании
        await callback.message.answer("✅ <b>Использована база знаний + нейроассистент</b>", parse_mode="HTML")
        
        # Сохраняем контекст для оценки
        await state.update_data(
            last_assistant_question=question,
            last_assistant_answer=answer,
            question_hash=question_hash
        )
        
        logger.info(
            f"Расширенный ответ от ассистента: user_id={db_user.id}, "
            f"time={response_time:.2f}s"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении расширенного ответа от ассистента: {e}", exc_info=True)
        await processing_msg.delete()
        await callback.message.answer(
            "❌ Произошла ошибка при обработке вашего запроса.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )


@router.callback_query(F.data.startswith("rate_assistant_helpful:"))
async def process_rate_assistant_helpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик положительной оценки ответа из FAQ (режим ассистента)
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("✅ Спасибо за оценку!")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_question')
    faq_context = data.get('faq_context')
    
    if question and faq_context:
        # Логируем положительную оценку
        async with get_session() as session:
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="faq_rated_helpful_assistant",
                details={
                    "user_question": question,
                    "faq_question": faq_context['question'],
                    "similarity_score": faq_context.get('similarity_score', 0),
                    "rating": "helpful"
                }
            )
        
        logger.info(
            f"FAQ ответ оценён положительно (ассистент): user_id={db_user.id}, "
            f"similarity={faq_context.get('similarity_score', 0):.2%}, "
            f"faq_q='{faq_context['question'][:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки оценки
        try:
            # Создаём новую клавиатуру только с кнопкой расширенного ответа
            question_hash = data.get('question_hash')
            if question_hash:
                new_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🤖 Получить расширенный ответ от нейроассистента",
                        callback_data=f"expand_assistant:{db_user.id}:{question_hash}"
                    )]
                ])
                await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")


@router.callback_query(F.data.startswith("rate_assistant_unhelpful:"))
async def process_rate_assistant_unhelpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик отрицательной оценки ответа из FAQ (режим ассистента)
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("📝 Спасибо за обратную связь! Обращаюсь к нейроассистенту.")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_question')
    question_for_ai = data.get('question_for_ai', question)  # Используем анонимизированную версию, если есть
    faq_context = data.get('faq_context')
    
    if question and faq_context:
        # Логируем отрицательную оценку
        async with get_session() as session:
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="faq_rated_unhelpful_assistant",
                details={
                    "user_question": question,
                    "faq_question": faq_context['question'],
                    "similarity_score": faq_context.get('similarity_score', 0),
                    "rating": "unhelpful"
                }
            )
        
        logger.warning(
            f"FAQ ответ оценён отрицательно (ассистент): user_id={db_user.id}, "
            f"similarity={faq_context.get('similarity_score', 0):.2%}, "
            f"user_q='{question}', faq_q='{faq_context['question'][:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")
        
        # Автоматически вызываем нейроассистента для более точного ответа
        processing_msg = await callback.message.answer("🤖 Обращаюсь к нейроассистенту для более точного ответа...")
        
        try:
            # Получаем клиента ассистента
            client = await get_assistant_client()
            
            # Проверяем, есть ли у пользователя thread
            thread_id = db_user.assistant_thread_id
            
            # Засекаем время
            start_time = time.time()
            
            # Отправляем вопрос ассистенту (используем анонимизированную версию)
            response = await client.ask_assistant(
                question=question_for_ai,
                thread_id=thread_id
            )
            
            # Время ответа
            response_time = time.time() - start_time
            
            # Сохраняем thread_id для пользователя, если он новый
            if not thread_id:
                async with get_session() as session:
                    await set_user_thread_id(session, db_user.id, response["thread_id"])
            
            answer = response["content"]
            
            # Сохранение в БД
            async with get_session() as session:
                # Сохраняем сообщения в историю
                await create_message(session, db_user.id, "user", question)
                await create_message(session, db_user.id, "assistant", answer)
                
                # Увеличиваем счетчик запросов
                await increment_user_requests(session, db_user.id)
                
                # Сохраняем запрос в статистику
                await create_query(
                    session,
                    user_id=db_user.id,
                    question=question,
                    answer=answer,
                    ai_provider=AIProvider.OPENAI,
                    ai_model=response["model"],
                    response_time=response_time,
                    tokens_used=response.get("tokens_used"),
                    category="assistant_after_negative"
                )
                
                # Логируем в аудит
                await create_audit_log(
                    session,
                    user_id=db_user.id,
                    action="assistant_after_negative_rating",
                    details={
                        "assistant_id": response["assistant_id"],
                        "thread_id": response["thread_id"],
                        "response_time": response_time,
                        "tokens": response.get("tokens_used")
                    }
                )
            
            # Удаляем сообщение о обработке
            await processing_msg.delete()
            
            # Отправляем ответ
            max_length = 4000
            prefix_text = "🤖 <b>Ответ нейроассистента:</b>\n\n"
            
            if len(answer) <= max_length:
                await callback.message.answer(f"{prefix_text}{answer}", parse_mode="HTML")
            else:
                # Разбиваем на части
                parts = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
                for i, part in enumerate(parts):
                    prefix = prefix_text if i == 0 else ""
                    await callback.message.answer(f"{prefix}{part}", parse_mode="HTML")
            
            logger.info(
                f"Ассистент ответ после отрицательной оценки: user_id={db_user.id}, "
                f"time={response_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении ответа ассистента после отрицательной оценки: {e}", exc_info=True)
            await processing_msg.delete()
            await callback.message.answer(
                "❌ Произошла ошибка при обращении к нейроассистенту.\n"
                "Пожалуйста, попробуйте задать вопрос заново."
            )


@router.callback_query(F.data.startswith("rate_assistant_ai_helpful:"))
async def process_rate_assistant_ai_helpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик положительной оценки ответа нейроассистента
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("👍 Спасибо за обратную связь!")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_assistant_question')
    answer = data.get('last_assistant_answer')
    
    if question and answer:
        # Логируем положительную оценку
        async with get_session() as session:
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="assistant_ai_rated_helpful",
                details={
                    "question": question[:100],  # Первые 100 символов
                    "answer_length": len(answer),
                    "rating": "helpful"
                }
            )
        
        logger.info(
            f"Ответ ассистента оценён положительно: user_id={db_user.id}, "
            f"question='{question[:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")


@router.callback_query(F.data.startswith("rate_assistant_ai_unhelpful:"))
async def process_rate_assistant_ai_unhelpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик отрицательной оценки ответа нейроассистента
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("📝 Спасибо за обратную связь!")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_assistant_question')
    answer = data.get('last_assistant_answer')
    
    if question and answer:
        # Логируем отрицательную оценку
        async with get_session() as session:
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="assistant_ai_rated_unhelpful",
                details={
                    "question": question[:100],  # Первые 100 символов
                    "answer_length": len(answer),
                    "rating": "unhelpful"
                }
            )
        
        logger.warning(
            f"Ответ ассистента оценён отрицательно: user_id={db_user.id}, "
            f"question='{question[:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")
        
        # Информируем пользователя
        await callback.message.answer(
            "Спасибо за обратную связь! Это поможет нам улучшить качество ответов нейроассистента.\n\n"
            "Вы можете:\n"
            "• Переформулировать вопрос для получения другого ответа\n"
            "• Сбросить историю диалога через /reset_thread\n"
            "• Обратиться к администратору через /help"
        )
    
    # Очищаем state
    await state.clear()

