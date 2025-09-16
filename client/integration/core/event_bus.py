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
            if event_type in self.subscribers:
                for subscriber in self.subscribers[event_type]:
                    try:
                        if asyncio.iscoroutinefunction(subscriber["callback"]):
                            await subscriber["callback"](event)
                        else:
                            subscriber["callback"](event)
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
