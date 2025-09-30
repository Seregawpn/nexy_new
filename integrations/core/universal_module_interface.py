"""
Универсальный интерфейс для взаимодействия модулей
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator
from enum import Enum

logger = logging.getLogger(__name__)

class ModuleStatus(Enum):
    """Статус модуля"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    STOPPED = "stopped"

class UniversalModuleInterface(ABC):
    """
    Универсальный интерфейс для всех модулей
    
    Обеспечивает стандартный способ взаимодействия между модулями
    без знания о конкретной реализации.
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Инициализация модуля
        
        Args:
            name: Имя модуля
            config: Конфигурация модуля
        """
        self.name = name
        self.config = config
        self.status = ModuleStatus.UNINITIALIZED
        self.is_initialized = False
        
        logger.info(f"Module {self.name} created")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Инициализация модуля
        
        Returns:
            True если инициализация успешна, False иначе
        """
        pass
    
    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Основная обработка данных
        
        Args:
            input_data: Входные данные для обработки
            
        Yields:
            Результаты обработки
        """
        pass
    
    @abstractmethod
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов модуля
        
        Returns:
            True если очистка успешна, False иначе
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса модуля
        
        Returns:
            Словарь со статусом модуля
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "is_initialized": self.is_initialized,
            "config_keys": list(self.config.keys()) if self.config else []
        }
    
    def set_status(self, status: ModuleStatus):
        """Установка статуса модуля"""
        self.status = status
        logger.debug(f"Module {self.name} status changed to {status.value}")
    
    def __str__(self) -> str:
        """Строковое представление модуля"""
        return f"Module({self.name}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Представление модуля для отладки"""
        return (
            f"UniversalModuleInterface("
            f"name='{self.name}', "
            f"status='{self.status.value}', "
            f"initialized={self.is_initialized}"
            f")"
        )
