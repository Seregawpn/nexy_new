"""
ApplicationStateManager - Управление состоянием приложения
"""

import logging
from typing import Dict, Any, Optional
import threading

"""
NOTE: AppMode is imported from the centralized mode_management module to avoid
duplication and desynchronization. This keeps a single source of truth for
application modes across all integrations.
"""
try:
    # Preferred: top-level import (packaged or PYTHONPATH includes modules)
    from mode_management import AppMode  # type: ignore
except Exception:
    try:
        # Fallback: explicit modules path if repository layout is used
        from modules.mode_management import AppMode  # type: ignore
    except Exception:
        # Last-resort minimal inline enum to not break local tools; values match
        # the centralized one. Should not be used in production.
        from enum import Enum
        class AppMode(Enum):
            SLEEPING = "sleeping"
            LISTENING = "listening"
            PROCESSING = "processing"

logger = logging.getLogger(__name__)

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

                # 🎯 TRAY DEBUG: Синхронный лог ПЕРЕД публикацией
                logger.info(f"🎯 TRAY DEBUG: set_mode() готов публиковать app.mode_changed: {mode}")
                logger.info(f"🎯 TRAY DEBUG: EventBus подключен: {self._event_bus is not None}")

                # Публикуем централизованные события (если EventBus подключен)
                if self._event_bus is not None:
                    try:
                        import asyncio
                        # Всегда ориентируемся на loop, закреплённый в EventBus
                        loop = getattr(self._event_bus, "_loop", None)
                        logger.info(
                            f"🔄 StateManager: начинаем публикацию событий (EventBus подключен, eb_loop={id(loop) if loop else None})"
                        )

                        async def _publish_changes():
                            logger.info(
                                f"🎯 TRAY DEBUG: StateManager публикует app.mode_changed: {mode} (type: {type(mode)})"
                            )
                            event_data = {"mode": mode}
                            logger.info(f"🎯 TRAY DEBUG: StateManager event_data: {event_data}")
                            await self._event_bus.publish("app.mode_changed", event_data)
                            logger.info("🎯 TRAY DEBUG: StateManager app.mode_changed опубликовано успешно")

                            # Проверяем есть ли подписчики
                            try:
                                subscribers = getattr(self._event_bus, 'subscribers', {}).get("app.mode_changed", [])
                                logger.info(
                                    f"🎯 TRAY DEBUG: StateManager подписчиков на app.mode_changed: {len(subscribers)}"
                                )
                            except Exception:
                                pass
                            logger.info(
                                f"🔄 StateManager: -> publish app.state_changed: {self.previous_mode} -> {mode}"
                            )
                            await self._event_bus.publish("app.state_changed", {
                                "old_mode": self.previous_mode,
                                "new_mode": mode
                            })

                        # Если у EventBus есть живой loop — публикуем на нём
                        if loop is not None and getattr(loop, 'is_running', lambda: False)():
                            logger.info("🔄 StateManager: публикуем через run_coroutine_threadsafe на loop EventBus (без ожидания)")
                            # Не ждём завершения — исключаем блокировку UI-сигналов
                            asyncio.run_coroutine_threadsafe(_publish_changes(), loop)
                        else:
                            logger.info("🔄 StateManager: публикуем через asyncio.run (fallback)")
                            asyncio.run(_publish_changes())
                        logger.info("✅ StateManager: события опубликованы успешно")
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
