"""
Gemini Live Provider для обработки текста
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional
from integrations.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

# Импорты Gemini Live API (с обработкой отсутствия)
try:
    import google.generativeai as genai
    from google.generativeai import types
    GEMINI_LIVE_AVAILABLE = True
except ImportError:
    genai = None
    types = None
    GEMINI_LIVE_AVAILABLE = False
    logger.warning("⚠️ Gemini Live API не найден - провайдер будет недоступен")

class GeminiLiveProvider(UniversalProviderInterface):
    """
    Провайдер обработки текста с использованием Gemini Live API
    
    Основной провайдер для генерации текста с поддержкой
    Google Search и других инструментов.
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
        
        self.model_name = config.get('model', 'gemini-2.0-flash-exp')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2048)
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 60)
        
        # System prompt для Gemini Live
        self.system_prompt = (
            "Your name is Nexy. You are a helpful AI assistant. "
            "Provide clear, concise, and accurate responses. "
            "If you don't know something, say so honestly. "
            "Keep responses focused and relevant to the user's question. "
            "You have access to Google Search for current information when needed."
        )
        
        self.model = None
        self.is_available = GEMINI_LIVE_AVAILABLE and bool(self.api_key)
        
        logger.info(f"Gemini Live Provider initialized: available={self.is_available}")
    
    async def initialize(self) -> bool:
        """
        Инициализация Gemini Live провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            if not self.is_available:
                logger.error("Gemini Live Provider not available - missing dependencies or API key")
                return False
            
            # Настраиваем API ключ
            genai.configure(api_key=self.api_key)
            
            # Создаем модель
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=genai.GenerationConfig(
                    temperature=self.temperature,
                    max_output_tokens=self.max_tokens,
                    candidate_count=1
                ),
                system_instruction=self.system_prompt
            )
            
            # Тестируем подключение
            test_response = await self._test_connection()
            
            if test_response:
                self.is_initialized = True
                logger.info(f"Gemini Live Provider initialized successfully with model: {self.model_name}")
                return True
            else:
                logger.error("Gemini Live Provider test generation failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Live Provider: {e}")
            return False
    
    async def process(self, input_data: str) -> AsyncGenerator[str, None]:
        """
        Обработка текстового запроса с использованием Gemini Live API
        
        Args:
            input_data: Текстовый запрос пользователя
            
        Yields:
            Части сгенерированного ответа
        """
        try:
            if not self.is_initialized or not self.model:
                raise Exception("Gemini Live Provider not initialized")
            
            # Создаем инструменты (включая Google Search)
            tools = [genai.protos.Tool(google_search_retrieval={})]
            
            # Генерируем ответ с инструментами
            response = await self._generate_with_tools(input_data, tools)
            
            if not response or not response.text:
                raise Exception("No response generated")
            
            # Разбиваем на предложения для streaming
            sentences = self._split_into_sentences(response.text)
            
            # Отправляем каждое предложение как отдельный chunk
            for sentence in sentences:
                if sentence.strip():
                    yield sentence.strip() + " "
            
            logger.debug(f"Gemini Live Provider generated {len(sentences)} sentences")
            
        except Exception as e:
            logger.error(f"Gemini Live Provider processing error: {e}")
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов Gemini Live провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            self.model = None
            self.is_initialized = False
            logger.info("Gemini Live Provider cleaned up")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up Gemini Live Provider: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """
        Тестирование подключения к Gemini Live API
        
        Returns:
            True если подключение работает, False иначе
        """
        try:
            if not self.model:
                return False
            
            # Простой тестовый запрос
            test_response = self.model.generate_content("Hello")
            return bool(test_response and test_response.text)
            
        except Exception as e:
            logger.warning(f"Gemini Live Provider connection test failed: {e}")
            return False
    
    async def _generate_with_tools(self, prompt: str, tools: list) -> Optional[Any]:
        """
        Генерация ответа с использованием инструментов
        
        Args:
            prompt: Текстовый запрос
            tools: Список инструментов
            
        Returns:
            Ответ от модели или None
        """
        try:
            if not self.model:
                return None
            
            # Создаем чат с инструментами
            chat = self.model.start_chat()
            
            # Отправляем сообщение с инструментами
            response = chat.send_message(
                prompt,
                tools=tools
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating with tools: {e}")
            return None
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья Gemini Live провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            if not self.is_available or not self.model:
                return False
            
            # Простая проверка - тестовый запрос
            test_response = await self._test_connection()
            return test_response
            
        except Exception as e:
            logger.warning(f"Gemini Live Provider health check failed: {e}")
            return False
    
    def _split_into_sentences(self, text: str) -> list:
        """
        Разбиение текста на предложения для streaming
        
        Args:
            text: Текст для разбиения
            
        Returns:
            Список предложений
        """
        if not text:
            return []
        
        # Простое разбиение по знакам препинания
        import re
        sentences = re.split(r'[.!?]+', text)
        
        # Фильтруем пустые предложения и добавляем знаки препинания
        result = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Добавляем точку если предложение не заканчивается знаком препинания
                if not re.search(r'[.!?]$', sentence):
                    sentence += '.'
                result.append(sentence)
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение расширенного статуса Gemini Live провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "gemini_live",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "is_available": self.is_available,
            "api_key_set": bool(self.api_key),
            "gemini_live_available": GEMINI_LIVE_AVAILABLE
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик Gemini Live провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "gemini_live",
            "model_name": self.model_name,
            "is_available": self.is_available,
            "api_key_set": bool(self.api_key)
        })
        
        return base_metrics
