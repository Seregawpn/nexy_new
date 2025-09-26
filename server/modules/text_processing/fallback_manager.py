"""
Fallback Manager для модуля Text Processing
"""

import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from integrations.core.universal_fallback_manager import UniversalFallbackManager
from integrations.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

class TextProcessingFallbackManager:
    """
    Менеджер fallback для модуля обработки текста
    
    Использует UniversalFallbackManager для управления
    переключением между провайдерами текста.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация менеджера fallback
        
        Args:
            config: Конфигурация модуля
        """
        self.config = config or {}
        
        # Создаем универсальный менеджер fallback
        fallback_config = {
            'circuit_breaker_threshold': self.config.get('circuit_breaker_threshold', 3),
            'circuit_breaker_timeout': self.config.get('circuit_breaker_timeout', 300),
            'timeout': self.config.get('fallback_timeout', 30)
        }
        
        self.fallback_manager = UniversalFallbackManager(
            module_name="text_processing",
            config=fallback_config
        )
        
        self.providers: List[UniversalProviderInterface] = []
        
        logger.info("TextProcessingFallbackManager initialized")
    
    def register_providers(self, providers: List[UniversalProviderInterface]):
        """
        Регистрация провайдеров текста
        
        Args:
            providers: Список провайдеров текста
        """
        self.providers = providers
        self.fallback_manager.register_providers(providers)
        
        logger.info(f"Registered {len(providers)} text processing providers")
        for provider in providers:
            logger.debug(f"  - {provider.name} (priority: {provider.priority})")
    
    async def process_text(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Обработка текста с fallback логикой
        
        Args:
            prompt: Текстовый запрос пользователя
            
        Yields:
            Части сгенерированного ответа
        """
        try:
            logger.debug(f"Processing text with {len(self.providers)} providers")
            
            async for result in self.fallback_manager.process_with_fallback(prompt):
                yield result
                
        except Exception as e:
            logger.error(f"Error in text processing fallback: {e}")
            yield f"Error: Text processing failed - {str(e)}"
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса менеджера fallback
        
        Returns:
            Словарь со статусом менеджера
        """
        return self.fallback_manager.get_status()
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик менеджера fallback
        
        Returns:
            Словарь с метриками менеджера
        """
        return self.fallback_manager.get_metrics()
    
    def reset_metrics(self):
        """Сброс метрик менеджера"""
        self.fallback_manager.reset_metrics()
        logger.info("Text processing fallback metrics reset")
    
    def get_healthy_providers(self) -> List[UniversalProviderInterface]:
        """
        Получение списка здоровых провайдеров
        
        Returns:
            Список здоровых провайдеров
        """
        return self.fallback_manager.get_healthy_providers()
    
    def get_failed_providers(self) -> List[UniversalProviderInterface]:
        """
        Получение списка failed провайдеров
        
        Returns:
            Список failed провайдеров
        """
        return self.fallback_manager.get_failed_providers()
    
    def get_provider_by_name(self, name: str) -> Optional[UniversalProviderInterface]:
        """
        Получение провайдера по имени
        
        Args:
            name: Имя провайдера
            
        Returns:
            Провайдер или None если не найден
        """
        for provider in self.providers:
            if provider.name == name:
                return provider
        return None
    
    def get_provider_status(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Получение статуса конкретного провайдера
        
        Args:
            name: Имя провайдера
            
        Returns:
            Статус провайдера или None если не найден
        """
        provider = self.get_provider_by_name(name)
        if provider:
            return provider.get_status()
        return None
    
    def get_provider_metrics(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Получение метрик конкретного провайдера
        
        Args:
            name: Имя провайдера
            
        Returns:
            Метрики провайдера или None если не найден
        """
        provider = self.get_provider_by_name(name)
        if provider:
            return provider.get_metrics()
        return None
    
    def force_reset_provider(self, name: str) -> bool:
        """
        Принудительный сброс провайдера
        
        Args:
            name: Имя провайдера
            
        Returns:
            True если провайдер сброшен, False если не найден
        """
        provider = self.get_provider_by_name(name)
        if provider:
            provider.reset_metrics()
            # Сбрасываем circuit breaker
            self.fallback_manager.circuit_breakers[provider.name] = False
            logger.info(f"Provider {name} forcefully reset")
            return True
        return False
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по всем провайдерам
        
        Returns:
            Словарь со сводкой
        """
        summary = {
            "total_providers": len(self.providers),
            "healthy_providers": len(self.get_healthy_providers()),
            "failed_providers": len(self.get_failed_providers()),
            "providers": []
        }
        
        for provider in self.providers:
            provider_info = {
                "name": provider.name,
                "priority": provider.priority,
                "status": provider.status.value,
                "is_initialized": provider.is_initialized,
                "error_count": provider.error_count,
                "total_requests": provider.total_requests,
                "success_rate": (
                    provider.successful_requests / provider.total_requests 
                    if provider.total_requests > 0 else 0
                )
            }
            summary["providers"].append(provider_info)
        
        return summary
    
    def __str__(self) -> str:
        """Строковое представление менеджера"""
        return f"TextProcessingFallbackManager(providers={len(self.providers)})"
    
    def __repr__(self) -> str:
        """Представление менеджера для отладки"""
        return (
            f"TextProcessingFallbackManager("
            f"providers={len(self.providers)}, "
            f"healthy={len(self.get_healthy_providers())}, "
            f"failed={len(self.get_failed_providers())}"
            f")"
        )
