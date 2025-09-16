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
from core.event_bus import EventBus, EventPriority
from core.state_manager import ApplicationStateManager, AppMode
from core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

logger = logging.getLogger(__name__)

@dataclass
class InputProcessingConfig:
    """Конфигурация интеграции input_processing (клавиатура)"""
    keyboard_config: KeyboardConfig
    enable_keyboard_monitoring: bool = True
    auto_start: bool = True

class InputProcessingIntegration:
    """Интеграция модуля input_processing"""
    
    def __init__(self, event_bus: EventBus, state_manager: ApplicationStateManager, 
                 error_handler: ErrorHandler, config: InputProcessingConfig):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config
        
        # Компоненты
        self.keyboard_monitor: Optional[KeyboardMonitor] = None
        
        # Состояние
        self.is_initialized = False
        self.is_running = False
        self._current_session_id: Optional[float] = None
        self._session_recognized: bool = False
        
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
            self.keyboard_monitor = KeyboardMonitor(self.config.keyboard_config)
            
            # Регистрация обработчиков
            self.keyboard_monitor.register_callback(
                KeyEventType.PRESS,
                self._handle_press
            )
            self.keyboard_monitor.register_callback(
                KeyEventType.SHORT_PRESS, 
                self._handle_short_press
            )
            self.keyboard_monitor.register_callback(
                KeyEventType.LONG_PRESS, 
                self._handle_long_press
            )
            self.keyboard_monitor.register_callback(
                KeyEventType.RELEASE, 
                self._handle_key_release
            )
            
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
        """Начало удержания: включаем запись и переводим в LISTENING"""
        try:
            # Создаем сессию и сбрасываем флаг распознавания
            self._current_session_id = event.timestamp or time.monotonic()
            self._session_recognized = False
            # Публикуем старт записи
            await self.event_bus.publish(
                "voice.recording_start",
                {
                    "source": "keyboard",
                    "timestamp": event.timestamp,
                    "session_id": self._current_session_id,
                }
            )
            
            # Переключаем режим в LISTENING
            if hasattr(self.state_manager, 'set_mode'):
                if asyncio.iscoroutinefunction(self.state_manager.set_mode):
                    await self.state_manager.set_mode(AppMode.LISTENING)
                else:
                    self.state_manager.set_mode(AppMode.LISTENING)
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
        
    async def start(self) -> bool:
        """Запуск input_processing"""
        try:
            if not self.is_initialized:
                logger.warning("⚠️ input_processing не инициализирован")
                return False
                
            # Запуск мониторинга клавиатуры
            if self.keyboard_monitor:
                # Передаем основной event loop для корректной работы async колбэков
                import asyncio
                self.keyboard_monitor.set_loop(asyncio.get_running_loop())
                self.keyboard_monitor.start_monitoring()
                logger.info("🎹 Мониторинг клавиатуры запущен")
                
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
            logger.debug(f"🔑 Короткое нажатие: {event.duration:.3f}с")
            
            # Публикация события
            await self.event_bus.publish(
                "keyboard.short_press",
                {
                    "event": event,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
            )
            
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
            logger.debug(f"🔑 Длинное нажатие: {event.duration:.3f}с")
            
            # Публикация события
            await self.event_bus.publish(
                "keyboard.long_press",
                {
                    "event": event,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
            )
            
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
            logger.debug(f"🔑 Отпускание: {event.duration:.3f}с")
            
            # Публикация события
            await self.event_bus.publish(
                "keyboard.release",
                {
                    "event": event,
                    "timestamp": event.timestamp,
                    "duration": event.duration
                }
            )
            
            # Останавливаем запись
            await self.event_bus.publish(
                "voice.recording_stop",
                {
                    "source": "keyboard",
                    "timestamp": event.timestamp,
                    "duration": event.duration,
                    "session_id": self._current_session_id,
                }
            )

            # Мгновенное решение на отпускании: используем флаг распознавания текущей сессии
            recognized = bool(self._session_recognized)

            # Переключаем состояние в зависимости от результата
            if hasattr(self.state_manager, 'set_mode'):
                if recognized:
                    if asyncio.iscoroutinefunction(self.state_manager.set_mode):
                        await self.state_manager.set_mode(AppMode.PROCESSING)
                    else:
                        self.state_manager.set_mode(AppMode.PROCESSING)
                else:
                    if asyncio.iscoroutinefunction(self.state_manager.set_mode):
                        await self.state_manager.set_mode(AppMode.SLEEPING)
                    else:
                        self.state_manager.set_mode(AppMode.SLEEPING)

            # Сбрасываем сессию
            self._current_session_id = None
            self._session_recognized = False
            
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
            mode = event.data
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
