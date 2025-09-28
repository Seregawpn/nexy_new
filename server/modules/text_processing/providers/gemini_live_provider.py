"""
Gemini Live Provider для обработки текста с поддержкой изображений и Google Search

Протестированная реализация с поэтапным подходом:
- Этап 1: Базовый Live API (текст → текст)
- Этап 2: JPEG поддержка (текст + изображение → текст)  
- Этап 3: Google Search (текст + изображение + поиск → текст)
"""

import asyncio
import logging
import base64
from typing import AsyncGenerator, Dict, Any, Optional
from integrations.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

# Импорты Gemini Live API (с обработкой отсутствия)
try:
    from google import genai
    from google.genai import types
    GEMINI_LIVE_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GEMINI_LIVE_AVAILABLE = False
    logger.warning("⚠️ Gemini Live API не найден - провайдер будет недоступен")

class GeminiLiveProvider(UniversalProviderInterface):
    """
    Провайдер обработки текста с использованием Gemini Live API
    
    Поддерживает:
    - Базовую обработку текста
    - JPEG изображения
    - Google Search
    - Стриминг ответов
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Gemini Live провайдера
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__(
            name="gemini_live",
            priority=1,  # Основной провайдер
            config=config
        )
        
        self.model_name = config.get('model', 'gemini-live-2.5-flash-preview')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2048)
        self.media_resolution = config.get('media_resolution', 'MEDIA_RESOLUTION_HIGH')
        self.tools = config.get('tools', [])
        self.system_prompt = config.get('system_prompt', '')
        self.api_key = config.get('api_key', '')
        
        # JPEG настройки
        self.image_mime_type = config.get('image_mime_type', 'image/jpeg')
        self.image_max_size = config.get('image_max_size', 10 * 1024 * 1024)
        self.streaming_chunk_size = config.get('streaming_chunk_size', 8192)
        
        # Клиент
        self.client = None
        self.is_available = GEMINI_LIVE_AVAILABLE and bool(self.api_key)
        self.is_initialized = False
        
        logger.info(f"GeminiLiveProvider initialized: available={self.is_available}")
    
    async def initialize(self) -> bool:
        """
        Инициализация Live API
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info(f"🔍 ДИАГНОСТИКА GeminiLiveProvider.initialize():")
            logger.info(f"   → is_available: {self.is_available}")
            logger.info(f"   → api_key present: {bool(self.api_key)}")
            logger.info(f"   → model_name: {self.model_name}")
            
            if not self.is_available:
                logger.error("Missing API key or dependencies")
                return False
            
            # Создаем клиент
            logger.info(f"🔍 Создаем Gemini клиент...")
            self.client = genai.Client(api_key=self.api_key)
            logger.info(f"✅ Gemini клиент создан")
            
            # Базовая конфигурация
            config = {
                "response_modalities": ["TEXT"]
            }
            # Добавляем system_instruction если задан
            if self.system_prompt:
                logger.info(f"🔍 System prompt: '{self.system_prompt[:100]}...'")
                try:
                    # Если доступен types.Content, используем его, иначе строку
                    if types and hasattr(types, 'Content') and hasattr(types, 'Part'):
                        config["system_instruction"] = types.Content(
                            parts=[types.Part.from_text(text=self.system_prompt)],
                            role="user"
                        )
                        logger.info(f"✅ System instruction добавлен с role='user'")
                    else:
                        config["system_instruction"] = self.system_prompt
                        logger.info(f"✅ System instruction добавлен как строка")
                except Exception:
                    config["system_instruction"] = self.system_prompt
            
            # Добавляем инструменты если есть (Google Search для этапа 3)
            if self.tools and "google_search" in self.tools:
                config["tools"] = [{"google_search": {}}]
            
            # НЕ добавляем media_resolution - модель не поддерживает
            
            # Тестируем подключение
            logger.info(f"🔍 Тестируем подключение к Gemini Live API...")
            async with self.client.aio.live.connect(model=self.model_name, config=config) as test_session:
                logger.info(f"✅ Подключение к Gemini Live API установлено")
                
                logger.info(f"🔍 Отправляем тестовое сообщение...")
                await test_session.send_client_content(
                    turns={"role": "user", "parts": [{"text": "Hello"}]}, 
                    turn_complete=True
                )
                logger.info(f"✅ Тестовое сообщение отправлено")
                
                logger.info(f"🔍 Ожидаем ответ от Gemini...")
                async for response in test_session.receive():
                    logger.info(f"🔍 Получен ответ: {type(response)}")
                    if response.text:
                        self.is_initialized = True
                        logger.info(f"✅ Live API initialized: {self.model_name}")
                        return True
            
            logger.error(f"❌ Тестовое подключение не получило ответ")
            return False
            
        except Exception as e:
            logger.error(f"Live API initialization failed: {e}")
            return False
    
    async def process(self, input_data: str) -> AsyncGenerator[str, None]:
        """
        ЭТАП 1: Обработка текста через Live API
        
        Args:
            input_data: Текстовый запрос
            
        Yields:
            Части текстового ответа
        """
        try:
            if not self.is_initialized or not self.client:
                raise Exception("Live API not initialized")
            
            # Конфигурация
            config = {
                "response_modalities": ["TEXT"]
            }
            if self.system_prompt:
                try:
                    if types and hasattr(types, 'Content') and hasattr(types, 'Part'):
                        config["system_instruction"] = types.Content(
                            parts=[types.Part.from_text(text=self.system_prompt)],
                            role="user"
                        )
                    else:
                        config["system_instruction"] = self.system_prompt
                except Exception:
                    config["system_instruction"] = self.system_prompt
            
            # Добавляем инструменты если есть (Google Search для этапа 3)
            if self.tools and "google_search" in self.tools:
                config["tools"] = [{"google_search": {}}]
            
            async with self.client.aio.live.connect(model=self.model_name, config=config) as session:
                # Отправляем текст
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": input_data}]}, 
                    turn_complete=True
                )
                
                # Получаем ответ
                async for response in session.receive():
                    if response.text:
                        # НЕ разбиваем на предложения здесь - это делает StreamingWorkflowIntegration
                        yield response.text
                    
                    # Обрабатываем инструменты (Google Search) - проверяем наличие атрибута
                    if hasattr(response, 'tool_calls') and response.tool_calls:
                        for tool_call in response.tool_calls:
                            if hasattr(tool_call, 'google_search') and tool_call.google_search:
                                logger.info("Google Search executed")
                    
                    if response.server_content and response.server_content.turn_complete:
                        break
                
                logger.debug("Live API text processing completed")
                
        except Exception as e:
            logger.error(f"Live API text processing error: {e}")
            raise e
    
    async def process_with_image(self, input_data: str, image_data: bytes) -> AsyncGenerator[str, None]:
        """
        ЭТАП 2: Обработка текста с JPEG изображением
        
        Args:
            input_data: Текстовый запрос
            image_data: JPEG данные изображения
            
        Yields:
            Части текстового ответа
        """
        try:
            if not self.is_initialized or not self.client:
                raise Exception("Live API not initialized")
            
            # Конфигурация (без media_resolution)
            config = {
                "response_modalities": ["TEXT"]
            }
            if self.system_prompt:
                try:
                    if types and hasattr(types, 'Content') and hasattr(types, 'Part'):
                        config["system_instruction"] = types.Content(
                            parts=[types.Part.from_text(text=self.system_prompt)],
                            role="user"
                        )
                    else:
                        config["system_instruction"] = self.system_prompt
                except Exception:
                    config["system_instruction"] = self.system_prompt
            
            # НЕ добавляем media_resolution - модель не поддерживает
            
            # Добавляем инструменты если есть (Google Search для этапа 3)
            if self.tools and "google_search" in self.tools:
                config["tools"] = [{"google_search": {}}]
            
            async with self.client.aio.live.connect(model=self.model_name, config=config) as session:
                # Отправляем текст
                await session.send_client_content(
                    turns={"role": "user", "parts": [{"text": input_data}]}, 
                    turn_complete=False
                )
                
                # Отправляем JPEG изображение
                await self._send_jpeg_image(session, image_data)
                
                # Завершаем ввод
                await session.send_client_content(turn_complete=True)
                
                # Получаем ответ
                async for response in session.receive():
                    if response.text:
                        # НЕ разбиваем на предложения здесь - это делает StreamingWorkflowIntegration
                        yield response.text
                    
                    # Обрабатываем инструменты (Google Search) - проверяем наличие атрибута
                    if hasattr(response, 'tool_calls') and response.tool_calls:
                        for tool_call in response.tool_calls:
                            if hasattr(tool_call, 'google_search') and tool_call.google_search:
                                logger.info("Google Search executed with image")
                    
                    if response.server_content and response.server_content.turn_complete:
                        break
                
                logger.debug("Live API with image processing completed")
                
        except Exception as e:
            logger.error(f"Live API with image processing error: {e}")
            raise e
    
    async def _send_jpeg_image(self, session, image_data: bytes) -> None:
        """
        Отправка JPEG изображения через Live API
        
        Args:
            session: Live API сессия
            image_data: JPEG данные изображения
        """
        try:
            # Проверяем, что image_data не None
            if image_data is None:
                logger.debug("No image data provided, skipping image processing")
                return
            
            # Проверяем JPEG формат
            if not image_data.startswith(b'\xff\xd8\xff'):
                raise ValueError("Image must be in JPEG format")
            
            # Проверяем размер
            if len(image_data) > self.image_max_size:
                raise ValueError(f"Image too large: {len(image_data)} bytes")
            
            # КРИТИЧНО: Используем send_client_content, НЕ send_realtime_input
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            await session.send_client_content(
                turns={
                    "role": "user", 
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": self.image_mime_type,
                                "data": image_b64
                            }
                        }
                    ]
                }, 
                turn_complete=False
            )
            
            logger.debug("JPEG image sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending JPEG image: {e}")
            raise e
    
    def _split_into_sentences(self, text: str) -> list:
        """
        Разбиение текста на предложения для стриминга
        
        Args:
            text: Текст для разбиения
            
        Returns:
            Список предложений
        """
        if not text:
            return []
        
        import re
        sentences = re.split(r'[.!?]+', text)
        
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                if not re.search(r'[.!?]$', sentence):
                    sentence += '.'
                result.append(sentence)
        
        return result
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            self.client = None
            self.is_initialized = False
            logger.info("Live API cleaned up")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Live API: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса провайдера
        
        Returns:
            Словарь со статусом
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "gemini_live",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "tools": self.tools,
            "media_resolution": self.media_resolution,
            "is_available": self.is_available,
            "api_key_set": bool(self.api_key),
            "gemini_live_available": GEMINI_LIVE_AVAILABLE
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "gemini_live",
            "model_name": self.model_name,
            "is_available": self.is_available,
            "api_key_set": bool(self.api_key),
            "tools_enabled": len(self.tools) > 0
        })
        
        return base_metrics