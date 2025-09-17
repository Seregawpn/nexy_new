"""
EventBus - Система событий для интеграции модулей
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Приоритеты событий"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class EventBus:
    """Система событий для интеграции модулей"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Dict[str, Any]]] = {}
        self.event_history: List[Dict[str, Any]] = []
        self.max_history = 1000
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def attach_loop(self, loop: Optional[asyncio.AbstractEventLoop] = None):
        """Зафиксировать основной event loop для безопасной доставки событий из любых потоков."""
        try:
            self._loop = loop or asyncio.get_running_loop()
            logger.debug(f"EventBus: attached loop={id(self._loop)} running={self._loop.is_running() if self._loop else False}")
        except Exception:
            self._loop = None
        
    async def subscribe(self, event_type: str, callback: Callable, priority: EventPriority = EventPriority.MEDIUM):
        """Подписка на событие"""
        try:
            if event_type not in self.subscribers:
                self.subscribers[event_type] = []
            
            subscriber = {
                "callback": callback,
                "priority": priority,
                "event_type": event_type
            }
            
            self.subscribers[event_type].append(subscriber)
            
            # Сортируем по приоритету (высокий приоритет первым)
            self.subscribers[event_type].sort(key=lambda x: x["priority"].value, reverse=True)
            
            logger.info(f"📝 Подписка на событие: {event_type} (приоритет: {priority.name})")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подписки на событие {event_type}: {e}")
    
    async def unsubscribe(self, event_type: str, callback: Callable):
        """Отписка от события"""
        try:
            if event_type in self.subscribers:
                self.subscribers[event_type] = [
                    sub for sub in self.subscribers[event_type] 
                    if sub["callback"] != callback
                ]
                
                if not self.subscribers[event_type]:
                    del self.subscribers[event_type]
                
                logger.info(f"📝 Отписка от события: {event_type}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отписки от события {event_type}: {e}")
    
    async def publish(self, event_type: str, data: Dict[str, Any] = None):
        """Публикация события"""
        try:
            if data is None:
                data = {}
            
            event = {
                "type": event_type,
                "data": data,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Добавляем в историю
            self.event_history.append(event)
            if len(self.event_history) > self.max_history:
                self.event_history.pop(0)
            
            # Уведомляем подписчиков
            subs_cnt = len(self.subscribers.get(event_type, []))
            if event_type == "app.mode_changed":
                logger.info(f"EventBus: '{event_type}' → subscribers={subs_cnt}, data={data}")
            logger.debug(f"EventBus: dispatch '{event_type}' to {subs_cnt} subscriber(s)")
            if event_type in self.subscribers:
                for subscriber in self.subscribers[event_type]:
                    try:
                        cb = subscriber["callback"]
                        if asyncio.iscoroutinefunction(cb):
                            # Если закреплён основной loop и он запущен — выполняем в нём
                            if self._loop and self._loop.is_running() and self._loop != asyncio.get_event_loop():
                                fut = asyncio.run_coroutine_threadsafe(cb(event), self._loop)
                                logger.debug(f"EventBus: scheduled async callback on main loop for '{event_type}': {cb} -> {fut}")
                            else:
                                logger.debug(f"EventBus: awaiting async callback inline for '{event_type}': {cb}")
                                await cb(event)
                        else:
                            logger.debug(f"EventBus: calling sync callback for '{event_type}': {cb}")
                            cb(event)
                    except Exception as e:
                        logger.error(f"❌ Ошибка в обработчике события {event_type}: {e}")

            logger.debug(f"📢 Событие опубликовано: {event_type}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка публикации события {event_type}: {e}")
    
    def get_event_history(self, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Получить историю событий"""
        try:
            if event_type:
                filtered_history = [
                    event for event in self.event_history 
                    if event["type"] == event_type
                ]
            else:
                filtered_history = self.event_history
            
            return filtered_history[-limit:]
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения истории событий: {e}")
            return []
    
    def get_subscribers_count(self, event_type: str = None) -> int:
        """Получить количество подписчиков"""
        try:
            if event_type:
                return len(self.subscribers.get(event_type, []))
            else:
                return sum(len(subs) for subs in self.subscribers.values())
                
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета подписчиков: {e}")
            return 0
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус EventBus"""
        return {
            "subscribers_count": self.get_subscribers_count(),
            "event_types": list(self.subscribers.keys()),
            "history_size": len(self.event_history),
            "max_history": self.max_history
        }
