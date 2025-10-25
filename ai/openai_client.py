"""
Клиент для работы с OpenAI API
"""
import asyncio
from typing import List, Dict, Optional
from openai import AsyncOpenAI, OpenAIError

from ai.base_client import BaseAIClient
from utils.config import OpenAIConfig
from utils.logger import setup_logger

logger = setup_logger()


class OpenAIClient(BaseAIClient):
    """
    Клиент для работы с OpenAI API
    """
    
    def __init__(self, config: OpenAIConfig):
        """
        Инициализация клиента
        
        Args:
            config: Конфигурация OpenAI
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key)
        self.model = config.model
        logger.info(f"OpenAI клиент инициализирован с моделью {self.model}")
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Отправка запроса к OpenAI
        
        Args:
            messages: История сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Dict: Ответ с метаданными
        """
        try:
            temperature = temperature if temperature is not None else self.config.temperature
            max_tokens = max_tokens or self.config.max_tokens
            
            logger.debug(f"Отправка запроса к OpenAI: {len(messages)} сообщений")
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = {
                "content": response.choices[0].message.content,
                "model": response.model,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "finish_reason": response.choices[0].finish_reason
            }
            
            logger.debug(f"Получен ответ от OpenAI: {result['tokens_used']} токенов")
            return result
            
        except OpenAIError as e:
            logger.error(f"Ошибка OpenAI API: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обращении к OpenAI: {e}")
            raise
    
    async def get_model_name(self) -> str:
        """
        Получить название модели
        
        Returns:
            str: Название модели
        """
        return self.model
    
    async def check_connection(self) -> bool:
        """
        Проверить подключение к OpenAI
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            # Отправляем тестовый запрос
            test_messages = [{"role": "user", "content": "test"}]
            await asyncio.wait_for(
                self.chat_completion(test_messages, max_tokens=5),
                timeout=10.0
            )
            logger.info("Подключение к OpenAI успешно")
            return True
        except Exception as e:
            logger.error(f"Не удалось подключиться к OpenAI: {e}")
            return False

