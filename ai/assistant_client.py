"""
Клиент для работы с OpenAI Assistants API (нейроассистент)
"""
import asyncio
from typing import Optional, List, Dict
from openai import AsyncOpenAI, OpenAIError

from utils.config import OpenAIConfig
from utils.logger import setup_logger

logger = setup_logger()


class OpenAIAssistantClient:
    """
    Клиент для работы с OpenAI Assistants API
    """
    
    def __init__(self, config: OpenAIConfig):
        """
        Инициализация клиента
        
        Args:
            config: Конфигурация OpenAI
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key)
        self.assistant_id: Optional[str] = None
        logger.info("OpenAI Assistant клиент инициализирован")
    
    async def create_assistant(
        self,
        name: str = "OT Consultant Assistant",
        instructions: str = None,
        model: str = None,
        tools: List[Dict] = None,
        file_ids: List[str] = None
    ) -> str:
        """
        Создать нового ассистента
        
        Args:
            name: Имя ассистента
            instructions: Инструкции для ассистента
            model: Модель (по умолчанию из конфига)
            tools: Инструменты для ассистента
            file_ids: ID файлов для базы знаний
            
        Returns:
            str: ID созданного ассистента
        """
        try:
            if instructions is None:
                instructions = self._get_default_instructions()
            
            if model is None:
                model = self.config.model
            
            if tools is None:
                tools = [{"type": "file_search"}]  # Поиск по базе знаний
            
            logger.info(f"Создание ассистента: {name}")
            
            assistant = await self.client.beta.assistants.create(
                name=name,
                instructions=instructions,
                model=model,
                tools=tools
            )
            
            self.assistant_id = assistant.id
            logger.info(f"Ассистент создан: {assistant.id}")
            
            return assistant.id
            
        except OpenAIError as e:
            logger.error(f"Ошибка при создании ассистента: {e}")
            raise
    
    async def get_or_create_assistant(
        self,
        assistant_id: Optional[str] = None
    ) -> str:
        """
        Получить существующего ассистента или создать нового
        
        Args:
            assistant_id: ID существующего ассистента
            
        Returns:
            str: ID ассистента
        """
        if assistant_id:
            try:
                # Проверяем, существует ли ассистент
                assistant = await self.client.beta.assistants.retrieve(assistant_id)
                self.assistant_id = assistant.id
                logger.info(f"Использование существующего ассистента: {assistant.id}")
                return assistant.id
            except OpenAIError:
                logger.warning(f"Ассистент {assistant_id} не найден, создаем новый")
        
        # Создаем нового ассистента
        return await self.create_assistant()
    
    async def create_thread(self) -> str:
        """
        Создать новый thread (поток общения)
        
        Returns:
            str: ID созданного thread
        """
        try:
            thread = await self.client.beta.threads.create()
            logger.debug(f"Thread создан: {thread.id}")
            return thread.id
        except OpenAIError as e:
            logger.error(f"Ошибка при создании thread: {e}")
            raise
    
    async def add_message_to_thread(
        self,
        thread_id: str,
        content: str,
        role: str = "user"
    ) -> str:
        """
        Добавить сообщение в thread
        
        Args:
            thread_id: ID thread
            content: Содержимое сообщения
            role: Роль (user/assistant)
            
        Returns:
            str: ID сообщения
        """
        try:
            message = await self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role=role,
                content=content
            )
            logger.debug(f"Сообщение добавлено в thread {thread_id}")
            return message.id
        except OpenAIError as e:
            logger.error(f"Ошибка при добавлении сообщения: {e}")
            raise
    
    async def run_assistant(
        self,
        thread_id: str,
        assistant_id: Optional[str] = None
    ) -> Dict:
        """
        Запустить ассистента на thread и получить ответ
        
        Args:
            thread_id: ID thread
            assistant_id: ID ассистента (или используется self.assistant_id)
            
        Returns:
            Dict: Ответ с метаданными
        """
        try:
            assistant_id = assistant_id or self.assistant_id
            
            if not assistant_id:
                raise ValueError("Assistant ID не установлен")
            
            logger.debug(f"Запуск ассистента {assistant_id} на thread {thread_id}")
            
            # Создаем run
            run = await self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            
            # Ожидаем завершения run
            while run.status in ["queued", "in_progress"]:
                await asyncio.sleep(0.5)
                run = await self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )
            
            if run.status != "completed":
                logger.error(f"Run завершился с статусом: {run.status}")
                raise Exception(f"Run failed with status: {run.status}")
            
            # Получаем сообщения из thread
            messages = await self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=1
            )
            
            if not messages.data:
                raise Exception("Не получены сообщения от ассистента")
            
            # Извлекаем текст ответа
            last_message = messages.data[0]
            response_text = ""
            
            for content_block in last_message.content:
                if hasattr(content_block, 'text'):
                    response_text += content_block.text.value
            
            # Получаем метаданные
            result = {
                "content": response_text,
                "model": run.model,
                "assistant_id": assistant_id,
                "thread_id": thread_id,
                "run_id": run.id,
                "tokens_used": getattr(run.usage, 'total_tokens', 0) if run.usage else 0
            }
            
            logger.debug(f"Ответ получен от ассистента: {result['tokens_used']} токенов")
            return result
            
        except OpenAIError as e:
            logger.error(f"Ошибка при запуске ассистента: {e}")
            raise
    
    async def ask_assistant(
        self,
        question: str,
        thread_id: Optional[str] = None,
        assistant_id: Optional[str] = None
    ) -> Dict:
        """
        Задать вопрос ассистенту (высокоуровневый метод)
        
        Args:
            question: Вопрос пользователя
            thread_id: ID существующего thread (если None, создается новый)
            assistant_id: ID ассистента
            
        Returns:
            Dict: Ответ с метаданными
        """
        # Создаем или используем существующий thread
        if not thread_id:
            thread_id = await self.create_thread()
        
        # Добавляем вопрос в thread
        await self.add_message_to_thread(thread_id, question)
        
        # Запускаем ассистента и получаем ответ
        result = await self.run_assistant(thread_id, assistant_id)
        
        return result
    
    async def upload_file(
        self,
        file_path: str,
        purpose: str = "assistants"
    ) -> str:
        """
        Загрузить файл в OpenAI для использования ассистентом
        
        Args:
            file_path: Путь к файлу
            purpose: Цель использования файла
            
        Returns:
            str: ID загруженного файла
        """
        try:
            with open(file_path, "rb") as file:
                response = await self.client.files.create(
                    file=file,
                    purpose=purpose
                )
            
            logger.info(f"Файл загружен: {file_path} -> {response.id}")
            return response.id
            
        except Exception as e:
            logger.error(f"Ошибка при загрузке файла: {e}")
            raise
    
    async def attach_files_to_assistant(
        self,
        assistant_id: str,
        file_ids: List[str]
    ):
        """
        Прикрепить файлы к ассистенту
        
        Args:
            assistant_id: ID ассистента
            file_ids: Список ID файлов
        """
        try:
            await self.client.beta.assistants.update(
                assistant_id=assistant_id,
                tool_resources={
                    "file_search": {
                        "file_ids": file_ids
                    }
                }
            )
            logger.info(f"Файлы прикреплены к ассистенту {assistant_id}")
            
        except OpenAIError as e:
            logger.error(f"Ошибка при прикреплении файлов: {e}")
            raise
    
    async def delete_thread(self, thread_id: str):
        """
        Удалить thread
        
        Args:
            thread_id: ID thread
        """
        try:
            await self.client.beta.threads.delete(thread_id)
            logger.debug(f"Thread удален: {thread_id}")
        except OpenAIError as e:
            logger.warning(f"Ошибка при удалении thread: {e}")
    
    def _get_default_instructions(self) -> str:
        """
        Получить инструкции по умолчанию для ассистента
        
        Returns:
            str: Инструкции
        """
        from ai.prompts import SYSTEM_PROMPT_OT_DOU
        return SYSTEM_PROMPT_OT_DOU
    
    async def get_assistant_info(self, assistant_id: Optional[str] = None) -> Dict:
        """
        Получить информацию об ассистенте
        
        Args:
            assistant_id: ID ассистента
            
        Returns:
            Dict: Информация об ассистенте
        """
        try:
            assistant_id = assistant_id or self.assistant_id
            if not assistant_id:
                raise ValueError("Assistant ID не установлен")
            
            assistant = await self.client.beta.assistants.retrieve(assistant_id)
            
            return {
                "id": assistant.id,
                "name": assistant.name,
                "model": assistant.model,
                "instructions": assistant.instructions,
                "tools": [tool.type for tool in assistant.tools] if assistant.tools else []
            }
            
        except OpenAIError as e:
            logger.error(f"Ошибка при получении информации об ассистенте: {e}")
            raise

