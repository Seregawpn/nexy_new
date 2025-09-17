"""
Нативный монитор клавиатуры для macOS через Quartz CGEventTap.

API совместим с KeyboardMonitor: register_callback, set_loop, start_monitoring, stop_monitoring, get_status.
"""

import asyncio
import logging
import threading
import time
from typing import Optional, Callable, Dict, Any

try:
    from Quartz import (
        CGEventTapCreate,
        CGEventTapEnable,
        CFRunLoopAddSource,
        CFRunLoopGetCurrent,
        CFRunLoopGetMain,
        CFRunLoopRunInMode,
        CFRunLoopSourceInvalidate,
        CFMachPortCreateRunLoopSource,
        kCGHIDEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionListenOnly,
        kCGEventKeyDown,
        kCGEventKeyUp,
        kCFRunLoopCommonModes,
        kCFRunLoopDefaultMode,
        CGEventGetIntegerValueField,
        kCGKeyboardEventKeycode,
    )
    QUARTZ_AVAILABLE = True
except Exception as e:  # pragma: no cover
    QUARTZ_AVAILABLE = False

from ..types import KeyEvent, KeyEventType, KeyboardConfig

logger = logging.getLogger(__name__)


class QuartzKeyboardMonitor:
    """Глобальный монитор клавиатуры на macOS через Quartz Event Tap."""

    # Минимальная карта key_to_monitor -> keycode (US). Сейчас нужен только пробел.
    KEYCODES = {
        "space": 49,
        # При необходимости можно расширить: enter(36), esc(53), shift(56/60), ctrl(59/62), alt(58/61)
    }

    def __init__(self, config: KeyboardConfig):
        self.config = config
        self.key_to_monitor = config.key_to_monitor
        self.short_press_threshold = config.short_press_threshold
        self.long_press_threshold = config.long_press_threshold
        self.event_cooldown = config.event_cooldown
        self.hold_check_interval = config.hold_check_interval

        # Состояние
        self.is_monitoring = False
        self.key_pressed = False
        self.press_start_time: Optional[float] = None
        self.last_event_time = 0.0
        self._long_sent = False

        # Потоки
        self.hold_monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.state_lock = threading.RLock()

        # Callbacks
        self.event_callbacks: Dict[KeyEventType, Callable] = {}

        # Async loop для async-колбэков
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # Quartz объекты
        self._tap = None
        self._tap_source = None

        # Доступность
        self.keyboard_available = QUARTZ_AVAILABLE
        if not QUARTZ_AVAILABLE:
            logger.warning("⚠️ Quartz недоступен — нативный монитор клавиатуры отключен")

        # Целевой keycode
        self._target_keycode = self.KEYCODES.get(self.key_to_monitor, None)
        if self._target_keycode is None:
            logger.warning(f"⚠️ Неподдерживаемая клавиша для Quartz: {self.key_to_monitor}")
            self.keyboard_available = False

    def register_callback(self, event_type, callback: Callable):
        if isinstance(event_type, str):
            try:
                event_type = KeyEventType(event_type)
            except ValueError:
                logger.warning(f"⚠️ Неизвестный тип события: {event_type}")
                return
        self.event_callbacks[event_type] = callback
        logger.debug(f"QuartzMonitor: callback зарегистрирован для {event_type}")

    def set_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        logger.debug("QuartzMonitor: установлен event loop для async-колбэков")

    def start_monitoring(self) -> bool:
        if not self.keyboard_available:
            logger.warning("⚠️ Клавиатурный Quartz-монитор недоступен")
            return False
        if self.is_monitoring:
            logger.warning("⚠️ Мониторинг уже запущен")
            return False

        try:
            # Создаем Event Tap
            def _tap_callback(proxy, event_type, event, refcon):
                try:
                    if event_type not in (kCGEventKeyDown, kCGEventKeyUp):
                        return event

                    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                    if keycode != self._target_keycode:
                        return event

                    now = time.time()

                    # cooldown
                    if now - self.last_event_time < self.event_cooldown:
                        return event

                    if event_type == kCGEventKeyDown:
                        logger.debug("Quartz tap: keyDown detected for target key")
                        with self.state_lock:
                            if self.key_pressed:
                                # игнорируем авто-повтор
                                return event
                            self.key_pressed = True
                            self.press_start_time = now
                            self._long_sent = False

                        # PRESS
                        ev = KeyEvent(
                            key=self.key_to_monitor,
                            event_type=KeyEventType.PRESS,
                            timestamp=now,
                        )
                        self._trigger_event(KeyEventType.PRESS, 0.0, ev)
                    else:  # kCGEventKeyUp
                        logger.debug("Quartz tap: keyUp detected for target key")
                        with self.state_lock:
                            if not self.key_pressed:
                                return event
                            duration = now - (self.press_start_time or now)
                            self.key_pressed = False
                            self.press_start_time = None
                            self.last_event_time = now
                            # если уже отправили LONG_PRESS — трактуем как RELEASE
                            event_type_out = (
                                KeyEventType.SHORT_PRESS if duration < self.short_press_threshold else KeyEventType.RELEASE
                            )

                        ev = KeyEvent(
                            key=self.key_to_monitor,
                            event_type=event_type_out,
                            timestamp=now,
                            duration=duration,
                        )
                        self._trigger_event(event_type_out, duration, ev)

                    return event
                except Exception as e:
                    logger.error(f"❌ Ошибка в tap callback: {e}")
                    return event

            self._tap = CGEventTapCreate(
                kCGHIDEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionListenOnly,
                (1 << kCGEventKeyDown) | (1 << kCGEventKeyUp),
                _tap_callback,
                None,
            )

            if not self._tap:
                logger.error("❌ Не удалось создать CGEventTap — проверьте Accessibility/Input Monitoring")
                self.keyboard_available = False
                return False

            self._tap_source = CFMachPortCreateRunLoopSource(None, self._tap, 0)

            # Добавляем в главный run loop (AppKit)
            # Важно: сохранить ссылку на callback, иначе он может быть собран GC
            self._tap_callback = _tap_callback  # type: ignore[attr-defined]
            CFRunLoopAddSource(CFRunLoopGetMain(), self._tap_source, kCFRunLoopDefaultMode)
            CGEventTapEnable(self._tap, True)
            logger.info(f"QuartzMonitor: CGEventTap включен для keycode={self._target_keycode}")

            # Запускаем поток мониторинга удержания (для long press)
            self.stop_event.clear()
            self.hold_monitor_thread = threading.Thread(
                target=self._run_hold_monitor,
                name="QuartzHoldMonitor",
                daemon=True,
            )
            self.hold_monitor_thread.start()

            self.is_monitoring = True
            logger.info("🎹 Quartz-монитор клавиатуры запущен")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка запуска Quartz-монитора: {e}")
            self.is_monitoring = False
            return False

    def stop_monitoring(self):
        if not self.is_monitoring:
            return
        try:
            self.is_monitoring = False
            self.stop_event.set()
            if self.hold_monitor_thread and self.hold_monitor_thread.is_alive():
                self.hold_monitor_thread.join(timeout=2.0)

            if self._tap_source:
                try:
                    CFRunLoopSourceInvalidate(self._tap_source)
                except Exception:
                    pass
                self._tap_source = None

            if self._tap:
                try:
                    CGEventTapEnable(self._tap, False)
                except Exception:
                    pass
                self._tap = None

            logger.info("🛑 Quartz-монитор клавиатуры остановлен")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки Quartz-монитора: {e}")

    def _run_hold_monitor(self):
        while not self.stop_event.is_set():
            try:
                with self.state_lock:
                    if self.key_pressed and self.press_start_time:
                        duration = time.time() - self.press_start_time
                        if not self._long_sent and duration >= self.long_press_threshold:
                            ev = KeyEvent(
                                key=self.key_to_monitor,
                                event_type=KeyEventType.LONG_PRESS,
                                timestamp=time.time(),
                                duration=duration,
                            )
                            self._trigger_event(KeyEventType.LONG_PRESS, duration, ev)
                            self._long_sent = True
                time.sleep(self.hold_check_interval)
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторе удержания: {e}")
                time.sleep(0.1)

    def _trigger_event(self, event_type: KeyEventType, duration: float, event: Optional[KeyEvent] = None):
        try:
            callback = self.event_callbacks.get(event_type)
            if not callback:
                return
            if event is None:
                event = KeyEvent(
                    key=self.key_to_monitor,
                    event_type=event_type,
                    timestamp=time.time(),
                    duration=duration,
                )

            threading.Thread(target=lambda: self._run_callback(callback, event), daemon=True).start()
            logger.debug(f"QuartzMonitor: _trigger_event {event_type.value}, duration={duration:.3f}")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска события: {e}")

    def _run_callback(self, callback: Callable, event: KeyEvent):
        try:
            import inspect
            if inspect.iscoroutinefunction(callback):
                # Выполняем корутину напрямую в отдельном временном loop
                # Это гарантирует выполнение даже если основной loop заблокирован rumps
                try:
                    asyncio.run(callback(event))
                except RuntimeError:
                    # На случай конфликтов с текущим loop используем thread-safe постинг
                    if self._loop:
                        asyncio.run_coroutine_threadsafe(callback(event), self._loop)
                    else:
                        raise
            else:
                callback(event)
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения callback: {e}")

    def get_status(self) -> Dict[str, Any]:
        with self.state_lock:
            return {
                "is_monitoring": self.is_monitoring,
                "key_pressed": self.key_pressed,
                "keyboard_available": self.keyboard_available,
                "fallback_mode": False,
                "config": {
                    "key": self.key_to_monitor,
                    "short_press_threshold": self.short_press_threshold,
                    "long_press_threshold": self.long_press_threshold,
                },
                "callbacks_registered": len(self.event_callbacks),
                "backend": "quartz",
            }
