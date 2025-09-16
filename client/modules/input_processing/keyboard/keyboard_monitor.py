"""
Мониторинг клавиатуры - рефакторинг из improved_input_handler.py
"""

import asyncio
import threading
import time
import logging
from typing import Optional, Callable, Dict, Any

from .types import KeyEvent, KeyEventType, KeyboardConfig

logger = logging.getLogger(__name__)

class KeyboardMonitor:
    """Мониторинг клавиатуры с поддержкой различных типов нажатий"""
    
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
        self.press_start_time = None
        self.last_event_time = 0
        
        # Threading
        self.monitor_thread = None
        self.hold_monitor_thread = None
        self.stop_event = threading.Event()
        self.state_lock = threading.RLock()
        
        # Callbacks
        self.event_callbacks: Dict[KeyEventType, Callable] = {}
        
        # Event loop для async колбэков
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Fallback режим
        self.fallback_mode = False
        self.keyboard_available = True
        
        # Инициализируем клавиатуру
        self._init_keyboard()
    
    def _init_keyboard(self):
        """Инициализирует клавиатуру"""
        try:
            import pynput.keyboard as keyboard
            self.keyboard = keyboard
            self.keyboard_available = True
            logger.info("✅ Клавиатура инициализирована")
        except ImportError as e:
            logger.warning(f"⚠️ pynput недоступен: {e}")
            self.keyboard_available = False
            self.fallback_mode = True
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации клавиатуры: {e}")
            self.keyboard_available = False
    
    def start_monitoring(self):
        """Начинает мониторинг клавиатуры"""
        if not self.keyboard_available:
            logger.warning("⚠️ Клавиатура недоступна, мониторинг не запущен")
            return False
            
        if self.is_monitoring:
            logger.warning("⚠️ Мониторинг уже запущен")
            return False
            
        try:
            self.is_monitoring = True
            self.stop_event.clear()
            
            # Запускаем поток мониторинга
            self.monitor_thread = threading.Thread(
                target=self._run_keyboard_listener,
                name="KeyboardMonitor",
                daemon=True
            )
            self.monitor_thread.start()
            
            # Запускаем поток мониторинга удержания
            self.hold_monitor_thread = threading.Thread(
                target=self._run_hold_monitor,
                name="HoldMonitor",
                daemon=True
            )
            self.hold_monitor_thread.start()
            
            logger.info("🎹 Мониторинг клавиатуры запущен")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга: {e}")
            self.is_monitoring = False
            return False
    
    def stop_monitoring(self):
        """Останавливает мониторинг клавиатуры"""
        if not self.is_monitoring:
            return
            
        try:
            self.is_monitoring = False
            self.stop_event.set()
            
            # Ждем завершения потоков
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=2.0)
                
            if self.hold_monitor_thread and self.hold_monitor_thread.is_alive():
                self.hold_monitor_thread.join(timeout=2.0)
                
            logger.info("🛑 Мониторинг клавиатуры остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки мониторинга: {e}")
    
    def register_callback(self, event_type, callback: Callable):
        """Регистрирует callback для типа события"""
        # Поддерживаем как KeyEventType, так и строки
        if isinstance(event_type, str):
            # Конвертируем строку в KeyEventType
            try:
                event_type = KeyEventType(event_type)
            except ValueError:
                logger.warning(f"⚠️ Неизвестный тип события: {event_type}")
                return
                
        self.event_callbacks[event_type] = callback
        logger.debug(f"📝 Зарегистрирован callback для {event_type.value}")
    
    def set_loop(self, loop: asyncio.AbstractEventLoop):
        """Устанавливает event loop для async колбэков"""
        self._loop = loop
        logger.debug("🔄 Event loop установлен для KeyboardMonitor")
    
    def _run_keyboard_listener(self):
        """Запускает listener клавиатуры"""
        try:
            with self.keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            ) as listener:
                listener.join()
        except Exception as e:
            logger.error(f"❌ Ошибка в listener клавиатуры: {e}")
    
    def _run_hold_monitor(self):
        """Мониторит удержание клавиши"""
        while not self.stop_event.is_set():
            try:
                with self.state_lock:
                    if self.key_pressed and self.press_start_time:
                        duration = time.time() - self.press_start_time
                        
                        # Проверяем долгое нажатие
                        if duration >= self.long_press_threshold:
                            self._trigger_event(KeyEventType.LONG_PRESS, duration)
                            self.press_start_time = None  # Сбрасываем, чтобы не повторять
                            
                time.sleep(self.hold_check_interval)
                
            except Exception as e:
                logger.error(f"❌ Ошибка в мониторе удержания: {e}")
                time.sleep(0.1)
    
    def _on_key_press(self, key):
        """Обработка нажатия клавиши"""
        try:
            current_time = time.time()
            
            # Проверяем cooldown
            if current_time - self.last_event_time < self.event_cooldown:
                return
                
            # Проверяем, что это наша клавиша
            if not self._is_target_key(key):
                return
                
            with self.state_lock:
                # Если клавиша уже нажата, игнорируем
                if self.key_pressed:
                    return
                    
                self.key_pressed = True
                self.press_start_time = current_time
                
            # Создаем событие нажатия
            event = KeyEvent(
                key=self._key_to_string(key),
                event_type=KeyEventType.PRESS,
                timestamp=current_time
            )
            
            self._trigger_event(KeyEventType.PRESS, 0.0, event)
            logger.debug(f"🔑 Клавиша нажата: {self._key_to_string(key)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки нажатия: {e}")
    
    def _on_key_release(self, key):
        """Обработка отпускания клавиши"""
        try:
            current_time = time.time()
            
            # Проверяем, что это наша клавиша
            if not self._is_target_key(key):
                return
                
            with self.state_lock:
                if not self.key_pressed:
                    return
                    
                duration = current_time - self.press_start_time if self.press_start_time else 0
                
                # Определяем тип события
                if duration < self.short_press_threshold:
                    event_type = KeyEventType.SHORT_PRESS
                else:
                    event_type = KeyEventType.RELEASE
                
                # Создаем событие
                event = KeyEvent(
                    key=self._key_to_string(key),
                    event_type=event_type,
                    timestamp=current_time,
                    duration=duration
                )
                
                self._trigger_event(event_type, duration, event)
                
                # Сбрасываем состояние
                self.key_pressed = False
                self.press_start_time = None
                self.last_event_time = current_time
                
            logger.debug(f"🔑 Клавиша отпущена: {self._key_to_string(key)} (длительность: {duration:.3f}s)")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки отпускания: {e}")
    
    def _is_target_key(self, key) -> bool:
        """Проверяет, является ли клавиша целевой"""
        try:
            if not self.keyboard_available:
                return False
                
            if self.key_to_monitor == 'space':
                return key == self.keyboard.Key.space
            elif self.key_to_monitor == 'ctrl':
                return key == self.keyboard.Key.ctrl
            elif self.key_to_monitor == 'alt':
                return key == self.keyboard.Key.alt
            elif self.key_to_monitor == 'shift':
                return key == self.keyboard.Key.shift
            elif self.key_to_monitor == 'enter':
                return key == self.keyboard.Key.enter
            elif self.key_to_monitor == 'esc':
                return key == self.keyboard.Key.esc
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки клавиши: {e}")
            return False
    
    def _key_to_string(self, key) -> str:
        """Преобразует клавишу в строку"""
        try:
            if not self.keyboard_available:
                return "unknown"
                
            if hasattr(key, 'char') and key.char:
                return key.char
            elif hasattr(key, 'name'):
                return key.name
            else:
                return str(key)
                
        except Exception as e:
            logger.error(f"❌ Ошибка преобразования клавиши: {e}")
            return "unknown"
    
    def _trigger_event(self, event_type: KeyEventType, duration: float, event: KeyEvent = None):
        """Запускает событие"""
        try:
            callback = self.event_callbacks.get(event_type)
            if callback:
                if event is None:
                    event = KeyEvent(
                        key=self.key_to_monitor,
                        event_type=event_type,
                        timestamp=time.time(),
                        duration=duration
                    )
                
                # Запускаем callback в отдельном потоке
                threading.Thread(
                    target=lambda: self._run_callback(callback, event),
                    daemon=True
                ).start()
                
        except Exception as e:
            logger.error(f"❌ Ошибка запуска события: {e}")
    
    def _run_callback(self, callback, event):
        """Запуск callback с правильной обработкой async/sync функций"""
        try:
            import inspect
            
            # Проверяем, является ли callback корутиной
            if inspect.iscoroutinefunction(callback):
                # Если это корутина, планируем в основной event loop
                if self._loop and self._loop.is_running():
                    asyncio.run_coroutine_threadsafe(callback(event), self._loop)
                else:
                    # Fallback - создаем новый event loop
                    asyncio.run(callback(event))
            else:
                # Если это обычная функция, вызываем напрямую
                callback(event)
                
        except Exception as e:
            logger.error(f"❌ Ошибка выполнения callback: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус мониторинга"""
        with self.state_lock:
            return {
                "is_monitoring": self.is_monitoring,
                "key_pressed": self.key_pressed,
                "keyboard_available": self.keyboard_available,
                "fallback_mode": self.fallback_mode,
                "config": {
                    "key": self.key_to_monitor,
                    "short_press_threshold": self.short_press_threshold,
                    "long_press_threshold": self.long_press_threshold,
                },
                "callbacks_registered": len(self.event_callbacks)
            }
