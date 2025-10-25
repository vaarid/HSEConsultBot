"""
Обработчик вопросов пользователей
"""
import time
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states.conversation import ConversationStates
from database.db import get_session
from database.crud import (
    create_message, get_user_messages, increment_user_requests,
    create_query, create_audit_log
)
from database.models import User, AIProvider
from ai.factory import AIClientFactory
from ai.prompts import get_system_prompt, CATEGORIZATION_PROMPT
from services.knowledge_base import get_knowledge_base
from utils.config import load_config
from utils.logger import setup_logger

logger = setup_logger()
router = Router()


@router.message(Command("ask"))
async def cmd_ask(message: Message, state: FSMContext, db_user: User):
    """
    Обработчик команды /ask
    
    Args:
        message: Сообщение
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await message.answer(
        "❓ Задайте ваш вопрос по охране труда.\n\n"
        "Я постараюсь дать развернутый ответ со ссылками на законодательство РФ."
    )
    await state.set_state(ConversationStates.waiting_for_question)


@router.message(ConversationStates.waiting_for_question)
@router.message(lambda message: message.text and not message.text.startswith('/'))
async def process_question(message: Message, state: FSMContext, db_user: User):
    """
    Обработка вопроса пользователя
    
    Args:
        message: Сообщение с вопросом
        state: FSM состояние
        db_user: Пользователь из БД
    """
    # Проверяем rate limit
    from utils.rate_limiter import get_rate_limiter
    
    rate_limiter = get_rate_limiter()
    allowed, error_message = rate_limiter.check_rate_limit(db_user.id, "question")
    
    if not allowed:
        await message.answer(error_message, parse_mode="HTML")
        return
    
    # Записываем запрос
    rate_limiter.record_request(db_user.id, "question")
    
    question = message.text
    
    if not question or len(question) < 5:
        await message.answer("❌ Вопрос слишком короткий. Пожалуйста, сформулируйте вопрос подробнее.")
        return
    
    # Проверяем на наличие персональных данных и анонимизируем
    from utils.privacy import anonymize_personal_data, should_warn_about_personal_data, get_privacy_warning
    
    anonymized_question, has_personal_data = anonymize_personal_data(question, log_detection=True)
    
    # Если обнаружены ПД, предупреждаем пользователя
    if has_personal_data:
        await message.answer(get_privacy_warning(), parse_mode="HTML")
        logger.warning(f"Пользователь {db_user.id} указал персональные данные в вопросе. Применена анонимизация.")
    
    # Используем анонимизированный вопрос для обработки
    question_for_processing = anonymized_question if has_personal_data else question
    
    # Отправляем уведомление о обработке
    processing_msg = await message.answer("🔍 Ищу ответ в базе знаний...")
    
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
                    text="🤖 Получить расширенный ответ от AI",
                    callback_data=f"expand_answer:{db_user.id}:{question_hash}"
                )],
                [
                    InlineKeyboardButton(
                        text="👍 Полезно",
                        callback_data=f"rate_helpful:{question_hash}"
                    ),
                    InlineKeyboardButton(
                        text="👎 Не то",
                        callback_data=f"rate_unhelpful:{question_hash}"
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
            
            logger.info(f"Ответ из FAQ показан, ожидается запрос расширенного ответа")
            return
        else:
            # Ответ в FAQ не найден - сразу обращаемся к AI
            await processing_msg.edit_text("⏳ Обрабатываю ваш вопрос через AI...")
        
        # 4. Загрузка конфигурации
        config = load_config()
        
        # 5. Создание AI клиента
        ai_client = AIClientFactory.create_client(config)
        
        # 6. Получение истории сообщений
        async with get_session() as session:
            history = await get_user_messages(session, db_user.id, limit=config.app.max_history_length)
        
        # 7. Формирование сообщений для AI
        messages = [
            {"role": "system", "content": get_system_prompt(db_user.role.value)}
        ]
        
        # 8. Добавляем историю
        for hist_msg in history:
            messages.append({
                "role": hist_msg.role,
                "content": hist_msg.content
            })
        
        # 9. Добавляем текущий вопрос (используем анонимизированную версию)
        messages.append({
            "role": "user",
            "content": question_for_processing
        })
        
        # 10. Засекаем время
        start_time = time.time()
        
        # 11. Отправка запроса к AI
        response = await ai_client.chat_completion(messages)
        
        # 12. Время ответа
        response_time = time.time() - start_time
        
        answer = response["content"]
        
        # 13. Сохранение в БД
        async with get_session() as session:
            # Сохраняем сообщения в историю
            await create_message(session, db_user.id, "user", question)
            await create_message(session, db_user.id, "assistant", answer)
            
            # Увеличиваем счетчик запросов
            await increment_user_requests(session, db_user.id)
            
            # Категоризация вопроса (опционально)
            category = None
            try:
                cat_response = await ai_client.chat_completion(
                    [{"role": "user", "content": CATEGORIZATION_PROMPT.format(question=question)}],
                    max_tokens=10
                )
                category = cat_response["content"].strip().lower()
            except Exception as e:
                logger.warning(f"Не удалось категоризировать вопрос: {e}")
            
            # Сохраняем запрос в статистику
            await create_query(
                session,
                user_id=db_user.id,
                question=question,
                answer=answer,
                ai_provider=AIProvider(config.app.ai_provider),
                ai_model=response["model"],
                response_time=response_time,
                tokens_used=response.get("tokens_used"),
                category=category
            )
            
            # Логируем в аудит
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="question_asked",
                details={
                    "category": category,
                    "response_time": response_time,
                    "tokens": response.get("tokens_used")
                }
            )
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        # Создаём кнопки для оценки AI ответа
        question_hash = hash(question) % 1000000
        ai_rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍 Полезно",
                    callback_data=f"rate_ai_helpful:{question_hash}"
                ),
                InlineKeyboardButton(
                    text="👎 Не то",
                    callback_data=f"rate_ai_unhelpful:{question_hash}"
                )
            ]
        ])
        
        # Отправляем ответ
        # Разбиваем длинный ответ на части (Telegram ограничение 4096 символов)
        max_length = 4000
        
        if len(answer) <= max_length:
            await message.answer(answer, parse_mode="Markdown", reply_markup=ai_rating_keyboard)
        else:
            # Разбиваем на части
            parts = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
            for i, part in enumerate(parts):
                # Кнопки только на последней части
                keyboard = ai_rating_keyboard if i == len(parts) - 1 else None
                await message.answer(part, parse_mode="Markdown", reply_markup=keyboard)
        
        # Сохраняем контекст для оценки
        await state.update_data(
            last_ai_question=question,
            last_ai_answer=answer,
            question_hash=question_hash
        )
        
        logger.info(
            f"Вопрос обработан: user_id={db_user.id}, "
            f"category={category}, time={response_time:.2f}s"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса: {e}", exc_info=True)
        await processing_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при обработке вашего вопроса.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
    
    await state.clear()


@router.callback_query(F.data.startswith("expand_answer:"))
async def process_expand_answer(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик запроса расширенного ответа от AI
    
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
    processing_msg = await callback.message.answer("🤖 Готовлю расширенный ответ от AI...")
    
    try:
        # Формируем контекст для AI
        faq_context = f"""
Релевантная информация из базы знаний:
Вопрос: {faq_context_data['question']}
Ответ: {faq_context_data['answer']}
Правовая база: {faq_context_data['legal_reference']}
Ссылка: {faq_context_data['legal_url']}
"""
        
        # Загрузка конфигурации
        config = load_config()
        
        # Создание AI клиента
        ai_client = AIClientFactory.create_client(config)
        
        # Получение истории сообщений
        async with get_session() as session:
            history = await get_user_messages(session, db_user.id, limit=config.app.max_history_length)
        
        # Формирование сообщений для AI
        messages = [
            {"role": "system", "content": get_system_prompt(db_user.role.value)}
        ]
        
        # Добавляем историю
        for hist_msg in history:
            messages.append({
                "role": hist_msg.role,
                "content": hist_msg.content
            })
        
        # Формируем вопрос с контекстом из FAQ (используем анонимизированную версию)
        enhanced_question = f"""{faq_context}

Вопрос пользователя: {question_for_ai}

Пожалуйста, дополни и расширь ответ из базы знаний, предоставь дополнительные детали, практические рекомендации или разъяснения."""
        
        # Добавляем текущий вопрос
        messages.append({
            "role": "user",
            "content": enhanced_question
        })
        
        # Засекаем время
        start_time = time.time()
        
        # Отправка запроса к AI
        response = await ai_client.chat_completion(messages)
        
        # Время ответа
        response_time = time.time() - start_time
        
        answer = response["content"]
        
        # Сохранение в БД
        async with get_session() as session:
            # Сохраняем сообщения в историю
            await create_message(session, db_user.id, "user", question)
            await create_message(session, db_user.id, "assistant", answer)
            
            # Увеличиваем счетчик запросов
            await increment_user_requests(session, db_user.id)
            
            # Категоризация вопроса
            category = None
            try:
                cat_response = await ai_client.chat_completion(
                    [{"role": "user", "content": CATEGORIZATION_PROMPT.format(question=question)}],
                    max_tokens=10
                )
                category = cat_response["content"].strip().lower()
            except Exception as e:
                logger.warning(f"Не удалось категоризировать вопрос: {e}")
            
            # Сохраняем запрос в статистику
            await create_query(
                session,
                user_id=db_user.id,
                question=question,
                answer=answer,
                ai_provider=AIProvider(config.app.ai_provider),
                ai_model=response["model"],
                response_time=response_time,
                tokens_used=response.get("tokens_used"),
                category=category
            )
            
            # Логируем в аудит
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="expand_answer_requested",
                details={
                    "question": question,
                    "model": response["model"],
                    "category": category,
                    "response_time": response_time,
                    "tokens": response.get("tokens_used")
                }
            )
        
        # Удаляем сообщение о обработке
        await processing_msg.delete()
        
        # Создаём кнопки для оценки расширенного AI ответа
        question_hash = hash(question) % 1000000
        ai_rating_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍 Полезно",
                    callback_data=f"rate_ai_helpful:{question_hash}"
                ),
                InlineKeyboardButton(
                    text="👎 Не то",
                    callback_data=f"rate_ai_unhelpful:{question_hash}"
                )
            ]
        ])
        
        # Отправляем ответ
        max_length = 4000
        prefix_text = "🤖 Расширенный ответ от AI:\n\n"
        
        if len(answer) <= max_length - len(prefix_text):
            await callback.message.answer(f"{prefix_text}{answer}", parse_mode="Markdown", reply_markup=ai_rating_keyboard)
        else:
            # Разбиваем на части
            parts = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
            for i, part in enumerate(parts):
                prefix = prefix_text if i == 0 else ""
                # Кнопки только на последней части
                keyboard = ai_rating_keyboard if i == len(parts) - 1 else None
                await callback.message.answer(f"{prefix}{part}", parse_mode="Markdown", reply_markup=keyboard)
        
        # Информация об использовании
        await callback.message.answer("✅ <b>Использована база знаний + AI</b>", parse_mode="HTML")
        
        # Сохраняем контекст для оценки
        await state.update_data(
            last_ai_question=question,
            last_ai_answer=answer,
            question_hash=question_hash
        )
        
        logger.info(
            f"Расширенный ответ: user_id={db_user.id}, "
            f"category={category}, time={response_time:.2f}s"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении расширенного ответа: {e}", exc_info=True)
        await processing_msg.delete()
        await callback.message.answer(
            "❌ Произошла ошибка при обработке вашего запроса.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )


@router.callback_query(F.data.startswith("rate_helpful:"))
async def process_rate_helpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик положительной оценки ответа из FAQ
    
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
                action="faq_rated_helpful",
                details={
                    "user_question": question,
                    "faq_question": faq_context['question'],
                    "similarity_score": faq_context.get('similarity_score', 0),
                    "rating": "helpful"
                }
            )
        
        logger.info(
            f"FAQ ответ оценён положительно: user_id={db_user.id}, "
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
                        text="🤖 Получить расширенный ответ от AI",
                        callback_data=f"expand_answer:{db_user.id}:{question_hash}"
                    )]
                ])
                await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")


@router.callback_query(F.data.startswith("rate_unhelpful:"))
async def process_rate_unhelpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик отрицательной оценки ответа из FAQ
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("📝 Спасибо за обратную связь! Попробую найти более подходящий ответ.")
    
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
                action="faq_rated_unhelpful",
                details={
                    "user_question": question,
                    "faq_question": faq_context['question'],
                    "similarity_score": faq_context.get('similarity_score', 0),
                    "rating": "unhelpful"
                }
            )
        
        logger.warning(
            f"FAQ ответ оценён отрицательно: user_id={db_user.id}, "
            f"similarity={faq_context.get('similarity_score', 0):.2%}, "
            f"user_q='{question}', faq_q='{faq_context['question'][:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")
        
        # Автоматически вызываем AI для более точного ответа
        await callback.message.answer("🤖 Обращаюсь к AI для более точного ответа...")
        
        try:
            # Загрузка конфигурации
            config = load_config()
            
            # Создание AI клиента
            ai_client = AIClientFactory.create_client(config)
            
            # Получение истории сообщений
            async with get_session() as session:
                history = await get_user_messages(session, db_user.id, limit=config.app.max_history_length)
            
            # Формирование сообщений для AI
            messages = [
                {"role": "system", "content": get_system_prompt(db_user.role.value)}
            ]
            
            # Добавляем историю
            for hist_msg in history:
                messages.append({
                    "role": hist_msg.role,
                    "content": hist_msg.content
                })
            
            # Добавляем текущий вопрос (используем анонимизированную версию)
            messages.append({
                "role": "user",
                "content": question_for_ai
            })
            
            # Засекаем время
            start_time = time.time()
            
            # Отправка запроса к AI
            response = await ai_client.chat_completion(messages)
            
            # Время ответа
            response_time = time.time() - start_time
            
            answer = response["content"]
            
            # Сохранение в БД
            async with get_session() as session:
                # Сохраняем сообщения в историю
                await create_message(session, db_user.id, "user", question)
                await create_message(session, db_user.id, "assistant", answer)
                
                # Увеличиваем счетчик запросов
                await increment_user_requests(session, db_user.id)
                
                # Категоризация вопроса
                category = None
                try:
                    cat_response = await ai_client.chat_completion(
                        [{"role": "user", "content": CATEGORIZATION_PROMPT.format(question=question)}],
                        max_tokens=10
                    )
                    category = cat_response["content"].strip().lower()
                except Exception as e:
                    logger.warning(f"Не удалось категоризировать вопрос: {e}")
                
                # Сохраняем запрос в статистику
                await create_query(
                    session,
                    user_id=db_user.id,
                    question=question,
                    answer=answer,
                    ai_provider=AIProvider(config.app.ai_provider),
                    ai_model=response["model"],
                    response_time=response_time,
                    tokens_used=response.get("tokens_used"),
                    category=category
                )
                
                # Логируем в аудит
                await create_audit_log(
                    session,
                    user_id=db_user.id,
                    action="ai_after_negative_rating",
                    details={
                        "question": question,
                        "model": response["model"],
                        "category": category,
                        "response_time": response_time,
                        "tokens": response.get("tokens_used")
                    }
                )
            
            # Отправляем ответ
            max_length = 4000
            
            if len(answer) <= max_length:
                await callback.message.answer(answer, parse_mode="Markdown")
            else:
                # Разбиваем на части
                parts = [answer[i:i+max_length] for i in range(0, len(answer), max_length)]
                for part in parts:
                    await callback.message.answer(part, parse_mode="Markdown")
            
            logger.info(
                f"AI ответ после отрицательной оценки: user_id={db_user.id}, "
                f"category={category}, time={response_time:.2f}s"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении AI ответа после отрицательной оценки: {e}", exc_info=True)
            await callback.message.answer(
                "❌ Произошла ошибка при обращении к AI.\n"
                "Пожалуйста, попробуйте задать вопрос заново."
            )


@router.callback_query(F.data.startswith("rate_ai_helpful:"))
async def process_rate_ai_helpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик положительной оценки AI ответа
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("👍 Спасибо за обратную связь!")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_ai_question')
    answer = data.get('last_ai_answer')
    
    if question and answer:
        # Логируем положительную оценку
        async with get_session() as session:
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="ai_rated_helpful",
                details={
                    "question": question[:100],  # Первые 100 символов
                    "answer_length": len(answer),
                    "rating": "helpful"
                }
            )
        
        logger.info(
            f"AI ответ оценён положительно: user_id={db_user.id}, "
            f"question='{question[:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")


@router.callback_query(F.data.startswith("rate_ai_unhelpful:"))
async def process_rate_ai_unhelpful(callback: CallbackQuery, state: FSMContext, db_user: User):
    """
    Обработчик отрицательной оценки AI ответа
    
    Args:
        callback: Callback запрос
        state: FSM состояние
        db_user: Пользователь из БД
    """
    await callback.answer("📝 Спасибо за обратную связь!")
    
    # Получаем сохранённый контекст
    data = await state.get_data()
    question = data.get('last_ai_question')
    answer = data.get('last_ai_answer')
    
    if question and answer:
        # Логируем отрицательную оценку
        async with get_session() as session:
            await create_audit_log(
                session,
                user_id=db_user.id,
                action="ai_rated_unhelpful",
                details={
                    "question": question[:100],  # Первые 100 символов
                    "answer_length": len(answer),
                    "rating": "unhelpful"
                }
            )
        
        logger.warning(
            f"AI ответ оценён отрицательно: user_id={db_user.id}, "
            f"question='{question[:50]}...'"
        )
        
        # Обновляем сообщение, убирая кнопки
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception as e:
            logger.warning(f"Не удалось обновить клавиатуру после оценки: {e}")
        
        # Информируем пользователя
        await callback.message.answer(
            "Спасибо за обратную связь! Это поможет нам улучшить качество ответов.\n\n"
            "Вы можете:\n"
            "• Переформулировать вопрос для получения другого ответа\n"
            "• Обратиться к администратору через /help"
        )
    
    # Очищаем state
    await state.clear()

