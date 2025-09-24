"""
LangChain Provider для обработки текста
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional
from integration.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

# Импорты LangChain (с обработкой отсутствия)
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    ChatGoogleGenerativeAI = None
    HumanMessage = None
    SystemMessage = None
    LANGCHAIN_AVAILABLE = False
    logger.warning("⚠️ LangChain не найден - провайдер будет недоступен")

class LangChainProvider(UniversalProviderInterface):
    """
    Провайдер обработки текста с использованием LangChain + Gemini
    
    Fallback провайдер для случаев, когда Gemini Live API недоступен.
    Использует LangChain для интеграции с Google Gemini API.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация LangChain провайдера
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__(
            name="langchain",
            priority=2,  # Fallback провайдер
            config=config
        )
        
        self.model_name = config.get('model', 'gemini-pro')
        self.temperature = config.get('temperature', 0.7)
        self.api_key = config.get('api_key', '')
        self.timeout = config.get('timeout', 60)
        
        # System prompt для LangChain
        self.system_prompt = (
            "Your name is Nexy. You are a helpful AI assistant. "
            "Provide clear, concise, and accurate responses. "
            "If you don't know something, say so honestly. "
            "Keep responses focused and relevant to the user's question."
        )
        
        self.llm = None
        self.is_available = LANGCHAIN_AVAILABLE and bool(self.api_key)
        
        logger.info(f"LangChain Provider initialized: available={self.is_available}")
    
    async def initialize(self) -> bool:
        """
        Инициализация LangChain провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            if not self.is_available:
                logger.error("LangChain Provider not available - missing dependencies or API key")
                return False
            
            # Создаем LLM экземпляр
            self.llm = ChatGoogleGenerativeAI(
                model=self.model_name,
                google_api_key=self.api_key,
                temperature=self.temperature,
                max_output_tokens=2048,
                timeout=self.timeout
            )
            
            # Тестируем подключение
            test_message = HumanMessage(content="Hello")
            response = await self.llm.agenerate([[test_message]])
            
            if response.generations and response.generations[0]:
                self.is_initialized = True
                logger.info(f"LangChain Provider initialized successfully with model: {self.model_name}")
                return True
            else:
                logger.error("LangChain Provider test generation failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize LangChain Provider: {e}")
            return False
    
    async def process(self, input_data: str) -> AsyncGenerator[str, None]:
        """
        Обработка текстового запроса с использованием LangChain
        
        Args:
            input_data: Текстовый запрос пользователя
            
        Yields:
            Части сгенерированного ответа
        """
        try:
            if not self.is_initialized or not self.llm:
                raise Exception("LangChain Provider not initialized")
            
            # Создаем сообщения
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=input_data)
            ]
            
            # Генерируем ответ
            response = await self.llm.agenerate([messages])
            
            if not response.generations or not response.generations[0]:
                raise Exception("No response generated")
            
            # Получаем текст ответа
            full_text = response.generations[0][0].text
            
            if not full_text:
                raise Exception("Empty response generated")
            
            # Разбиваем на предложения для streaming
            sentences = self._split_into_sentences(full_text)
            
            # Отправляем каждое предложение как отдельный chunk
            for sentence in sentences:
                if sentence.strip():
                    yield sentence.strip() + " "
            
            logger.debug(f"LangChain Provider generated {len(sentences)} sentences")
            
        except Exception as e:
            logger.error(f"LangChain Provider processing error: {e}")
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов LangChain провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            self.llm = None
            self.is_initialized = False
            logger.info("LangChain Provider cleaned up")
            return True
        except Exception as e:
            logger.error(f"Error cleaning up LangChain Provider: {e}")
            return False
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья LangChain провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            if not self.is_available or not self.llm:
                return False
            
            # Простая проверка - тестовый запрос
            test_message = HumanMessage(content="Health check")
            response = await self.llm.agenerate([[test_message]])
            
            return bool(response.generations and response.generations[0])
            
        except Exception as e:
            logger.warning(f"LangChain Provider health check failed: {e}")
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
        Получение расширенного статуса LangChain провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "langchain",
            "model_name": self.model_name,
            "temperature": self.temperature,
            "is_available": self.is_available,
            "api_key_set": bool(self.api_key),
            "langchain_available": LANGCHAIN_AVAILABLE
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик LangChain провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "langchain",
            "model_name": self.model_name,
            "is_available": self.is_available,
            "api_key_set": bool(self.api_key)
        })
        
        return base_metrics
