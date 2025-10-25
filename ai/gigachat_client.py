"""
Клиент для работы с GigaChat API
"""
import asyncio
import aiohttp
import uuid
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from ai.base_client import BaseAIClient
from utils.config import GigaChatConfig
from utils.logger import setup_logger

logger = setup_logger()


class GigaChatClient(BaseAIClient):
    """
    Клиент для работы с GigaChat API через прямые HTTP запросы
    """
    
    def __init__(self, config: GigaChatConfig):
        """
        Инициализация клиента
        
        Args:
            config: Конфигурация GigaChat
        """
        self.config = config
        self.model = config.model
        self.base_url = "https://gigachat.devices.sberbank.ru/api/v1"
        self.token = None
        self.token_expires = None
        logger.info(f"GigaChat клиент инициализирован с моделью {self.model}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Получение заголовков для аутентификации"""
        # Парсим API ключ (ожидаем формат client_id:client_secret)
        if ':' in self.config.api_key:
            client_id, client_secret = self.config.api_key.split(':', 1)
        else:
            # Если формат неверный, используем как client_id
            client_id = self.config.api_key
            client_secret = ""
        
        auth_string = f"{client_id}:{client_secret}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()
        
        return {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {auth_b64}"
        }
    
    async def _get_access_token(self) -> str:
        """Получение токена доступа для GigaChat"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            logger.debug("Используем существующий токен GigaChat")
            return self.token
        
        logger.info("Обновление токена GigaChat...")
        
        headers = self._get_auth_headers()
        data = {"scope": self.config.scope}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
                    headers=headers,
                    data=data,
                    ssl=False
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        self.token = result["access_token"]
                        expires_at = result.get("expires_at", None)
                        
                        if expires_at:
                            # GigaChat возвращает время в миллисекундах
                            if expires_at > 10000000000:
                                expires_at = expires_at / 1000
                            self.token_expires = datetime.fromtimestamp(expires_at - 60)
                        else:
                            # Если нет expires_at, используем стандартное время
                            self.token_expires = datetime.now() + timedelta(seconds=1800)
                        
                        logger.info("Токен GigaChat успешно обновлен")
                        return self.token
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка получения токена: {response.status} - {error_text}")
                        raise Exception(f"Ошибка получения токена: {response.status}")
        except Exception as e:
            logger.error(f"Ошибка при получении токена GigaChat: {e}")
            raise
    
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Отправка запроса к GigaChat
        
        Args:
            messages: История сообщений
            temperature: Температура генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Dict: Ответ с метаданными
        """
        try:
            logger.debug(f"Отправка запроса к GigaChat: {len(messages)} сообщений")
            
            # Получаем токен доступа
            token = await self._get_access_token()
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Authorization": f"Bearer {token}"
            }
            
            # Формируем payload для GigaChat API
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens or 2048
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    ssl=False
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"Получен ответ от GigaChat, длина: {len(str(result))} символов")
                        
                        # Извлекаем содержимое ответа
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                        else:
                            content = str(result)
                        
                        return {
                            "content": content,
                            "model": result.get("model", self.model),
                            "tokens_used": result.get("usage", {}).get("total_tokens", 0),
                            "finish_reason": result.get("choices", [{}])[0].get("finish_reason", "stop")
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Ошибка GigaChat API: {response.status} - {error_text}")
                        raise Exception(f"Ошибка GigaChat API: {response.status}")
                        
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обращении к GigaChat: {e}")
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
        Проверить подключение к GigaChat
        
        Returns:
            bool: True если подключение успешно
        """
        try:
            logger.info("Проверка подключения к GigaChat...")
            
            # Получаем токен
            token = await self._get_access_token()
            if not token:
                logger.warning("GigaChat: токен не получен")
                return False
            
            # Тестируем реальное подключение
            test_messages = [{"role": "user", "content": "Тест"}]
            test_response = await self.chat_completion(test_messages, max_tokens=5)
            if test_response and "content" in test_response:
                logger.info("GigaChat: подключение успешно")
                return True
            else:
                logger.warning("GigaChat: нет ответа от API")
                return False
                
        except Exception as e:
            logger.error(f"GigaChat: ошибка подключения - {e}")
            return False

