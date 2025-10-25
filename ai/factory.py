"""
Фабрика для создания AI клиентов
"""
from typing import Optional
from ai.base_client import BaseAIClient
from ai.openai_client import OpenAIClient
from ai.gigachat_client import GigaChatClient
from utils.config import Config
from utils.logger import setup_logger

logger = setup_logger()


class AIClientFactory:
    """
    Фабрика для создания AI клиентов
    """
    
    @staticmethod
    def create_client(config: Config, provider: Optional[str] = None) -> BaseAIClient:
        """
        Создать AI клиента на основе конфигурации
        
        Args:
            config: Конфигурация приложения
            provider: Имя провайдера (openai, gigachat). Если None, берется из config
            
        Returns:
            BaseAIClient: Инстанс AI клиента
            
        Raises:
            ValueError: Если провайдер не поддерживается
        """
        provider = provider or config.app.ai_provider
        
        if provider == "openai":
            logger.info("Создание OpenAI клиента")
            return OpenAIClient(config.openai)
        elif provider == "gigachat":
            logger.info("Создание GigaChat клиента")
            return GigaChatClient(config.gigachat)
        else:
            raise ValueError(f"Неподдерживаемый AI провайдер: {provider}")
    
    @staticmethod
    def get_available_providers() -> list[str]:
        """
        Получить список доступных провайдеров
        
        Returns:
            list: Список провайдеров
        """
        return ["openai", "gigachat"]

