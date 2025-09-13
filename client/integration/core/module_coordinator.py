"""
Координатор модулей - ИНТЕГРАЦИЯ всех существующих и новых модулей
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass

# Импортируем существующие модули
from speech_playback import SequentialSpeechPlayer, PlayerConfig
from audio_device_manager import DeviceManager

# Импортируем новые модули
from input_processing import KeyboardMonitor, SpeechRecognizer, KeyEvent, KeyEventType, SpeechEvent, SpeechState
from interrupt_management import InterruptCoordinator, InterruptDependencies, InterruptEvent, InterruptType, InterruptPriority
from mode_management import ModeController, AppMode, ModeTransition, ModeTransitionType

logger = logging.getLogger(__name__)

@dataclass
class ModuleDependencies:
    """Зависимости между модулями"""
    speech_player: Optional[SequentialSpeechPlayer] = None
    audio_device_manager: Optional[DeviceManager] = None
    grpc_client: Optional[Any] = None
    state_manager: Optional[Any] = None
    screen_capture: Optional[Any] = None

class ModuleCoordinator:
    """Координатор модулей - связывает все существующие и новые модули"""
    
    def __init__(self):
        # Существующие модули (НЕ ТРОГАЕМ)
        self.speech_player = None
        self.audio_device_manager = None
        self.grpc_client = None
        self.state_manager = None
        self.screen_capture = None
        
        # Новые модули
        self.keyboard_monitor = None
        self.speech_recognizer = None
        self.interrupt_coordinator = None
        self.mode_controller = None
        
        # Состояние
        self.is_initialized = False
        self.is_running = False
        
    def initialize(self, dependencies: ModuleDependencies):
        """Инициализирует все модули с существующими зависимостями"""
        try:
            # Сохраняем существующие модули
            self.speech_player = dependencies.speech_player
            self.audio_device_manager = dependencies.audio_device_manager
            self.grpc_client = dependencies.grpc_client
            self.state_manager = dependencies.state_manager
            self.screen_capture = dependencies.screen_capture
            
            # Инициализируем новые модули
            self._initialize_keyboard_monitor()
            self._initialize_speech_recognizer()
            self._initialize_interrupt_coordinator()
            self._initialize_mode_controller()
            
            # Связываем модули
            self._connect_modules()
            
            self.is_initialized = True
            logger.info("✅ Все модули инициализированы с существующими зависимостями")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации модулей: {e}")
            raise
            
    def _initialize_keyboard_monitor(self):
        """Инициализирует мониторинг клавиатуры"""
        from ...input_processing import KeyboardConfig
        
        config = KeyboardConfig(
            key_to_monitor="space",
            short_press_threshold=0.6,
            long_press_threshold=2.0,
            event_cooldown=0.1,
            hold_check_interval=0.05,
            debounce_time=0.1
        )
        
        self.keyboard_monitor = KeyboardMonitor(config)
        self.keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, self._handle_short_press)
        self.keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, self._handle_long_press)
        self.keyboard_monitor.register_callback(KeyEventType.RELEASE, self._handle_key_release)
        
    def _initialize_speech_recognizer(self):
        """Инициализирует распознавание речи"""
        from ...input_processing import SpeechConfig
        
        config = SpeechConfig(
            sample_rate=16000,
            chunk_size=1024,
            channels=1,
            energy_threshold=100,
            dynamic_energy_threshold=True,
            pause_threshold=0.5,
            phrase_threshold=0.3,
            non_speaking_duration=0.3,
            max_duration=30.0,
            auto_start=True
        )
        
        self.speech_recognizer = SpeechRecognizer(config)
        
    def _initialize_interrupt_coordinator(self):
        """Инициализирует координатор прерываний"""
        self.interrupt_coordinator = InterruptCoordinator()
        
        dependencies = InterruptDependencies(
            speech_player=self.speech_player,
            speech_recognizer=self.speech_recognizer,
            grpc_client=self.grpc_client,
            state_manager=self.state_manager
        )
        
        self.interrupt_coordinator.initialize(dependencies)
        
    def _initialize_mode_controller(self):
        """Инициализирует контроллер режимов"""
        self.mode_controller = ModeController()
        
        # Регистрируем режимы с существующими модулями
        from mode_management.modes.speaking_mode import SpeakingMode
        from mode_management.modes.recording_mode import RecordingMode
        
        speaking_mode = SpeakingMode(
            speech_player=self.speech_player,
            audio_device_manager=self.audio_device_manager
        )
        
        recording_mode = RecordingMode(
            speech_recognizer=self.speech_recognizer
        )
        
        self.mode_controller.register_mode_handler(AppMode.SPEAKING, speaking_mode)
        self.mode_controller.register_mode_handler(AppMode.RECORDING, recording_mode)
        
        # Регистрируем переходы между режимами
        self._register_mode_transitions()
        
    def _register_mode_transitions(self):
        """Регистрирует переходы между режимами"""
        # IDLE → LISTENING
        transition = ModeTransition(
            from_mode=AppMode.IDLE,
            to_mode=AppMode.LISTENING,
            transition_type=ModeTransitionType.AUTOMATIC,
            priority=1
        )
        self.mode_controller.register_transition(transition)
        
        # LISTENING → RECORDING (долгое нажатие)
        transition = ModeTransition(
            from_mode=AppMode.LISTENING,
            to_mode=AppMode.RECORDING,
            transition_type=ModeTransitionType.MANUAL,
            priority=1
        )
        self.mode_controller.register_transition(transition)
        
        # SPEAKING → RECORDING (долгое нажатие с прерыванием)
        transition = ModeTransition(
            from_mode=AppMode.SPEAKING,
            to_mode=AppMode.RECORDING,
            transition_type=ModeTransitionType.INTERRUPT,
            priority=1
        )
        self.mode_controller.register_transition(transition)
        
        # RECORDING → PROCESSING (отпускание клавиши)
        transition = ModeTransition(
            from_mode=AppMode.RECORDING,
            to_mode=AppMode.PROCESSING,
            transition_type=ModeTransitionType.AUTOMATIC,
            priority=1
        )
        self.mode_controller.register_transition(transition)
        
        # PROCESSING → IDLE (завершение обработки)
        transition = ModeTransition(
            from_mode=AppMode.PROCESSING,
            to_mode=AppMode.IDLE,
            transition_type=ModeTransitionType.AUTOMATIC,
            priority=1
        )
        self.mode_controller.register_transition(transition)
        
    def _connect_modules(self):
        """Связывает модули между собой"""
        # Регистрируем обработчики прерываний
        from interrupt_management.handlers.speech_interrupt import SpeechInterruptHandler
        from interrupt_management.handlers.recording_interrupt import RecordingInterruptHandler
        
        speech_interrupt_handler = SpeechInterruptHandler(
            speech_player=self.speech_player,
            grpc_client=self.grpc_client
        )
        
        recording_interrupt_handler = RecordingInterruptHandler(
            speech_recognizer=self.speech_recognizer
        )
        
        # Подключаем обработчики
        self.interrupt_coordinator.register_handler(
            InterruptType.SPEECH_STOP,
            speech_interrupt_handler.handle_speech_stop
        )
        
        self.interrupt_coordinator.register_handler(
            InterruptType.RECORDING_STOP,
            recording_interrupt_handler.handle_recording_stop
        )
        
    async def _handle_short_press(self, event: KeyEvent):
        """Обрабатывает короткое нажатие пробела"""
        logger.info("🔑 Короткое нажатие пробела")
        
        # Если речь идет - прерываем через speech_playback
        if self.mode_controller.current_mode == AppMode.SPEAKING:
            interrupt_event = InterruptEvent(
                type=InterruptType.SPEECH_STOP,
                priority=InterruptPriority.HIGH,
                source="keyboard_short_press",
                timestamp=event.timestamp
            )
            await self.interrupt_coordinator.trigger_interrupt(interrupt_event)
            logger.info("🛑 Речь прервана через speech_playback")
            
    async def _handle_long_press(self, event: KeyEvent):
        """Обрабатывает долгое нажатие пробела"""
        logger.info("🔑 Долгое нажатие пробела")
        
        # Прерываем речь если идет
        if self.mode_controller.current_mode == AppMode.SPEAKING:
            interrupt_event = InterruptEvent(
                type=InterruptType.SPEECH_STOP,
                priority=InterruptPriority.HIGH,
                source="keyboard_long_press",
                timestamp=event.timestamp
            )
            await self.interrupt_coordinator.trigger_interrupt(interrupt_event)
            logger.info("🛑 Речь прервана через speech_playback")
            
        # Переключаемся в режим записи
        await self.mode_controller.switch_mode(AppMode.RECORDING)
        
    async def _handle_key_release(self, event: KeyEvent):
        """Обрабатывает отпускание пробела"""
        logger.info("🔑 Отпускание пробела")
        
        # Если записываем - останавливаем запись
        if self.mode_controller.current_mode == AppMode.RECORDING:
            interrupt_event = InterruptEvent(
                type=InterruptType.RECORDING_STOP,
                priority=InterruptPriority.NORMAL,
                source="keyboard_release",
                timestamp=event.timestamp
            )
            await self.interrupt_coordinator.trigger_interrupt(interrupt_event)
            await self.mode_controller.switch_mode(AppMode.PROCESSING)
            logger.info("🛑 Запись остановлена, переключение в режим обработки")
            
    async def start(self):
        """Запускает координатор"""
        if not self.is_initialized:
            raise RuntimeError("Модули не инициализированы")
            
        try:
            # Запускаем мониторинг клавиатуры
            self.keyboard_monitor.start_monitoring()
            self.is_running = True
            logger.info("🚀 Координатор модулей запущен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска координатора: {e}")
            raise
            
    async def stop(self):
        """Останавливает координатор"""
        try:
            if self.keyboard_monitor:
                self.keyboard_monitor.stop_monitoring()
                
            self.is_running = False
            logger.info("🛑 Координатор модулей остановлен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка остановки координатора: {e}")
            
    def get_status(self) -> Dict[str, Any]:
        """Возвращает статус координатора"""
        return {
            "is_initialized": self.is_initialized,
            "is_running": self.is_running,
            "current_mode": self.mode_controller.current_mode.value if self.mode_controller else None,
            "keyboard_monitor": self.keyboard_monitor.get_status() if self.keyboard_monitor else None,
            "speech_recognizer": self.speech_recognizer.get_status() if self.speech_recognizer else None,
            "interrupt_coordinator": self.interrupt_coordinator.get_status() if self.interrupt_coordinator else None,
            "mode_controller": self.mode_controller.get_status() if self.mode_controller else None,
        }
