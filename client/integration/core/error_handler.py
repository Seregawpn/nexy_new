"""
ErrorHandler - Обработка ошибок в интеграции
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Уровни серьезности ошибок"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ErrorCategory(Enum):
    """Категории ошибок"""
    INITIALIZATION = "initialization"
    RUNTIME = "runtime"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERMISSION = "permission"
    UNKNOWN = "unknown"

class ErrorHandler:
    """Обработчик ошибок для интеграции"""
    
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.error_history = []
        self.max_history = 1000
        
    async def handle_error(self, severity: ErrorSeverity, category: ErrorCategory, 
                          message: str, context: Dict[str, Any] = None):
        """Обработать ошибку"""
        try:
            if context is None:
                context = {}
            
            error = {
                "severity": severity,
                "category": category,
                "message": message,
                "context": context,
                "timestamp": self._get_timestamp()
            }
            
            # Добавляем в историю
            self.error_history.append(error)
            if len(self.error_history) > self.max_history:
                self.error_history.pop(0)
            
            # Логируем ошибку
            log_level = self._get_log_level(severity)
            logger.log(log_level, f"❌ {category.value.upper()}: {message}")
            
            # Публикуем событие ошибки
            if self.event_bus:
                await self.event_bus.publish("error.occurred", {
                    "severity": severity.value,
                    "category": category.value,
                    "message": message,
                    "context": context
                })
            
        except Exception as e:
            logger.error(f"❌ Ошибка в обработчике ошибок: {e}")
    
    def _get_log_level(self, severity: ErrorSeverity) -> int:
        """Получить уровень логирования для серьезности"""
        levels = {
            ErrorSeverity.LOW: logging.DEBUG,
            ErrorSeverity.MEDIUM: logging.INFO,
            ErrorSeverity.HIGH: logging.WARNING,
            ErrorSeverity.CRITICAL: logging.ERROR
        }
        return levels.get(severity, logging.ERROR)
    
    def _get_timestamp(self) -> float:
        """Получить текущий timestamp"""
        import time
        return time.time()
    
    def get_error_history(self, severity: ErrorSeverity = None, 
                         category: ErrorCategory = None, limit: int = 100) -> list:
        """Получить историю ошибок"""
        try:
            filtered_history = self.error_history
            
            if severity:
                filtered_history = [
                    error for error in filtered_history 
                    if error["severity"] == severity
                ]
            
            if category:
                filtered_history = [
                    error for error in filtered_history 
                    if error["category"] == category
                ]
            
            return filtered_history[-limit:]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории ошибок: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус обработчика ошибок"""
        return {
            "error_history_size": len(self.error_history),
            "max_history": self.max_history,
            "has_event_bus": self.event_bus is not None
        }
