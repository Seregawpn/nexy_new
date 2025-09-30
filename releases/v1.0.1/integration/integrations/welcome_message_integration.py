"""
WelcomeMessageIntegration — интеграция модуля приветствия с EventBus

Назначение:
- Воспроизводит приветственное сообщение при запуске приложения
- Поддерживает предзаписанное аудио и TTS fallback
- Интегрируется с SpeechPlaybackIntegration для воспроизведения
"""

import asyncio
import logging
from typing import Optional, Dict, Any
import numpy as np

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

# Импорт модуля приветствия
from modules.welcome_message.core.welcome_player import WelcomePlayer
from modules.welcome_message.core.types import WelcomeConfig, WelcomeResult
from modules.welcome_message.config.welcome_config import WelcomeConfigLoader

# Импорт конфигурации
from config.unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)


class WelcomeMessageIntegration:
    """Интеграция модуля приветствия с EventBus"""
    
    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        
        # Загружаем конфигурацию
        try:
            unified_config = UnifiedConfigLoader()
            config_loader = WelcomeConfigLoader.from_unified_config(unified_config)
            self.config = config_loader.load_config()
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка загрузки конфигурации: {e}")
            self.config = WelcomeConfig()
        
        # Создаем плеер приветствия
        self.welcome_player = WelcomePlayer(self.config)
        
        # Настраиваем коллбеки
        self.welcome_player.set_callbacks(
            on_started=self._on_welcome_started,
            on_completed=self._on_welcome_completed,
            on_error=self._on_welcome_error
        )
        
        self._initialized = False
        self._running = False
    
    async def initialize(self) -> bool:
        """Инициализация интеграции"""
        try:
            logger.info("🔧 [WELCOME_INTEGRATION] Инициализация...")
            
            # Подписываемся на события
            await self.event_bus.subscribe("app.startup", self._on_app_startup, EventPriority.MEDIUM)
            
            self._initialized = True
            logger.info("✅ [WELCOME_INTEGRATION] Инициализирован")
            return True
            
        except Exception as e:
            await self._handle_error(e, where="welcome.initialize")
            return False
    
    async def start(self) -> bool:
        """Запуск интеграции"""
        if not self._initialized:
            logger.error("❌ [WELCOME_INTEGRATION] Не инициализирован")
            return False
        
        self._running = True
        logger.info("✅ [WELCOME_INTEGRATION] Запущен")
        return True
    
    async def stop(self) -> bool:
        """Остановка интеграции"""
        try:
            self._running = False
            logger.info("✅ [WELCOME_INTEGRATION] Остановлен")
            return True
        except Exception as e:
            await self._handle_error(e, where="welcome.stop", severity="warning")
            return False
    
    async def _on_app_startup(self, event):
        """Обработка события запуска приложения"""
        try:
            if not self.config.enabled:
                logger.info("🔇 [WELCOME_INTEGRATION] Приветствие отключено в конфигурации")
                return
            
            logger.info("🚀 [WELCOME_INTEGRATION] Обработка запуска приложения")
            
            # Небольшая задержка для полной инициализации системы
            if self.config.delay_sec > 0:
                await asyncio.sleep(self.config.delay_sec)
            
            # Воспроизводим приветствие
            await self._play_welcome_message()
            
        except Exception as e:
            await self._handle_error(e, where="welcome.on_app_startup", severity="warning")
    
    async def _play_welcome_message(self):
        """Воспроизводит приветственное сообщение"""
        try:
            logger.info("🎵 [WELCOME_INTEGRATION] Начинаю воспроизведение приветствия")
            
            # Воспроизводим через плеер
            result = await self.welcome_player.play_welcome()
            
            if result.success:
                logger.info(f"✅ [WELCOME_INTEGRATION] Приветствие воспроизведено: {result.method}, {result.duration_sec:.1f}s")
            else:
                logger.warning(f"⚠️ [WELCOME_INTEGRATION] Приветствие не удалось: {result.error}")
            
        except Exception as e:
            await self._handle_error(e, where="welcome.play_message", severity="warning")
    
    def _on_welcome_started(self):
        """Коллбек начала воспроизведения приветствия"""
        try:
            logger.info("🎵 [WELCOME_INTEGRATION] Приветствие началось")
            # Публикуем событие начала
            asyncio.create_task(self.event_bus.publish("welcome.started", {
                "text": self.config.text,
                "method": "prerecorded"  # Будет обновлено в _on_welcome_completed
            }))
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _on_welcome_started: {e}")
    
    def _on_welcome_completed(self, result: WelcomeResult):
        """Коллбек завершения воспроизведения приветствия"""
        try:
            logger.info(f"🎵 [WELCOME_INTEGRATION] Приветствие завершено: {result.method}, success={result.success}")
            
            # Публикуем событие завершения
            asyncio.create_task(self.event_bus.publish("welcome.completed", {
                "success": result.success,
                "method": result.method,
                "duration_sec": result.duration_sec,
                "error": result.error,
                "metadata": result.metadata or {}
            }))
            
            # Если есть аудио данные, отправляем их в SpeechPlaybackIntegration
            if result.success and result.method in ["prerecorded", "tts"]:
                audio_data = self.welcome_player.get_audio_data()
                if audio_data is not None:
                    asyncio.create_task(self._send_audio_to_playback(audio_data))
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _on_welcome_completed: {e}")
    
    def _on_welcome_error(self, error: str):
        """Коллбек ошибки воспроизведения приветствия"""
        try:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка приветствия: {error}")
            
            # Публикуем событие ошибки
            asyncio.create_task(self.event_bus.publish("welcome.failed", {
                "error": error,
                "text": self.config.text
            }))
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка в _on_welcome_error: {e}")
    
    async def _send_audio_to_playback(self, audio_data: np.ndarray):
        """Отправляет аудио данные в SpeechPlaybackIntegration для воспроизведения"""
        try:
            logger.info(f"🎵 [WELCOME_INTEGRATION] Отправляю аудио в SpeechPlaybackIntegration: {len(audio_data)} сэмплов")
            
            # ОТЛАДКА: Проверяем формат данных
            logger.info(f"🔍 [WELCOME_INTEGRATION] Формат данных: dtype={audio_data.dtype}, shape={audio_data.shape}")
            logger.info(f"🔍 [WELCOME_INTEGRATION] Диапазон: min={audio_data.min()}, max={audio_data.max()}")
            
            # ✅ ПРАВИЛЬНО: Передаем numpy массив напрямую в плеер
            # БЕЗ конвертации в bytes - плеер сам разберется с форматом
            await self.event_bus.publish("playback.raw_audio", {
                "audio_data": audio_data,  # numpy array
                "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "dtype": "int16",  # для информации
                "priority": 5,  # Высокий приоритет для приветствия
                "pattern": "welcome_message"
            })
            
            logger.info("✅ [WELCOME_INTEGRATION] Аудио отправлено в SpeechPlaybackIntegration")
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_INTEGRATION] Ошибка отправки аудио: {e}")
    
    async def _handle_error(self, e: Exception, *, where: str, severity: str = "error"):
        """Обработка ошибок"""
        if hasattr(self.error_handler, 'handle'):
            await self.error_handler.handle(
                error=e,
                category="welcome_message",
                severity=severity,
                context={"where": where}
            )
        else:
            logger.error(f"Welcome message error at {where}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус интеграции"""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "config": {
                "enabled": self.config.enabled,
                "text": self.config.text,
                "audio_file": self.config.audio_file,
                "fallback_to_tts": self.config.fallback_to_tts,
                "delay_sec": self.config.delay_sec
            },
            "player_state": self.welcome_player.state.value if hasattr(self.welcome_player, 'state') else "unknown"
        }
