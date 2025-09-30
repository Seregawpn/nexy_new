"""
Интеграция модуля input_processing
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

# Импорты модулей input_processing
from modules.input_processing.keyboard.keyboard_monitor import KeyboardMonitor
from modules.input_processing.keyboard.types import KeyEvent, KeyEventType, KeyboardConfig

# Импорты интеграции
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

@dataclass
class InputProcessingConfig:
    """Конфигурация интеграции input_processing (клавиатура)"""
    keyboard_config: KeyboardConfig
    enable_keyboard_monitoring: bool = True
    auto_start: bool = True
    keyboard_backend: str = "auto"  # auto|quartz|pynput

class InputProcessingIntegration:
    """Интеграция модуля input_processing"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: InputProcessingConfig):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config
        # Флаг используемого backend
        self._using_quartz = False

        # Компоненты
        self.keyboard_monitor: Optional[KeyboardMonitor] = None
        
        # Состояние
        self.is_initialized = False
        self.is_running = False
        self._current_session_id: Optional[float] = None
        self._session_recognized: bool = False
        self._recording_started: bool = False
        # Debounce для short press в LISTENING
        self._last_short_ts: float = 0.0
        # Текущее состояние gRPC-потока
        self._session_waiting_grpc: bool = False
        self._active_grpc_session_id: Optional[float] = None
        
    async def initialize(self) -> bool:
        """Инициализация input_processing (клавиатура)"""
        try:
            logger.info("🔧 Инициализация input_processing...")
            
            # Инициализация клавиатуры
            if self.config.enable_keyboard_monitoring:
                await self._initialize_keyboard_monitor()
            
            # Настраиваем обработчики событий
            await self._setup_event_handlers()
            
            self.is_initialized = True
            logger.info("✅ input_processing инициализирован")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.INITIALIZATION,
                message=f"Ошибка инициализации InputProcessingIntegration: {e}",
                context={"where": "input_processing_integration.initialize"}
            )
            return False
            
    async def _initialize_keyboard_monitor(self):
        """Инициализация мониторинга клавиатуры"""
        try:
            # Выбираем backend
            backend = (self.config.keyboard_backend or "auto").lower()
            use_quartz = False
            try:
                import platform
                is_macos = platform.system() == "Darwin"
            except Exception:
                is_macos = False

            if is_macos and backend in ("auto", "quartz"):
                try:
                    from modules.input_processing.keyboard.mac.quartz_monitor import QuartzKeyboardMonitor
                    self.keyboard_monitor = QuartzKeyboardMonitor(self.config.keyboard_config)
                    use_quartz = True
                    self._using_quartz = True
                    logger.info("✅ Используется QuartzKeyboardMonitor (macOS)")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось инициализировать QuartzKeyboardMonitor: {e}. Фоллбек на pynput")

            if not use_quartz:
                self.keyboard_monitor = KeyboardMonitor(self.config.keyboard_config)
            
            # Регистрация обработчиков: для Quartz можно регистрировать async-методы напрямую,
            # для pynput используем sync wrapper'ы
            if self._using_quartz:
                self.keyboard_monitor.register_callback(KeyEventType.PRESS, self._handle_press)
                self.keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, self._handle_short_press)
                self.keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, self._handle_long_press)
                self.keyboard_monitor.register_callback(KeyEventType.RELEASE, self._handle_key_release)
            else:
                self.keyboard_monitor.register_callback(KeyEventType.PRESS, self._sync_handle_press)
                self.keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, self._sync_handle_short_press)
                self.keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, self._sync_handle_long_press)
                self.keyboard_monitor.register_callback(KeyEventType.RELEASE, self._sync_handle_key_release)
            
            logger.info("✅ KeyboardMonitor инициализирован")
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.INITIALIZATION,
                message=f"Ошибка инициализации keyboard monitor: {e}",
                context={"where": "input_processing_integration.initialize_keyboard_monitor"}
            )
            raise
    async def _handle_press(self, event: KeyEvent):
        """Начало удержания: готовим сессию, но не открываем микрофон (until LONG_PRESS)."""
        try:
            logger.info(f"🔑 PRESS EVENT: {event.timestamp} - начинаем запись")
            logger.debug(f"PRESS: session(before)={self._current_session_id}, recognized={self._session_recognized}")
            print(f"🔑 PRESS EVENT: {event.timestamp} - начинаем запись")  # Для отладки
            
            # НЕ ПРЕРЫВАЕМ НА PRESS - только готовим сессию
            # Прерывание будет только при LONG_PRESS (через секунду)

            # Создаем сессию и сбрасываем флаг распознавания
            self._current_session_id = event.timestamp or time.monotonic()
            self._session_recognized = False
            self._recording_started = False
            self._session_waiting_grpc = False
            self._active_grpc_session_id = None
            logger.debug(f"PRESS: session(after)={self._current_session_id}, recognized reset to {self._session_recognized}")
            # Публикуем событие press чтобы другие модули (например VoiceOver) могли отреагировать мгновенно
            await self.event_bus.publish(
                "keyboard.press",
                {
                    "type": "keyboard.press",
                    "data": {
                        "timestamp": self._current_session_id,
                        "key": event.key,
                        "source": "keyboard",
                    },
                    "timestamp": event.timestamp,
                }
            )
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки press: {e}",
                context={"where": "input_processing_integration.handle_press"}
            )
            
            
    async def _setup_event_handlers(self):
        """Настройка обработчиков событий (только клавиатура)"""
        # Подписка на события смены режима
        await self.event_bus.subscribe("mode.switch", self._handle_mode_switch, EventPriority.HIGH)
        # Подписка на завершение распознавания (для мгновенного решения)
        await self.event_bus.subscribe("voice.recognition_completed", self._on_recognition_completed, EventPriority.HIGH)
        # Возврат в SLEEPING при неудаче/таймауте распознавания
        try:
            await self.event_bus.subscribe("voice.recognition_failed", self._on_recognition_failed, EventPriority.HIGH)
        except Exception:
            pass
        try:
            await self.event_bus.subscribe("voice.recognition_timeout", self._on_recognition_failed, EventPriority.HIGH)
        except Exception:
            pass
        await self.event_bus.subscribe("grpc.request_completed", self._on_grpc_completed, EventPriority.HIGH)
        await self.event_bus.subscribe("grpc.request_failed", self._on_grpc_failed, EventPriority.HIGH)

    async def _on_recognition_completed(self, event):
        """Фиксируем факт распознавания для текущей сессии"""
        try:
            data = event.get("data") or {}
            session_id = data.get("session_id")
            if self._current_session_id is not None and session_id == self._current_session_id:
                self._session_recognized = True
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки recognition_completed: {e}",
                context={"where": "input_processing_integration.on_recognition_completed"}
            )
    
    async def _on_recognition_failed(self, event):
        """Возврат в SLEEPING при неудаче/таймауте распознавания."""
        try:
            self._reset_session("recognition_failed")
            # Переходим в SLEEPING через централизованный запрос
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "input_processing"
            })
            logger.info("VOICE FAIL/TIMEOUT: запрос на SLEEPING отправлен")
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки recognition_failed/timeout: {e}",
                context={"where": "input_processing_integration.on_recognition_failed"}
            )

    def _reset_session(self, reason: str):
        """Сбрасывает состояние текущей сессии после завершения gRPC-цепочки."""
        logger.debug(f"SESSION RESET ({reason})")
        self._current_session_id = None
        self._active_grpc_session_id = None
        self._session_waiting_grpc = False
        self._session_recognized = False
        self._recording_started = False

    async def _on_grpc_completed(self, event):
        """Сбрасывает сессию при штатном завершении gRPC."""
        try:
            data = (event or {}).get("data", {})
            session_id = data.get("session_id")
            if session_id is None:
                return

            if session_id in {self._active_grpc_session_id, self._current_session_id}:
                logger.debug(f"gRPC completed for session {session_id}")
                self._reset_session("grpc_completed")
            else:
                logger.debug(
                    "gRPC completed for session %s, ignored (current=%s, active=%s)",
                    session_id,
                    self._current_session_id,
                    self._active_grpc_session_id,
                )
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки grpc.request_completed: {e}",
                context={"where": "input_processing_integration.on_grpc_completed"}
            )

    async def _on_grpc_failed(self, event):
        """Сбрасывает сессию при ошибке или отмене gRPC."""
        try:
            data = (event or {}).get("data", {})
            session_id = data.get("session_id")
            if session_id is None:
                return

            if session_id in {self._active_grpc_session_id, self._current_session_id}:
                logger.debug(f"gRPC failed for session {session_id}")
                self._reset_session("grpc_failed")
            else:
                logger.debug(
                    "gRPC failed for session %s, ignored (current=%s, active=%s)",
                    session_id,
                    self._current_session_id,
                    self._active_grpc_session_id,
                )
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки grpc.request_failed: {e}",
                context={"where": "input_processing_integration.on_grpc_failed"}
            )
        
    async def start(self) -> bool:
        """Запуск input_processing"""
        print(f"🔧 DEBUG: InputProcessingIntegration.start() вызван")
        try:
            if not self.is_initialized:
                logger.warning("⚠️ input_processing не инициализирован")
                return False
                
            # Запуск мониторинга клавиатуры
            if self.keyboard_monitor:
                # Передаем основной event loop для корректной работы async колбэков
                import asyncio
                # Используем loop из EventBus (фоновый), если доступен
                loop = getattr(self.event_bus, "_loop", None)
                if not loop:
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = None
                if loop:
                    self.keyboard_monitor.set_loop(loop)
                self.keyboard_monitor.start_monitoring()
                logger.info("🎹 Мониторинг клавиатуры запущен")
                
                # Отладка: проверяем статус
                status = self.keyboard_monitor.get_status()
                print(f"🔧 DEBUG: KeyboardMonitor статус: {status}")
                print(f"🔧 DEBUG: Callbacks зарегистрированы: {status.get('callbacks_registered', 0)}")
                print(f"🔧 DEBUG: Мониторинг активен: {status.get('is_monitoring', False)}")
                print(f"⌨️ DEBUG: НАЖМИТЕ ПРОБЕЛ СЕЙЧАС ДЛЯ ТЕСТИРОВАНИЯ!")
                
            self.is_running = True
            logger.info("✅ input_processing запущен")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка запуска InputProcessingIntegration: {e}",
                context={"where": "input_processing_integration.start"}
            )
            return False
            
    async def stop(self) -> bool:
        """Остановка input_processing"""
        try:
            # Остановка мониторинга клавиатуры
            if self.keyboard_monitor:
                self.keyboard_monitor.stop_monitoring()
                logger.info("🎹 Мониторинг клавиатуры остановлен")
                
            self.is_running = False
            logger.info("✅ input_processing остановлен")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка остановки InputProcessingIntegration: {e}",
                context={"where": "input_processing_integration.stop"}
            )
            return False
            
    # Обработчики событий клавиатуры
    async def _handle_short_press(self, event: KeyEvent):
        """Обработка короткого нажатия пробела"""
        try:
            logger.debug(f"🔑 SHORT_PRESS: {event.duration:.3f}с")
            # Debounce: подавляем повторные короткие нажатия в LISTENING в течение ~120 мс
            try:
                current = self.state_manager.get_current_mode()
            except Exception:
                current = None
            now = time.monotonic()
            if current == AppMode.LISTENING and (now - self._last_short_ts) < 0.12:
                logger.debug("SHORT_PRESS debounced in LISTENING")
                return
            if current == AppMode.LISTENING:
                self._last_short_ts = now
            
            # Публикация события
            logger.debug("SHORT_PRESS: публикуем keyboard.short_press")
            await self.event_bus.publish(
                "keyboard.short_press",
                {
                    "event": event,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
            )
            logger.debug("SHORT_PRESS: опубликовано")

            # В режиме Quartz SHORT_PRESS генерируется вместо RELEASE.
            # Если запись успели начать (после LONG_PRESS), останавливаем её.
            if self._recording_started and self._current_session_id is not None:
                logger.debug("SHORT_PRESS: публикуем voice.recording_stop (для закрытия микрофона)")
                await self.event_bus.publish(
                    "voice.recording_stop",
                    {
                        "source": "keyboard",
                        "timestamp": event.timestamp,
                        "duration": event.duration,
                        "session_id": self._current_session_id,
                    }
                )
                logger.debug("SHORT_PRESS: voice.recording_stop опубликовано")
                self._session_waiting_grpc = True
                self._active_grpc_session_id = self._current_session_id
                logger.debug(
                    "SHORT_PRESS: session_id=%s удерживаем до завершения gRPC",
                    self._current_session_id,
                )

            # Отменяем активный gRPC поток, если он идёт
            logger.debug("SHORT_PRESS: запрашиваем отмену активного gRPC стрима")
            await self.event_bus.publish("grpc.request_cancel", {
                "session_id": self._current_session_id
            })

            # МГНОВЕННО останавливаем воспроизведение через единый канал прерывания
            # Публикуем только если мы реально в PROCESSING, чтобы избежать дублей в LISTENING/SLEEPING
            try:
                current_mode = None
                try:
                    current_mode = self.state_manager.get_current_mode()
                except Exception:
                    current_mode = None
                if current_mode == AppMode.PROCESSING:
                    await self.event_bus.publish("playback.cancelled", {
                        "session_id": self._current_session_id,
                        "reason": "keyboard",
                        "source": "input_processing"
                    })
                    logger.debug("SHORT_PRESS: playback.cancelled опубликовано (PROCESSING)")
            except Exception:
                pass

            # При коротком нажатии: только прерывание (уже выполнено на PRESS) и переход в SLEEPING
            await self.event_bus.publish("mode.request", {
                "target": AppMode.SLEEPING,
                "source": "input_processing"
            })
            logger.info("SHORT_PRESS: запрос на SLEEPING отправлен")

            # Смена режима публикуется централизованно через ApplicationStateManager

            # Прерывание записи (если была)
            self._recording_started = False

            if not self._session_waiting_grpc:
                self._reset_session("short_press_idle")
            else:
                logger.debug("SHORT_PRESS: удерживаем session_id=%s до завершения gRPC", self._current_session_id)
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки short press: {e}",
                context={"where": "input_processing_integration.handle_short_press"}
            )
            
    async def _handle_long_press(self, event: KeyEvent):
        """Обработка длинного нажатия пробела"""
        try:
            logger.debug(f"🔑 LONG_PRESS: {event.duration:.3f}с")
            
            # Публикация события
            logger.debug("LONG_PRESS: публикуем keyboard.long_press")
            await self.event_bus.publish(
                "keyboard.long_press",
                {
                    "event": event,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
            )
            logger.debug("LONG_PRESS: опубликовано")

            # На LONG_PRESS стартуем запись и переходим в LISTENING (push-to-talk)
            if self._current_session_id is None:
                self._current_session_id = event.timestamp or time.monotonic()
            if not self._recording_started:
                await self.event_bus.publish(
                    "voice.recording_start",
                    {
                        "source": "keyboard",
                        "timestamp": event.timestamp,
                        "session_id": self._current_session_id,
                    }
                )
                self._recording_started = True
                logger.debug("LONG_PRESS: voice.recording_start опубликовано")

                # Запрашиваем переход в LISTENING централизованно
                await self.event_bus.publish("mode.request", {
                    "target": AppMode.LISTENING,
                    "source": "input_processing"
                })
                logger.info("LONG_PRESS: запрос на LISTENING отправлен")
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки long press: {e}",
                context={"where": "input_processing_integration.handle_long_press"}
            )
            
    async def _handle_key_release(self, event: KeyEvent):
        """Обработка отпускания пробела"""
        try:
            logger.info(f"🔑 RELEASE EVENT: {event.duration:.3f}с")
            logger.debug(f"RELEASE: session={self._current_session_id}, recognized={self._session_recognized}")
            print(f"🔑 RELEASE EVENT: {event.duration:.3f}с")  # Для отладки
            
            # Публикация события
            logger.debug("RELEASE: публикуем keyboard.release")
            await self.event_bus.publish(
                "keyboard.release",
                {
                    "event": event,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
            )
            logger.debug("RELEASE: keyboard.release опубликовано")
            
            # Останавливаем запись, только если она была начата (после LONG_PRESS)
            if self._recording_started and self._current_session_id is not None:
                logger.debug("RELEASE: публикуем voice.recording_stop")
                await self.event_bus.publish(
                    "voice.recording_stop",
                    {
                        "source": "keyboard",
                        "timestamp": event.timestamp,
                        "duration": event.duration,
                        "session_id": self._current_session_id,
                    }
                )
                logger.debug("RELEASE: voice.recording_stop опубликовано")

            # Переходим в PROCESSING только если запись велась; иначе остаёмся в текущем режиме (обычно SLEEPING)
            if self._recording_started:
                logger.debug("RELEASE: публикуем mode.request(PROCESSING)")
                await self.event_bus.publish("mode.request", {
                    "target": AppMode.PROCESSING,
                    "source": "input_processing"
                })
                logger.info("RELEASE: запрос на PROCESSING отправлен")

            # Смена режима публикуется централизованно через ApplicationStateManager

            was_recording = self._recording_started
            self._recording_started = False

            if was_recording:
                self._session_waiting_grpc = True
                self._active_grpc_session_id = self._current_session_id
                logger.debug("RELEASE: удерживаем session_id=%s до завершения gRPC", self._current_session_id)
            elif self._session_waiting_grpc:
                logger.debug("RELEASE: session_id=%s уже ожидает завершения gRPC", self._current_session_id)
            else:
                self._reset_session("release_no_recording")
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки key release: {e}",
                context={"where": "input_processing_integration.handle_key_release"}
            )
            
            
    # Обработчики внешних событий
    async def _handle_mode_switch(self, event):
        """Обработка смены режима"""
        try:
            # EventBus передает событие как dict
            if isinstance(event, dict):
                mode = event.get("data")
            else:
                mode = getattr(event, "data", None)
            logger.debug(f"🔄 Смена режима: {mode}")
            
            if mode == AppMode.LISTENING:
                # В режиме прослушивания - готовы к записи
                pass
            elif mode == AppMode.SLEEPING:
                # В режиме сна - останавливаем все процессы
                pass
                    
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.LOW,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки mode switch: {e}",
                context={"where": "input_processing_integration.handle_mode_switch"}
            )
    
    # Sync wrapper'ы для callback'ов KeyboardMonitor
    def _sync_handle_press(self, event):
        """Sync wrapper для async _handle_press"""
        try:
            print(f"🔑 SYNC PRESS: {event.timestamp} - ПОЛУЧЕН CALLBACK!")  # Отладка
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                print(f"🔑 DEBUG: Найден running loop, планирую async task")
                future = asyncio.run_coroutine_threadsafe(self._handle_press(event), loop)
                print(f"🔑 DEBUG: Task запланирован: {future}")
            except RuntimeError:
                print(f"🔑 DEBUG: Нет running loop, запускаю напрямую")
                asyncio.run(self._handle_press(event))
        except Exception as e:
            print(f"❌ Ошибка sync_handle_press: {e}")
            import traceback
            traceback.print_exc()
    
    def _sync_handle_short_press(self, event):
        """Sync wrapper для async _handle_short_press"""
        try:
            print(f"🔑 SYNC SHORT: {event.duration:.3f}с")  # Отладка
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._handle_short_press(event), loop)
            else:
                asyncio.run(self._handle_short_press(event))
        except Exception as e:
            print(f"❌ Ошибка sync_handle_short_press: {e}")
    
    def _sync_handle_long_press(self, event):
        """Sync wrapper для async _handle_long_press"""
        try:
            print(f"🔑 SYNC LONG: {event.duration:.3f}с")  # Отладка
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._handle_long_press(event), loop)
            else:
                asyncio.run(self._handle_long_press(event))
        except Exception as e:
            print(f"❌ Ошибка sync_handle_long_press: {e}")
    
    def _sync_handle_key_release(self, event):
        """Sync wrapper для async _handle_key_release"""
        try:
            print(f"🔑 SYNC RELEASE: {event.duration:.3f}с")  # Отладка
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self._handle_key_release(event), loop)
            else:
                asyncio.run(self._handle_key_release(event))
        except Exception as e:
            print(f"❌ Ошибка sync_handle_key_release: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Получение статуса интеграции"""
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "keyboard_monitor": {
                "enabled": self.keyboard_monitor is not None,
                "monitoring": self.keyboard_monitor.is_monitoring if self.keyboard_monitor else False,
                "status": self.keyboard_monitor.get_status() if self.keyboard_monitor else None
            }
        }
