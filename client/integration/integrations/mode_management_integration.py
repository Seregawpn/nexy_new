"""
ModeManagementIntegration — центральная точка управления режимами приложения.

Задачи:
- Принимать заявки на смену режима (mode.request) от модулей/интеграций
- Применять переходы согласно приоритетам и базовым правилам
- Делать реальный вызов state_manager.set_mode() ровно в одном месте

Примечание: на этапе мягкой миграции интеграции ещё могут вызывать set_mode напрямую.
Этот класс уже обеспечивает корректную обработку заявок и таймаут PROCESSING.
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler

# Централизованный контроллер режимов
try:
    from mode_management import (
        ModeController, ModeTransition, ModeTransitionType, ModeConfig,
    )
except Exception:
    # Fallback to explicit modules path when running from repo
    from modules.mode_management import (
        ModeController, ModeTransition, ModeTransitionType, ModeConfig,
    )

logger = logging.getLogger(__name__)


class ModeManagementIntegration:
    """Централизованное управление режимами."""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler

        self._initialized = False
        self._running = False

        # Централизованный контроллер режимов (single source of truth)
        self.controller: ModeController = ModeController(ModeConfig())

        # Управление таймаутом PROCESSING (0.0 = отключено по требованиям)
        self._processing_timeout_sec = 0.0
        self._processing_timeout_task: Optional[asyncio.Task] = None

        # Текущая активная сессия (для фильтрации заявок)
        self._active_session_id: Optional[Any] = None

        # Таймаут LISTENING (0.0 = отключено по требованиям)
        self._listening_timeout_sec = 0.0
        self._listening_timeout_task: Optional[asyncio.Task] = None

        # Приоритеты источников (чем больше — тем важнее)
        self._priorities = {
            'interrupt': 100,
            'keyboard.short_press': 80,
            'keyboard.release': 60,
            'keyboard.long_press': 60,
            'playback': 50,
            'grpc': 50,
            'fallback': 10,
        }

    # ---------------- Lifecycle ----------------
    async def initialize(self) -> bool:
        try:
            # Подписки на события заявок и системные события
            await self.event_bus.subscribe("mode.request", self._on_mode_request, EventPriority.CRITICAL)
            await self.event_bus.subscribe("app.mode_changed", self._on_app_mode_changed, EventPriority.HIGH)

            # Регистрируем допустимые переходы контроллера
            # Классический цикл: SLEEPING -> LISTENING -> PROCESSING -> SLEEPING
            self.controller.register_transition(ModeTransition(AppMode.SLEEPING, AppMode.LISTENING, ModeTransitionType.AUTOMATIC))
            self.controller.register_transition(ModeTransition(AppMode.LISTENING, AppMode.PROCESSING, ModeTransitionType.AUTOMATIC))
            self.controller.register_transition(ModeTransition(AppMode.PROCESSING, AppMode.SLEEPING, ModeTransitionType.AUTOMATIC))
            
            # 🆕 Прямой переход для приветствия: SLEEPING -> PROCESSING
            self.controller.register_transition(ModeTransition(AppMode.SLEEPING, AppMode.PROCESSING, ModeTransitionType.MANUAL))

            # Мост: при смене режима контроллером — обновляем StateManager,
            # который централизованно публикует события (app.mode_changed/app.state_changed)
            async def _on_controller_mode_changed(event):
                try:
                    # event.mode — это AppMode из централизованного модуля
                    self.state_manager.set_mode(event.mode)
                except Exception as e:
                    logger.error(f"StateManager bridging failed: {e}")
            self.controller.register_mode_change_callback(_on_controller_mode_changed)

            # Мост с существующими событиями (на время миграции)
            # Отключено, чтобы избежать дублей mode.request (источник — InputProcessingIntegration)
            # await self.event_bus.subscribe("keyboard.long_press", self._bridge_keyboard_long, EventPriority.MEDIUM)
            # await self.event_bus.subscribe("keyboard.release", self._bridge_keyboard_release, EventPriority.MEDIUM)
            # await self.event_bus.subscribe("keyboard.short_press", self._bridge_keyboard_short, EventPriority.MEDIUM)

            # Внимание: не возвращаем SLEEPING по завершению gRPC — ждём завершения воспроизведения
            # Доп. подписки для контекста (без публикации режимов)
            try:
                await self.event_bus.subscribe("voice.recording_start", self._on_voice_recording_start, EventPriority.MEDIUM)
            except Exception:
                pass
            # await self.event_bus.subscribe("grpc.request_completed", self._bridge_grpc_done, EventPriority.MEDIUM)
            # await self.event_bus.subscribe("grpc.request_failed", self._bridge_grpc_done, EventPriority.MEDIUM)

            await self.event_bus.subscribe("playback.completed", self._bridge_playback_done, EventPriority.MEDIUM)
            await self.event_bus.subscribe("playback.failed", self._bridge_playback_done, EventPriority.MEDIUM)

            # УБРАНО: interrupt.request - обрабатывается централизованно в InterruptManagementIntegration

            self._initialized = True
            logger.info("ModeManagementIntegration initialized")
            return True
        except Exception as e:
            logger.error(f"ModeManagementIntegration init failed: {e}")
            return False

    async def start(self) -> bool:
        if not self._initialized:
            return False
        self._running = True
        logger.info("ModeManagementIntegration started")
        return True

    async def stop(self) -> bool:
        try:
            self._running = False
            if self._processing_timeout_task:
                self._processing_timeout_task.cancel()
            return True
        except Exception:
            return False

    # ---------------- Event handlers ----------------
    async def _on_mode_request(self, event):
        try:
            data = (event or {}).get("data", {})
            target = data.get("target")  # может быть AppMode или str
            if isinstance(target, str):
                try:
                    target = AppMode(target.lower())
                except Exception:
                    # допускаем значения вида "PROCESSING" без понижения регистра
                    try:
                        target = AppMode(target.lower())
                    except Exception:
                        return
            if target not in (AppMode.SLEEPING, AppMode.LISTENING, AppMode.PROCESSING):
                return

            priority = int(data.get("priority", 0))
            source = str(data.get("source", "unknown"))
            session_id = data.get("session_id")

            # Фильтрация по сессии (в PROCESSING принимаем только текущую либо interrupt)
            current_mode = self.state_manager.get_current_mode()
            # Идемпотентность: если запрашивают тот же режим — игнорируем
            if target == current_mode:
                logger.debug(f"Mode request ignored (same mode): {target}")
                return
            if current_mode == AppMode.PROCESSING and source != 'interrupt':
                if self._active_session_id is not None and session_id is not None:
                    if session_id != self._active_session_id:
                        logger.debug("Mode request ignored due to session mismatch in PROCESSING")
                        return

            # Приоритеты: если заявка из более низкого приоритета — применяем только если нет конфликтов
            # Упрощённая модель: interrupt всегда применяется, остальное — напрямую
            if source == 'interrupt':
                await self._apply_mode(target, source="interrupt")
                return

            await self._apply_mode(target, source=source)

            # Обновляем активную сессию
            if target == AppMode.LISTENING:
                self._active_session_id = session_id
            elif target == AppMode.SLEEPING:
                self._active_session_id = None

        except Exception as e:
            logger.error(f"Mode request handling error: {e}")

    async def _on_app_mode_changed(self, event):
        try:
            data = (event or {}).get("data", {})
            new_mode = data.get("mode")
            # Синхронизируем внутренний контроллер, если режим изменили в обход
            try:
                if hasattr(self.controller, 'get_current_mode') and new_mode is not None:
                    if self.controller.get_current_mode() != new_mode:
                        # Обновляем только внутреннее состояние без действий/обработчиков
                        self.controller.previous_mode = getattr(self.controller, 'current_mode', None)
                        self.controller.current_mode = new_mode
                        self.controller.mode_start_time = __import__('time').time()
            except Exception:
                pass
            if new_mode == AppMode.PROCESSING:
                # PROCESSING: запуск таймера только если включен (>0)
                if self._processing_timeout_task and not self._processing_timeout_task.done():
                    self._processing_timeout_task.cancel()
                if (self._processing_timeout_sec or 0) > 0:
                    self._processing_timeout_task = asyncio.create_task(self._processing_timeout_guard())
                if self._listening_timeout_task and not self._listening_timeout_task.done():
                    self._listening_timeout_task.cancel()
            elif new_mode == AppMode.LISTENING:
                # LISTENING: запуск таймера только если включен (>0)
                if self._listening_timeout_task and not self._listening_timeout_task.done():
                    self._listening_timeout_task.cancel()
                if (self._listening_timeout_sec or 0) > 0:
                    self._listening_timeout_task = asyncio.create_task(self._listening_timeout_guard())
                if self._processing_timeout_task and not self._processing_timeout_task.done():
                    self._processing_timeout_task.cancel()
            else:
                # Прочие режимы — таймеры не нужны
                if self._processing_timeout_task and not self._processing_timeout_task.done():
                    self._processing_timeout_task.cancel()
                if self._listening_timeout_task and not self._listening_timeout_task.done():
                    self._listening_timeout_task.cancel()
        except Exception:
            pass

    async def _on_voice_recording_start(self, event):
        """Фиксируем session_id для контекста LISTENING/PROCESSING."""
        try:
            data = (event or {}).get("data", {})
            sid = data.get("session_id")
            if sid is not None:
                self._active_session_id = sid
        except Exception:
            pass

    # --------------- Bridges (temporary during migration) ---------------
    async def _bridge_keyboard_long(self, event):
        try:
            await self.event_bus.publish("mode.request", {
                "target": AppMode.LISTENING,
                "source": "keyboard.long_press"
            })
        except Exception:
            pass

    async def _bridge_keyboard_release(self, event):
        try:
            data = (event or {}).get("data", {})
            await self.event_bus.publish("mode.request", {
                "target": AppMode.PROCESSING,
                "source": "keyboard.release",
                "session_id": data.get("session_id")
            })
        except Exception:
            pass

    async def _bridge_keyboard_short(self, event):
        try:
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "keyboard.short_press"
            })
        except Exception:
            pass

    async def _bridge_grpc_done(self, event):
        try:
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "grpc"
            })
        except Exception:
            pass

    async def _bridge_playback_done(self, event):
        try:
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "playback"
            })
        except Exception:
            pass

    async def _bridge_interrupt(self, event):
        try:
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "interrupt",
                "priority": self._priorities.get('interrupt', 100)
            })
        except Exception:
            pass

    # ---------------- Internals ----------------
    async def _apply_mode(self, target: AppMode, *, source: str):
        try:
            # Поручаем переход контроллеру; он сам проверит доступность перехода
            # и при успехе через callback обновит StateManager (публикация событий сохранится централизованной)
            await self.controller.switch_mode(target)
        except Exception as e:
            logger.error(f"Apply mode error: {e}")

    async def _processing_timeout_guard(self):
        try:
            await asyncio.sleep(self._processing_timeout_sec)
            if self.state_manager.get_current_mode() == AppMode.PROCESSING:
                logger.warning("PROCESSING timeout — forcing SLEEPING via controller")
                try:
                    await self.controller.switch_mode(AppMode.SLEEPING)
                except Exception:
                    # Fallback to direct state update if controller failed
                    try:
                        self.state_manager.set_mode(AppMode.SLEEPING)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            return
        except Exception:
            pass

    async def _listening_timeout_guard(self):
        """Автовозврат в SLEEPING, если LISTENING затянулся без RELEASE/STOP."""
        try:
            await asyncio.sleep(self._listening_timeout_sec)
            if self.state_manager.get_current_mode() == AppMode.LISTENING:
                await self._apply_mode(AppMode.SLEEPING, source="mode_management")
        except asyncio.CancelledError:
            return
        except Exception:
            pass

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "running": self._running,
            "processing_timeout_sec": self._processing_timeout_sec,
            "listening_timeout_sec": self._listening_timeout_sec,
            "active_session_id": self._active_session_id,
        }
