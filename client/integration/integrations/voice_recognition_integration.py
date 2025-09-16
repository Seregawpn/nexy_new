"""
VoiceRecognitionIntegration - Интеграция распознавания речи с EventBus и ApplicationStateManager
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any

# Импорты из core
from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler, ErrorSeverity, ErrorCategory

# Импорты из модуля
from modules.voice_recognition.core.types import RecognitionConfig, RecognitionResult, RecognitionState
from modules.voice_recognition.core.speech_recognizer import SpeechRecognizer

logger = logging.getLogger(__name__)

@dataclass
class VoiceRecognitionIntegrationConfig:
    """Конфигурация VoiceRecognitionIntegration"""
    # Основные настройки
    enabled: bool = True
    simulation_mode: bool = True  # Для тестирования
    simulation_delay: float = 1.5  # Задержка симуляции в секундах
    simulation_success_rate: float = 0.8  # Процент успешных распознаваний
    
    # Настройки распознавания
    language: str = "en-US"
    timeout: float = 3.0
    phrase_timeout: float = 0.3
    energy_threshold: int = 100
    
    # Настройки микрофона
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1

class VoiceRecognitionIntegration:
    """Интеграция SpeechRecognizer с EventBus и ApplicationStateManager"""
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
        config: Optional[VoiceRecognitionIntegrationConfig] = None,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config or VoiceRecognitionIntegrationConfig()
        
        self._recognizer: Optional[SpeechRecognizer] = None
        self._initialized = False
        self._running = False
        
        # Текущая сессия
        self._current_session_id: Optional[str] = None
        self._recognition_start_time: Optional[float] = None
        
        logger.info("VoiceRecognitionIntegration created")
    
    async def initialize(self) -> bool:
        """Инициализация VoiceRecognitionIntegration"""
        try:
            if not self.config.enabled:
                logger.info("VoiceRecognitionIntegration отключен в конфигурации")
                return True
            
            logger.info("Initializing VoiceRecognitionIntegration...")
            
            # Создаем конфигурацию распознавания
            recognition_config = RecognitionConfig(
                language=self.config.language,
                sample_rate=self.config.sample_rate,
                chunk_size=self.config.chunk_size,
                channels=self.config.channels,
                energy_threshold=self.config.energy_threshold,
                timeout=self.config.timeout,
                phrase_timeout=self.config.phrase_timeout,
                enable_logging=True,
                enable_metrics=True
            )
            
            # Создаем SpeechRecognizer
            self._recognizer = SpeechRecognizer(recognition_config)
            
            # Настраиваем callbacks
            self._recognizer.register_callback(RecognitionState.LISTENING, self._on_listening_start)
            self._recognizer.register_callback(RecognitionState.PROCESSING, self._on_processing_start)
            self._recognizer.register_callback(RecognitionState.COMPLETED, self._on_recognition_complete)
            self._recognizer.register_callback(RecognitionState.ERROR, self._on_recognition_error)
            
            # Подписываемся на события приложения
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.MEDIUM)
            await self.event_bus.subscribe("app.state_changed", self._on_app_state_changed, EventPriority.HIGH)
            
            # Подписываемся на события записи
            await self.event_bus.subscribe("voice.recording_start", self._on_recording_start, EventPriority.HIGH)
            await self.event_bus.subscribe("voice.recording_stop", self._on_recording_stop, EventPriority.HIGH)
            
            self._initialized = True
            logger.info("VoiceRecognitionIntegration initialized successfully")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.INITIALIZATION,
                message=f"Ошибка инициализации VoiceRecognitionIntegration: {e}",
                context={"where": "voice_recognition_integration.initialize"}
            )
            return False
    
    async def start(self) -> bool:
        """Запуск VoiceRecognitionIntegration"""
        try:
            if not self._initialized:
                logger.warning("VoiceRecognitionIntegration не инициализирован")
                return False
            
            if not self.config.enabled:
                logger.info("VoiceRecognitionIntegration отключен")
                return True
            
            # Распознаватель готов к работе
            if self._recognizer:
                logger.info("SpeechRecognizer готов к работе")
            
            self._running = True
            logger.info("VoiceRecognitionIntegration started successfully")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка запуска VoiceRecognitionIntegration: {e}",
                context={"where": "voice_recognition_integration.start"}
            )
            return False
    
    async def stop(self) -> bool:
        """Остановка VoiceRecognitionIntegration"""
        try:
            if self._recognizer:
                # Останавливаем прослушивание если активно
                if self._recognizer.is_listening:
                    await self._recognizer.stop_listening()
                logger.info("SpeechRecognizer остановлен")
            
            self._running = False
            logger.info("VoiceRecognitionIntegration stopped successfully")
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка остановки VoiceRecognitionIntegration: {e}",
                context={"where": "voice_recognition_integration.stop"}
            )
            return False
    
    # Обработчики событий приложения
    async def _on_app_startup(self, event):
        """Обработка запуска приложения"""
        try:
            logger.info("App startup - initializing voice recognition")
            # Дополнительная инициализация при запуске
        except Exception as e:
            logger.error(f"Error handling app startup: {e}")
    
    async def _on_app_shutdown(self, event):
        """Обработка выключения приложения"""
        try:
            logger.info("App shutdown - stopping voice recognition")
            await self.stop()
        except Exception as e:
            logger.error(f"Error handling app shutdown: {e}")
    
    async def _on_app_state_changed(self, event):
        """Обработка изменения состояния приложения"""
        try:
            data = event.get("data", {})
            old_mode = data.get("old_mode")
            new_mode = data.get("new_mode")
            
            if new_mode == AppMode.LISTENING:
                logger.info("App mode changed to LISTENING - voice recognition ready")
            elif new_mode == AppMode.PROCESSING:
                logger.info("App mode changed to PROCESSING - voice recognition processing")
            elif new_mode == AppMode.SLEEPING:
                logger.info("App mode changed to SLEEPING - voice recognition idle")
                
        except Exception as e:
            logger.error(f"Error handling app state change: {e}")
    
    # Обработчики событий записи
    async def _on_recording_start(self, event):
        """Обработка начала записи"""
        try:
            data = event.get("data", {})
            session_id = data.get("session_id")
            source = data.get("source", "unknown")
            
            if source != "keyboard":
                return  # Обрабатываем только события от клавиатуры
            
            logger.info(f"🎤 Начало записи (сессия: {session_id})")
            
            # Сохраняем ID сессии
            self._current_session_id = session_id
            self._recognition_start_time = time.time()
            
            # Если включен режим симуляции, запускаем симуляцию
            if self.config.simulation_mode:
                await self._simulate_recognition()
            else:
                # Реальное распознавание
                if self._recognizer:
                    await self._recognizer.start_listening()
                
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки начала записи: {e}",
                context={"where": "voice_recognition_integration.on_recording_start"}
            )
    
    async def _on_recording_stop(self, event):
        """Обработка остановки записи"""
        try:
            data = event.get("data", {})
            session_id = data.get("session_id")
            source = data.get("source", "unknown")
            
            if source != "keyboard" or session_id != self._current_session_id:
                return  # Обрабатываем только события от клавиатуры для текущей сессии
            
            logger.info(f"🎤 Остановка записи (сессия: {session_id})")
            
            # Останавливаем распознавание
            if self._recognizer and not self.config.simulation_mode:
                await self._recognizer.stop_listening()
            
            # Сбрасываем сессию
            self._current_session_id = None
            self._recognition_start_time = None
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка обработки остановки записи: {e}",
                context={"where": "voice_recognition_integration.on_recording_stop"}
            )
    
    # Симуляция распознавания для тестирования
    async def _simulate_recognition(self):
        """Симуляция распознавания речи"""
        try:
            if not self._current_session_id:
                return
            
            logger.info(f"🎭 Симуляция распознавания (сессия: {self._current_session_id})")
            
            # Ждем указанное время
            await asyncio.sleep(self.config.simulation_delay)
            
            # Проверяем, что сессия еще активна
            if not self._current_session_id:
                logger.info("Сессия отменена, пропускаем симуляцию")
                return
            
            # Определяем успешность по вероятности
            import random
            is_successful = random.random() < self.config.simulation_success_rate
            
            if is_successful:
                # Симуляция успешного распознавания
                result = RecognitionResult(
                    text="Hello, this is a simulated recognition result",
                    confidence=0.85,
                    language=self.config.language,
                    duration=time.time() - (self._recognition_start_time or time.time()),
                    timestamp=time.time()
                )
                
                logger.info(f"✅ Симуляция успешного распознавания: '{result.text}'")
                
                # Публикуем событие успешного распознавания
                await self.event_bus.publish("voice.recognition_completed", {
                    "session_id": self._current_session_id,
                    "text": result.text,
                    "confidence": result.confidence,
                    "language": result.language,
                    "duration": result.duration,
                    "timestamp": result.timestamp
                })
                
            else:
                # Симуляция неуспешного распознавания
                logger.info("❌ Симуляция неуспешного распознавания")
                
                # Публикуем событие неуспешного распознавания
                await self.event_bus.publish("voice.recognition_failed", {
                    "session_id": self._current_session_id,
                    "error": "No speech detected",
                    "timestamp": time.time()
                })
                
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка симуляции распознавания: {e}",
                context={"where": "voice_recognition_integration.simulate_recognition"}
            )
    
    # Callbacks распознавателя
    def _on_listening_start(self, state: RecognitionState):
        """Callback начала прослушивания"""
        logger.info("🎧 Начало прослушивания")
    
    def _on_processing_start(self, state: RecognitionState):
        """Callback начала обработки"""
        logger.info("🔄 Начало обработки аудио")
    
    def _on_recognition_complete(self, result: RecognitionResult):
        """Callback завершения распознавания"""
        try:
            logger.info(f"✅ Распознавание завершено: '{result.text}' (уверенность: {result.confidence})")
            
            # Публикуем событие успешного распознавания
            if self.event_bus and self._current_session_id:
                asyncio.create_task(self.event_bus.publish("voice.recognition_completed", {
                    "session_id": self._current_session_id,
                    "text": result.text,
                    "confidence": result.confidence,
                    "language": result.language,
                    "duration": result.duration,
                    "timestamp": result.timestamp
                }))
                
        except Exception as e:
            logger.error(f"Error handling recognition complete: {e}")
    
    def _on_recognition_error(self, error: str):
        """Callback ошибки распознавания"""
        try:
            logger.error(f"❌ Ошибка распознавания: {error}")
            
            # Публикуем событие ошибки распознавания
            if self.event_bus and self._current_session_id:
                asyncio.create_task(self.event_bus.publish("voice.recognition_failed", {
                    "session_id": self._current_session_id,
                    "error": error,
                    "timestamp": time.time()
                }))
                
        except Exception as e:
            logger.error(f"Error handling recognition error: {e}")
    
    # Методы управления
    def get_status(self) -> Dict[str, Any]:
        """Получить статус VoiceRecognitionIntegration"""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "enabled": self.config.enabled,
            "simulation_mode": self.config.simulation_mode,
            "current_session": self._current_session_id,
            "recognizer_state": self._recognizer.state.value if self._recognizer else "unknown"
        }
    
    async def start_recognition(self, session_id: str) -> bool:
        """Начать распознавание для сессии"""
        try:
            if not self._running or not self._recognizer:
                return False
            
            self._current_session_id = session_id
            self._recognition_start_time = time.time()
            
            if self.config.simulation_mode:
                await self._simulate_recognition()
            else:
                await self._recognizer.start_listening()
            
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка запуска распознавания: {e}",
                context={"where": "voice_recognition_integration.start_recognition"}
            )
            return False
    
    async def stop_recognition(self) -> bool:
        """Остановить распознавание"""
        try:
            if not self._running or not self._recognizer:
                return False
            
            if not self.config.simulation_mode:
                await self._recognizer.stop_listening()
            
            self._current_session_id = None
            self._recognition_start_time = None
            
            return True
            
        except Exception as e:
            await self.error_handler.handle_error(
                severity=ErrorSeverity.MEDIUM,
                category=ErrorCategory.RUNTIME,
                message=f"Ошибка остановки распознавания: {e}",
                context={"where": "voice_recognition_integration.stop_recognition"}
            )
            return False
