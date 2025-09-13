"""
Координатор прерываний - центральный модуль для управления прерываниями
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass

from .types import (
    InterruptEvent, InterruptType, InterruptPriority, InterruptStatus,
    InterruptConfig, InterruptMetrics
)

logger = logging.getLogger(__name__)

@dataclass
class InterruptDependencies:
    """Зависимости для прерываний"""
    speech_player: Optional[Any] = None
    speech_recognizer: Optional[Any] = None
    grpc_client: Optional[Any] = None
    state_manager: Optional[Any] = None

class InterruptCoordinator:
    """Координатор прерываний - управляет всеми типами прерываний"""
    
    def __init__(self, config: InterruptConfig = None):
        self.config = config or InterruptConfig()
        self.dependencies = InterruptDependencies()
        
        # Активные прерывания
        self.active_interrupts: List[InterruptEvent] = []
        self.interrupt_history: List[InterruptEvent] = []
        
        # Обработчики прерываний
        self.interrupt_handlers: Dict[InterruptType, Callable] = {}
        self.priority_handlers: Dict[InterruptPriority, List[Callable]] = {}
        
        # Метрики
        self.metrics = InterruptMetrics()
        
        # Блокировка для thread-safety
        self._lock = asyncio.Lock()
        
    def initialize(self, dependencies: InterruptDependencies):
        """Инициализирует координатор с зависимостями"""
        self.dependencies = dependencies
        logger.info("✅ Координатор прерываний инициализирован")
        
    def register_handler(self, interrupt_type: InterruptType, handler: Callable):
        """Регистрирует обработчик для типа прерывания"""
        self.interrupt_handlers[interrupt_type] = handler
        logger.debug(f"📝 Зарегистрирован обработчик для {interrupt_type.value}")
        
    def register_priority_handler(self, priority: InterruptPriority, handler: Callable):
        """Регистрирует обработчик для приоритета"""
        if priority not in self.priority_handlers:
            self.priority_handlers[priority] = []
        self.priority_handlers[priority].append(handler)
        logger.debug(f"📝 Зарегистрирован обработчик для приоритета {priority.value}")
        
    async def trigger_interrupt(self, event: InterruptEvent) -> bool:
        """Запускает прерывание"""
        # Проверяем лимит активных прерываний (без блокировки)
        if len(self.active_interrupts) >= self.config.max_concurrent_interrupts:
            logger.warning(f"⚠️ Достигнут лимит активных прерываний: {self.config.max_concurrent_interrupts}")
            return False
        
        # Блокируем только для добавления в активные прерывания
        async with self._lock:
            # Повторно проверяем лимит (race condition protection)
            if len(self.active_interrupts) >= self.config.max_concurrent_interrupts:
                logger.warning(f"⚠️ Достигнут лимит активных прерываний: {self.config.max_concurrent_interrupts}")
                return False
            
            # Добавляем в активные прерывания
            event.status = InterruptStatus.PROCESSING
            self.active_interrupts.append(event)
            
            # Обновляем метрики
            self.metrics.total_interrupts += 1
            self.metrics.interrupts_by_type[event.type] += 1
            self.metrics.interrupts_by_priority[event.priority] += 1
            
            logger.info(f"🔄 Запуск прерывания {event.type.value} (приоритет: {event.priority.value})")
        
        try:
            # Выполняем прерывание БЕЗ блокировки (параллельно)
            result = await self._execute_interrupt(event)
            
            # Блокируем только для обновления статуса и перемещения в историю
            async with self._lock:
                # Обновляем статус
                if result:
                    event.status = InterruptStatus.COMPLETED
                    self.metrics.successful_interrupts += 1
                    logger.info(f"✅ Прерывание {event.type.value} выполнено успешно")
                else:
                    event.status = InterruptStatus.FAILED
                    self.metrics.failed_interrupts += 1
                    logger.error(f"❌ Прерывание {event.type.value} не выполнено")
                
                # Перемещаем в историю
                self.interrupt_history.append(event)
                self.active_interrupts.remove(event)
                
                # Очищаем старую историю (оставляем последние 100)
                if len(self.interrupt_history) > 100:
                    self.interrupt_history = self.interrupt_history[-100:]
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения прерывания {event.type.value}: {e}")
            event.status = InterruptStatus.FAILED
            event.error = str(e)
            
            # Блокируем для обновления статуса и перемещения в историю
            async with self._lock:
                self.metrics.failed_interrupts += 1
                self.interrupt_history.append(event)
                self.active_interrupts.remove(event)
            
            return False
                
    async def _execute_interrupt(self, event: InterruptEvent) -> bool:
        """Выполняет прерывание"""
        try:
            # Выполняем обработчик по типу
            handler = self.interrupt_handlers.get(event.type)
            if handler:
                start_time = time.time()
                result = await handler(event)
                processing_time = time.time() - start_time
                
                # Обновляем среднее время обработки
                if self.metrics.total_interrupts > 0:
                    self.metrics.average_processing_time = (
                        (self.metrics.average_processing_time * (self.metrics.total_interrupts - 1) + processing_time) 
                        / self.metrics.total_interrupts
                    )
                
                event.result = result
                return result
            else:
                logger.warning(f"⚠️ Обработчик для {event.type.value} не найден")
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка в обработчике {event.type.value}: {e}")
            event.error = str(e)
            return False
            
    def is_interrupting(self) -> bool:
        """Проверяет, идет ли прерывание"""
        return len(self.active_interrupts) > 0
        
    def get_active_interrupts(self) -> List[InterruptEvent]:
        """Возвращает активные прерывания"""
        return self.active_interrupts.copy()
        
    def get_interrupt_history(self, limit: int = 10) -> List[InterruptEvent]:
        """Возвращает историю прерываний"""
        return self.interrupt_history[-limit:]
        
    def get_metrics(self) -> InterruptMetrics:
        """Возвращает метрики прерываний"""
        return self.metrics
        
    def clear_history(self):
        """Очищает историю прерываний"""
        self.interrupt_history.clear()
        logger.info("🧹 История прерываний очищена")
        
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус координатора"""
        return {
            "active_interrupts": len(self.active_interrupts),
            "total_interrupts": self.metrics.total_interrupts,
            "successful_interrupts": self.metrics.successful_interrupts,
            "failed_interrupts": self.metrics.failed_interrupts,
            "success_rate": (
                self.metrics.successful_interrupts / max(self.metrics.total_interrupts, 1) * 100
            ),
            "average_processing_time": self.metrics.average_processing_time,
            "handlers_registered": len(self.interrupt_handlers),
            "config": {
                "max_concurrent_interrupts": self.config.max_concurrent_interrupts,
                "interrupt_timeout": self.config.interrupt_timeout,
                "retry_attempts": self.config.retry_attempts,
            }
        }
