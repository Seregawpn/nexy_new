"""
BaseWorkflow - Базовый класс для всех workflow'ов
Обеспечивает единообразную архитектуру и интеграцию с EventBus
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set
from enum import Enum

# Импорт режимов из централизованного источника
try:
    from modules.mode_management import AppMode
except ImportError:
    from enum import Enum
    class AppMode(Enum):
        SLEEPING = "sleeping"
        LISTENING = "listening" 
        PROCESSING = "processing"

from integration.core.event_bus import EventBus, EventPriority

logger = logging.getLogger(__name__)

class WorkflowState(Enum):
    """Состояния workflow'а"""
    IDLE = "idle"
    ACTIVE = "active"
    TRANSITIONING = "transitioning"
    CANCELLED = "cancelled"
    ERROR = "error"

class BaseWorkflow(ABC):
    """
    Базовый класс для workflow'ов режимов приложения.
    
    Принципы:
    - НЕ управляет режимами напрямую (только через события)
    - НЕ дублирует логику интеграций
    - Координирует последовательность событий
    - Обрабатывает прерывания и ошибки
    """
    
    def __init__(self, event_bus: EventBus, workflow_name: str):
        self.event_bus = event_bus
        self.workflow_name = workflow_name
        self.state = WorkflowState.IDLE
        self.current_session_id: Optional[str] = None
        self.active_tasks: Set[asyncio.Task] = set()
        self._shutdown_requested = False
        
    async def initialize(self):
        """Инициализация workflow'а - подписка на события"""
        try:
            await self._setup_subscriptions()
            logger.info(f"🔄 {self.workflow_name}: инициализирован")
        except Exception as e:
            logger.error(f"❌ {self.workflow_name}: ошибка инициализации - {e}")
            raise
    
    async def start(self):
        """Запуск workflow'а"""
        try:
            self.state = WorkflowState.ACTIVE
            await self._on_start()
            logger.info(f"🚀 {self.workflow_name}: запущен")
        except Exception as e:
            logger.error(f"❌ {self.workflow_name}: ошибка запуска - {e}")
            self.state = WorkflowState.ERROR
            raise
    
    async def stop(self):
        """Остановка workflow'а"""
        try:
            self._shutdown_requested = True
            self.state = WorkflowState.IDLE
            
            # Отменяем все активные задачи
            for task in list(self.active_tasks):
                if not task.done():
                    task.cancel()
            
            # Ждем завершения задач
            if self.active_tasks:
                await asyncio.gather(*self.active_tasks, return_exceptions=True)
            
            await self._on_stop()
            logger.info(f"🛑 {self.workflow_name}: остановлен")
        except Exception as e:
            logger.error(f"❌ {self.workflow_name}: ошибка остановки - {e}")
    
    @abstractmethod
    async def _setup_subscriptions(self):
        """Настройка подписок на события - реализуется в наследниках"""
        pass
    
    @abstractmethod
    async def _on_start(self):
        """Действия при запуске - реализуется в наследниках"""
        pass
    
    async def _on_stop(self):
        """Действия при остановке - может быть переопределено"""
        pass
    
    def _create_task(self, coro, name: str = None) -> asyncio.Task:
        """Создание отслеживаемой задачи"""
        task = asyncio.create_task(coro, name=f"{self.workflow_name}:{name or 'task'}")
        self.active_tasks.add(task)
        task.add_done_callback(self._task_done_callback)
        return task
    
    def _task_done_callback(self, task: asyncio.Task):
        """Callback завершения задачи"""
        self.active_tasks.discard(task)
        if task.cancelled():
            logger.debug(f"🔄 {self.workflow_name}: задача отменена - {task.get_name()}")
        elif task.exception():
            logger.error(f"❌ {self.workflow_name}: ошибка в задаче {task.get_name()} - {task.exception()}")
    
    async def _wait_for_event(self, event_type: str, timeout: float = 30.0, 
                            session_filter: bool = True) -> Optional[Dict[str, Any]]:
        """
        Ожидание конкретного события с таймаутом
        
        Args:
            event_type: Тип события
            timeout: Таймаут в секундах
            session_filter: Фильтровать по текущей сессии
        """
        event_received = asyncio.Event()
        event_data = {}
        
        async def event_handler(event):
            nonlocal event_data
            try:
                data = event.get("data", {})
                
                # Фильтрация по сессии если включена
                if session_filter and self.current_session_id:
                    event_session = data.get("session_id")
                    if event_session and event_session != self.current_session_id:
                        return
                
                event_data = data
                event_received.set()
            except Exception as e:
                logger.error(f"❌ {self.workflow_name}: ошибка обработки события {event_type} - {e}")
        
        # Подписываемся на событие
        await self.event_bus.subscribe(event_type, event_handler, EventPriority.HIGH)
        
        try:
            # Ждем событие с таймаутом
            await asyncio.wait_for(event_received.wait(), timeout=timeout)
            return event_data
        except asyncio.TimeoutError:
            logger.warning(f"⏰ {self.workflow_name}: таймаут ожидания события {event_type}")
            return None
        finally:
            # Отписываемся от события
            try:
                await self.event_bus.unsubscribe(event_type, event_handler)
            except Exception:
                pass
    
    async def _publish_mode_request(self, target_mode: AppMode, source: str, 
                                   session_id: Optional[str] = None, priority: int = 50):
        """Публикация запроса смены режима"""
        try:
            await self.event_bus.publish("mode.request", {
                "target": target_mode,
                "source": f"{self.workflow_name}.{source}",
                "session_id": session_id or self.current_session_id,
                "priority": priority
            })
            logger.debug(f"🔄 {self.workflow_name}: запрос смены режима {target_mode.value}")
        except Exception as e:
            logger.error(f"❌ {self.workflow_name}: ошибка публикации mode.request - {e}")
    
    def is_active(self) -> bool:
        """Проверка активности workflow'а"""
        return self.state == WorkflowState.ACTIVE and not self._shutdown_requested
    
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса workflow'а"""
        return {
            "name": self.workflow_name,
            "state": self.state.value,
            "session_id": self.current_session_id,
            "active_tasks": len(self.active_tasks),
            "shutdown_requested": self._shutdown_requested
        }
