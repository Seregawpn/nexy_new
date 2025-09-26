"""
Универсальный интерфейс для всех провайдеров
"""

import time
import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ProviderStatus(Enum):
    """Статус провайдера"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"

class UniversalProviderInterface(ABC):
    """
    Универсальный интерфейс для всех провайдеров
    
    Этот интерфейс должен быть реализован всеми провайдерами
    для обеспечения единообразия и совместимости.
    """
    
    def __init__(self, name: str, priority: int, config: Dict[str, Any]):
        """
        Инициализация провайдера
        
        Args:
            name: Имя провайдера
            priority: Приоритет провайдера (1 - высший, 2 - средний, 3 - низший)
            config: Конфигурация провайдера
        """
        self.name = name
        self.priority = priority
        self.config = config
        
        # Состояние провайдера
        self.status = ProviderStatus.UNKNOWN
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.last_success: Optional[float] = None
        self.is_initialized = False
        
        # Метрики
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
        logger.info(f"Provider {self.name} created with priority {self.priority}")
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Инициализация провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        pass
    
    @abstractmethod
    async def process(self, input_data: Any) -> AsyncGenerator[Any, None]:
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
        Очистка ресурсов провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Проверка здоровья провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        if not self.is_initialized:
            return False
            
        # Базовые проверки здоровья
        if self.status == ProviderStatus.FAILED:
            return False
            
        # Дополнительные проверки (переопределяются в наследниках)
        return await self._custom_health_check()
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья (переопределяется в наследниках)
        
        Returns:
            True если провайдер здоров, False иначе
        """
        return True
    
    def report_success(self):
        """Сообщить об успешном выполнении"""
        self.status = ProviderStatus.HEALTHY
        self.error_count = 0
        self.last_success = time.time()
        self.successful_requests += 1
        logger.debug(f"Provider {self.name} reported success")
    
    def report_error(self, error: str):
        """
        Сообщить об ошибке провайдера
        
        Args:
            error: Описание ошибки
        """
        self.error_count += 1
        self.last_error = str(error)
        self.failed_requests += 1
        
        if self.error_count >= 3:
            self.status = ProviderStatus.FAILED
            logger.warning(f"Provider {self.name} marked as FAILED after {self.error_count} errors")
        else:
            self.status = ProviderStatus.DEGRADED
            logger.warning(f"Provider {self.name} reported error #{self.error_count}: {error}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        return {
            "name": self.name,
            "priority": self.priority,
            "status": self.status.value,
            "is_initialized": self.is_initialized,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_success": self.last_success,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests 
                if self.total_requests > 0 else 0
            )
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        return {
            "name": self.name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (
                self.successful_requests / self.total_requests 
                if self.total_requests > 0 else 0
            ),
            "error_count": self.error_count,
            "last_success": self.last_success,
            "uptime": (
                time.time() - self.last_success 
                if self.last_success else None
            )
        }
    
    def reset_metrics(self):
        """Сброс метрик провайдера"""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.error_count = 0
        self.last_error = None
        self.status = ProviderStatus.UNKNOWN
        logger.info(f"Provider {self.name} metrics reset")
    
    def __str__(self) -> str:
        """Строковое представление провайдера"""
        return f"Provider({self.name}, priority={self.priority}, status={self.status.value})"
    
    def __repr__(self) -> str:
        """Представление провайдера для отладки"""
        return (
            f"UniversalProviderInterface("
            f"name='{self.name}', "
            f"priority={self.priority}, "
            f"status='{self.status.value}', "
            f"initialized={self.is_initialized}, "
            f"errors={self.error_count}"
            f")"
        )
