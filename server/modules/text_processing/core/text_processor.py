"""
Основной TextProcessor - координатор модуля обработки текста
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator
from modules.text_processing.config import TextProcessingConfig
from modules.text_processing.fallback_manager import TextProcessingFallbackManager
from modules.text_processing.providers.gemini_live_provider import GeminiLiveProvider
from modules.text_processing.providers.langchain_provider import LangChainProvider

logger = logging.getLogger(__name__)

class TextProcessor:
    """
    Основной процессор текста
    
    Координирует работу всех провайдеров текста через
    FallbackManager и обеспечивает единый интерфейс
    для обработки текстовых запросов.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация процессора текста
        
        Args:
            config: Конфигурация модуля
        """
        self.config = TextProcessingConfig(config)
        self.fallback_manager = TextProcessingFallbackManager(config)
        self.is_initialized = False
        
        # Провайдеры
        self.providers = []
        
        logger.info("TextProcessor initialized")
    
    async def initialize(self) -> bool:
        """
        Инициализация процессора текста
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing TextProcessor...")
            
            # Валидируем конфигурацию
            if not self.config.validate():
                logger.error("Text processing configuration validation failed")
                return False
            
            # Создаем провайдеры
            await self._create_providers()
            
            # Регистрируем провайдеры в fallback менеджере
            self.fallback_manager.register_providers(self.providers)
            
            # Инициализируем провайдеры
            await self._initialize_providers()
            
            self.is_initialized = True
            logger.info(f"TextProcessor initialized successfully with {len(self.providers)} providers")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize TextProcessor: {e}")
            return False
    
    async def _create_providers(self):
        """Создание провайдеров текста"""
        try:
            # Gemini Live Provider (основной)
            gemini_config = self.config.get_provider_config('gemini_live')
            gemini_provider = GeminiLiveProvider(gemini_config)
            self.providers.append(gemini_provider)
            
            # LangChain Provider (fallback)
            langchain_config = self.config.get_provider_config('langchain')
            langchain_provider = LangChainProvider(langchain_config)
            self.providers.append(langchain_provider)
            
            logger.info(f"Created {len(self.providers)} text processing providers")
            
        except Exception as e:
            logger.error(f"Error creating providers: {e}")
            raise e
    
    async def _initialize_providers(self):
        """Инициализация всех провайдеров"""
        initialized_count = 0
        
        for provider in self.providers:
            try:
                if await provider.initialize():
                    initialized_count += 1
                    logger.info(f"Provider {provider.name} initialized successfully")
                else:
                    logger.warning(f"Provider {provider.name} initialization failed")
            except Exception as e:
                logger.error(f"Error initializing provider {provider.name}: {e}")
        
        if initialized_count == 0:
            raise Exception("No providers could be initialized")
        
        logger.info(f"Initialized {initialized_count}/{len(self.providers)} providers")
    
    async def process_text(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Обработка текстового запроса
        
        Args:
            prompt: Текстовый запрос пользователя
            
        Yields:
            Части сгенерированного ответа
        """
        try:
            if not self.is_initialized:
                raise Exception("TextProcessor not initialized")
            
            logger.debug(f"Processing text: {prompt[:100]}...")
            
            async for result in self.fallback_manager.process_text(prompt):
                yield result
                
        except Exception as e:
            logger.error(f"Error processing text: {e}")
            yield f"Error: Text processing failed - {str(e)}"
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов процессора
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up TextProcessor...")
            
            # Очищаем провайдеры
            for provider in self.providers:
                try:
                    await provider.cleanup()
                except Exception as e:
                    logger.warning(f"Error cleaning up provider {provider.name}: {e}")
            
            self.is_initialized = False
            logger.info("TextProcessor cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up TextProcessor: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса процессора
        
        Returns:
            Словарь со статусом процессора
        """
        status = {
            "is_initialized": self.is_initialized,
            "config_status": self.config.get_status(),
            "fallback_manager": self.fallback_manager.get_status(),
            "providers": []
        }
        
        # Добавляем статус каждого провайдера
        for provider in self.providers:
            provider_status = provider.get_status()
            status["providers"].append(provider_status)
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик процессора
        
        Returns:
            Словарь с метриками процессора
        """
        metrics = {
            "is_initialized": self.is_initialized,
            "fallback_manager": self.fallback_manager.get_metrics(),
            "providers": []
        }
        
        # Добавляем метрики каждого провайдера
        for provider in self.providers:
            provider_metrics = provider.get_metrics()
            metrics["providers"].append(provider_metrics)
        
        return metrics
    
    def get_healthy_providers(self) -> list:
        """
        Получение списка здоровых провайдеров
        
        Returns:
            Список здоровых провайдеров
        """
        return self.fallback_manager.get_healthy_providers()
    
    def get_failed_providers(self) -> list:
        """
        Получение списка failed провайдеров
        
        Returns:
            Список failed провайдеров
        """
        return self.fallback_manager.get_failed_providers()
    
    def reset_metrics(self):
        """Сброс метрик процессора"""
        self.fallback_manager.reset_metrics()
        logger.info("TextProcessor metrics reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по процессору
        
        Returns:
            Словарь со сводкой
        """
        summary = {
            "is_initialized": self.is_initialized,
            "total_providers": len(self.providers),
            "healthy_providers": len(self.get_healthy_providers()),
            "failed_providers": len(self.get_failed_providers()),
            "config_valid": self.config.validate(),
            "fallback_summary": self.fallback_manager.get_summary()
        }
        
        return summary
    
    def __str__(self) -> str:
        """Строковое представление процессора"""
        return f"TextProcessor(initialized={self.is_initialized}, providers={len(self.providers)})"
    
    def __repr__(self) -> str:
        """Представление процессора для отладки"""
        return (
            f"TextProcessor("
            f"initialized={self.is_initialized}, "
            f"providers={len(self.providers)}, "
            f"healthy={len(self.get_healthy_providers())}, "
            f"failed={len(self.get_failed_providers())}"
            f")"
        )
