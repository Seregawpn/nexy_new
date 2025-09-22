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
        
    async def handle_error(self, severity: Any, category: Any, 
                          message: str, context: Dict[str, Any] = None):
        """Обработать ошибку"""
        try:
            if context is None:
                context = {}
            
            # Приведение типов к enum для устойчивости
            if not isinstance(severity, ErrorSeverity):
                sev_map = {
                    "low": ErrorSeverity.LOW,
                    "debug": ErrorSeverity.LOW,
                    "medium": ErrorSeverity.MEDIUM,
                    "info": ErrorSeverity.MEDIUM,
                    "high": ErrorSeverity.HIGH,
                    "warning": ErrorSeverity.HIGH,
                    "critical": ErrorSeverity.CRITICAL,
                    "error": ErrorSeverity.CRITICAL,
                }
                severity = sev_map.get(str(severity).lower(), ErrorSeverity.CRITICAL)
            if not isinstance(category, ErrorCategory):
                try:
                    category = ErrorCategory(str(category).lower())
                except Exception:
                    category = ErrorCategory.UNKNOWN
            
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

    async def handle(self, error: Exception, category: Any = "unknown", severity: Any = "error", context: Dict[str, Any] = None):
        """Совместимый метод обработки ошибок с гибкими типами аргументов.

        Args:
            error: Exception или строка сообщения
            category: строка или ErrorCategory
            severity: строка ('low'|'medium'|'high'|'critical'|'error') или ErrorSeverity
            context: произвольный контекст
        """
        try:
            # Сообщение
            message = str(error)
            # Severity маппинг
            if isinstance(severity, ErrorSeverity):
                sev = severity
            else:
                sev_map = {
                    "low": ErrorSeverity.LOW,
                    "debug": ErrorSeverity.LOW,
                    "medium": ErrorSeverity.MEDIUM,
                    "info": ErrorSeverity.MEDIUM,
                    "high": ErrorSeverity.HIGH,
                    "warning": ErrorSeverity.HIGH,
                    "critical": ErrorSeverity.CRITICAL,
                    "error": ErrorSeverity.CRITICAL,
                }
                sev = sev_map.get(str(severity).lower(), ErrorSeverity.CRITICAL)
            # Category маппинг
            if isinstance(category, ErrorCategory):
                cat = category
            else:
                try:
                    cat = ErrorCategory(str(category).lower())
                except Exception:
                    # Специфичные категории
                    if str(category).lower() in ("network",):
                        cat = ErrorCategory.NETWORK
                    elif str(category).lower() in ("permission", "permissions"):
                        cat = ErrorCategory.PERMISSION
                    elif str(category).lower() in ("configuration", "config"):
                        cat = ErrorCategory.CONFIGURATION
                    else:
                        cat = ErrorCategory.UNKNOWN
            await self.handle_error(sev, cat, message, context or {})
        except Exception as e:
            logger.error(f"❌ Ошибка в handle(): {e}")
    
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
