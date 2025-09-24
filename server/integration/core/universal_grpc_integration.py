"""
Универсальная интеграция для gRPC сервиса
"""

import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class UniversalGrpcIntegration(ABC):
    """
    Универсальная интеграция для gRPC сервиса
    
    Обеспечивает стандартный способ интеграции модулей с gRPC сервером
    """
    
    def __init__(self, name: str, module: Any):
        """
        Инициализация интеграции
        
        Args:
            name: Имя интеграции
            module: Экземпляр модуля для интеграции
        """
        self.name = name
        self.module = module
        self.is_initialized = False
        
        logger.info(f"gRPC Integration {self.name} created")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Инициализация интеграции
        
        Returns:
            True если инициализация успешна, False иначе
        """
        pass
    
    @abstractmethod
    async def process_request(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Обработка запроса через модуль
        
        Args:
            request_data: Данные запроса
            
        Yields:
            Результаты обработки
        """
        pass
    
    @abstractmethod
    async def interrupt(self, hardware_id: str) -> bool:
        """
        Прерывание обработки для указанного hardware_id
        
        Args:
            hardware_id: ID оборудования для прерывания
            
        Returns:
            True если прерывание успешно, False иначе
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов интеграции
        
        Returns:
            True если очистка успешна, False иначе
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса интеграции
        
        Returns:
            Словарь со статусом интеграции
        """
        return {
            "name": self.name,
            "is_initialized": self.is_initialized,
            "module_name": getattr(self.module, 'name', 'unknown') if self.module else 'none'
        }
    
    def __str__(self) -> str:
        """Строковое представление интеграции"""
        return f"GrpcIntegration({self.name}, initialized={self.is_initialized})"
    
    def __repr__(self) -> str:
        """Представление интеграции для отладки"""
        return (
            f"UniversalGrpcIntegration("
            f"name='{self.name}', "
            f"initialized={self.is_initialized}, "
            f"module={getattr(self.module, 'name', 'unknown') if self.module else 'none'}"
            f")"
        )
