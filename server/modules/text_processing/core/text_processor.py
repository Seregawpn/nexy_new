"""
Основной TextProcessor - координатор модуля обработки текста

Протестированная реализация с Live API (только стриминг):
- Этап 1: Стриминговая обработка текста (текст → поток текста)
- Этап 2: Стриминговая обработка с JPEG (текст + изображение → поток текста)  
- Этап 3: Google Search (текст + изображение + поиск → поток текста)
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator
from modules.text_processing.config import TextProcessingConfig
from modules.text_processing.providers.gemini_live_provider import GeminiLiveProvider

logger = logging.getLogger(__name__)

class TextProcessor:
    """
    Основной процессор текста с Live API (только стриминг)
    
    Координирует работу Live API провайдера и обеспечивает единый интерфейс
    для стриминговой обработки текстовых запросов с поддержкой изображений и поиска.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация процессора текста
        
        Args:
            config: Конфигурация модуля
        """
        self.config = TextProcessingConfig(config)
        
        # ТОЛЬКО Live API провайдер (без fallback)
        self.live_provider = GeminiLiveProvider(self.config.get_provider_config('gemini_live'))
        self.is_initialized = False
        
        logger.info("TextProcessor initialized with Live API")
    
    async def initialize(self) -> bool:
        """
        Инициализация Live API
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing TextProcessor with Live API...")
            
            if await self.live_provider.initialize():
                self.is_initialized = True
                logger.info("TextProcessor initialized with Live API")
                return True
            else:
                logger.error("Failed to initialize Live API")
                return False
                
        except Exception as e:
            logger.error(f"TextProcessor initialization error: {e}")
            return False
    
    
    async def process_text_streaming(self, text: str, image_data: bytes = None) -> AsyncGenerator[str, None]:
        """
        Стриминговая обработка текста с изображением через Live API
        
        Args:
            text: Текстовый запрос
            image_data: JPEG данные изображения (опционально)
            
        Yields:
            Части текстового ответа
        """
        try:
            if not self.is_initialized:
                raise Exception("TextProcessor not initialized")
            
            async for chunk in self.live_provider.process_with_image(text, image_data):
                yield chunk
                
        except Exception as e:
            logger.error(f"Text streaming with JPEG error: {e}")
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов процессора
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up TextProcessor...")
            
            # Очищаем Live API провайдер
            if self.live_provider:
                await self.live_provider.cleanup()
            
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
            "live_provider": self.live_provider.get_status() if self.live_provider else None
        }
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик процессора
        
        Returns:
            Словарь с метриками процессора
        """
        metrics = {
            "is_initialized": self.is_initialized,
            "live_provider": self.live_provider.get_metrics() if self.live_provider else None
        }
        
        return metrics
    
    def get_healthy_providers(self) -> list:
        """
        Получение списка здоровых провайдеров
        
        Returns:
            Список здоровых провайдеров (только Live API)
        """
        if self.live_provider and self.live_provider.is_initialized:
            return [self.live_provider]
        return []
    
    def get_failed_providers(self) -> list:
        """
        Получение списка failed провайдеров
        
        Returns:
            Список failed провайдеров
        """
        if self.live_provider and not self.live_provider.is_initialized:
            return [self.live_provider]
        return []
    
    def reset_metrics(self):
        """Сброс метрик процессора"""
        logger.info("TextProcessor metrics reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по процессору
        
        Returns:
            Словарь со сводкой
        """
        summary = {
            "is_initialized": self.is_initialized,
            "total_providers": 1,
            "healthy_providers": len(self.get_healthy_providers()),
            "failed_providers": len(self.get_failed_providers()),
            "config_valid": self.config.validate(),
            "live_api_available": self.live_provider.is_available if self.live_provider else False
        }
        
        return summary
    
    def __str__(self) -> str:
        """Строковое представление процессора"""
        return f"TextProcessor(initialized={self.is_initialized}, live_api={self.live_provider.is_initialized if self.live_provider else False})"
    
    def __repr__(self) -> str:
        """Представление процессора для отладки"""
        return (
            f"TextProcessor("
            f"initialized={self.is_initialized}, "
            f"live_api_initialized={self.live_provider.is_initialized if self.live_provider else False}, "
            f"live_api_available={self.live_provider.is_available if self.live_provider else False}"
            f")"
        )