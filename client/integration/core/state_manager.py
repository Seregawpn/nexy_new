"""
ApplicationStateManager - Управление состоянием приложения
"""

import logging
from typing import Dict, Any, Optional
import threading
from enum import Enum

logger = logging.getLogger(__name__)

class AppMode(Enum):
    """Режимы приложения"""
    SLEEPING = "sleeping"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"

class ApplicationStateManager:
    """Менеджер состояния приложения"""
    
    def __init__(self):
        self.current_mode = AppMode.SLEEPING
        self.previous_mode = None
        self.mode_history = []
        self.state_data = {}
        # EventBus (необязателен). Устанавливается координатором.
        self._event_bus = None
        self._loop = None  # основной asyncio loop, на который публикуем события

    def attach_event_bus(self, event_bus):
        """Прикрепить EventBus для публикации событий смены режима"""
        self._event_bus = event_bus
        try:
            import asyncio
            # Сохраняем текущий running loop как основной для публикаций
            self._loop = asyncio.get_running_loop()
            logger.debug(f"StateManager: attached EventBus with loop={id(self._loop)} running={self._loop.is_running() if self._loop else False}")
        except Exception:
            self._loop = None
        
    def set_mode(self, mode: AppMode):
        """Установить режим приложения"""
        try:
            if self.current_mode != mode:
                self.previous_mode = self.current_mode
                self.current_mode = mode
                
                # Добавляем в историю
                self.mode_history.append({
                    "mode": mode,
                    "previous_mode": self.previous_mode,
                    "timestamp": self._get_timestamp()
                })
                
                # Ограничиваем историю
                if len(self.mode_history) > 100:
                    self.mode_history.pop(0)
                
                logger.info(f"🔄 Режим изменен: {self.previous_mode.value} → {mode.value}")

                # Публикуем централизованные события (если EventBus подключен)
                if self._event_bus is not None:
                    try:
                        import asyncio
                        logger.info(f"🔄 StateManager: начинаем публикацию событий (EventBus подключен, loop={id(self._loop) if self._loop else None})")
                        async def _publish_changes():
                            logger.info(f"🔄 StateManager: -> publish app.mode_changed: {mode}")
                            await self._event_bus.publish("app.mode_changed", {"mode": mode})
                            logger.info(f"🔄 StateManager: -> publish app.state_changed: {self.previous_mode} -> {mode}")
                            await self._event_bus.publish("app.state_changed", {
                                "old_mode": self.previous_mode,
                                "new_mode": mode
                            })
                        # Публикуем всегда на сохранённый основной loop, если он есть и живой
                        if self._loop is not None and self._loop.is_running():
                            logger.info(f"🔄 StateManager: публикуем через run_coroutine_threadsafe")
                            asyncio.run_coroutine_threadsafe(_publish_changes(), self._loop)
                        else:
                            logger.info(f"🔄 StateManager: публикуем через asyncio.run (fallback)")
                            # Fallback: синхронно в текущем потоке
                            asyncio.run(_publish_changes())
                        logger.info(f"✅ StateManager: события опубликованы успешно")
                    except Exception as e:
                        logger.error(f"❌ StateManager: Не удалось опубликовать события смены режима: {e}")
                        import traceback
                        logger.error(f"❌ StateManager: Traceback: {traceback.format_exc()}")
                else:
                    logger.warning(f"⚠️ StateManager: EventBus не подключен, события не публикуются")
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки режима: {e}")
    
    def get_current_mode(self) -> AppMode:
        """Получить текущий режим"""
        return self.current_mode
    
    def get_previous_mode(self) -> Optional[AppMode]:
        """Получить предыдущий режим"""
        return self.previous_mode
    
    def set_state_data(self, key: str, value: Any):
        """Установить данные состояния"""
        try:
            self.state_data[key] = value
            logger.debug(f"📊 Данные состояния обновлены: {key}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка установки данных состояния: {e}")
    
    def get_state_data(self, key: str, default: Any = None) -> Any:
        """Получить данные состояния"""
        return self.state_data.get(key, default)
    
    def get_mode_history(self, limit: int = 10) -> list:
        """Получить историю режимов"""
        return self.mode_history[-limit:]
    
    def _get_timestamp(self) -> float:
        """Получить текущий timestamp"""
        import time
        return time.time()
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус менеджера состояния"""
        return {
            "current_mode": self.current_mode.value,
            "previous_mode": self.previous_mode.value if self.previous_mode else None,
            "mode_history_size": len(self.mode_history),
            "state_data_keys": list(self.state_data.keys())
        }
