"""
Базовый класс для AI клиентов
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional


class BaseAIClient(ABC):
    """
    Абстрактный базовый класс для AI провайдеров
    """
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Отправка запроса к AI модели
        
        Args:
            messages: История сообщений в формате [{"role": "user", "content": "..."}]
            temperature: Температура генерации (0-1)
            max_tokens: Максимальное количество токенов в ответе
            
        Returns:
            Dict: Ответ модели с метаданными
        """
        pass
    
    @abstractmethod
    async def get_model_name(self) -> str:
        """
        Получить название используемой модели
        
        Returns:
            str: Название модели
        """
        pass
    
    @abstractmethod
    async def check_connection(self) -> bool:
        """
        Проверить подключение к AI провайдеру
        
        Returns:
            bool: True если подключение успешно
        """
        pass

