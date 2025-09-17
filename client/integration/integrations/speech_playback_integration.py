"""
SpeechPlaybackIntegration — интеграция модуля последовательного воспроизведения с EventBus

Слушает gRPC-ответы (`grpc.response.audio`, `grpc.request_completed|failed`) и проигрывает аудио-чанки.
Поддерживает отмену через `keyboard.short_press`/`interrupt.request`.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any

import numpy as np

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler

from modules.speech_playback.core.player import SequentialSpeechPlayer, PlayerConfig

logger = logging.getLogger(__name__)


@dataclass
class SpeechPlaybackIntegrationConfig:
    sample_rate: int = 48000
    channels: int = 1
    dtype: str = 'int16'
    buffer_size: int = 512
    max_memory_mb: int = 256
    auto_device_selection: bool = True


class SpeechPlaybackIntegration:
    """Интеграция SequentialSpeechPlayer с EventBus"""

    def __init__(
        self,
        event_bus: EventBus,
        state_manager: ApplicationStateManager,
        error_handler: ErrorHandler,
        config: Optional[SpeechPlaybackIntegrationConfig] = None,
    ):
        self.event_bus = event_bus
        self.state_manager = state_manager
        self.error_handler = error_handler
        self.config = config or SpeechPlaybackIntegrationConfig()

        self._player: Optional[SequentialSpeechPlayer] = None
        self._initialized = False
        self._running = False
        self._had_audio_for_session: Dict[Any, bool] = {}

    async def initialize(self) -> bool:
        try:
            # Ленивая инициализация плеера — создаём объект сразу, инициализацию сделаем при первом чанке
            pc = PlayerConfig(
                sample_rate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                buffer_size=self.config.buffer_size,
                max_memory_mb=self.config.max_memory_mb,
                auto_device_selection=self.config.auto_device_selection,
            )
            self._player = SequentialSpeechPlayer(pc)

            # Подписки
            await self.event_bus.subscribe("grpc.response.audio", self._on_audio_chunk, EventPriority.HIGH)
            await self.event_bus.subscribe("grpc.request_completed", self._on_grpc_completed, EventPriority.HIGH)
            await self.event_bus.subscribe("grpc.request_failed", self._on_grpc_failed, EventPriority.HIGH)
            await self.event_bus.subscribe("keyboard.short_press", self._on_interrupt, EventPriority.CRITICAL)
            await self.event_bus.subscribe("interrupt.request", self._on_interrupt, EventPriority.CRITICAL)
            await self.event_bus.subscribe("app.shutdown", self._on_app_shutdown, EventPriority.HIGH)

            self._initialized = True
            logger.info("SpeechPlaybackIntegration initialized")
            return True
        except Exception as e:
            await self._handle_error(e, where="speech.initialize")
            return False

    async def start(self) -> bool:
        if not self._initialized:
            logger.error("SpeechPlaybackIntegration not initialized")
            return False
        self._running = True
        return True

    async def stop(self) -> bool:
        try:
            if self._player:
                try:
                    self._player.stop_playback()
                    self._player.shutdown()
                except Exception:
                    pass
            self._running = False
            return True
        except Exception as e:
            await self._handle_error(e, where="speech.stop", severity="warning")
            return False

    # -------- Event Handlers --------
    async def _on_audio_chunk(self, event):
        try:
            data = (event or {}).get("data", {})
            sid = data.get("session_id")
            audio_bytes: bytes = data.get("bytes") or b""
            dtype: str = (data.get("dtype") or 'int16').lower()
            shape = data.get("shape") or []
            if not audio_bytes:
                return

            # Инициализация плеера при первом чанке
            if self._player and not self._player.state_manager.is_playing and not self._player.state_manager.is_paused:
                if not self._player.initialize():
                    await self._handle_error(Exception("player_init_failed"), where="speech.player_init")
                    return

            # Декодирование в numpy
            try:
                np_dtype = np.int16 if dtype in ('int16', 'short') else (np.float32 if dtype in ('float32', 'float') else np.int16)
                arr = np.frombuffer(audio_bytes, dtype=np_dtype)
                if shape and len(shape) > 0:
                    try:
                        arr = arr.reshape(shape)
                    except Exception:
                        pass
            except Exception as e:
                await self._handle_error(e, where="speech.decode_audio", severity="warning")
                return

            # Добавляем чанк и запускаем/возобновляем воспроизведение
            try:
                if self._player:
                    self._player.add_audio_data(arr, priority=0, metadata={"session_id": sid})
                    if not self._player.state_manager.is_playing:
                        if not self._player.start_playback():
                            await self._handle_error(Exception("start_failed"), where="speech.start_playback")
                            return
                        await self.event_bus.publish("playback.started", {"session_id": sid})
                    elif self._player.state_manager.is_paused:
                        self._player.resume_playback()
                self._had_audio_for_session[sid] = True
            except Exception as e:
                await self._handle_error(e, where="speech.add_chunk")

        except Exception as e:
            await self._handle_error(e, where="speech.on_audio_chunk", severity="warning")

    async def _on_grpc_completed(self, event):
        try:
            data = (event or {}).get("data", {})
            sid = data.get("session_id")
            # Даем плееру доиграть буфер асинхронно
            async def _drain_and_stop():
                try:
                    if self._player:
                        # ожидаем опустошения буфера в отдельном потоке
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, self._player.wait_for_completion, 10.0)
                        self._player.stop_playback()
                    await self.event_bus.publish("playback.completed", {"session_id": sid})
                    # Возвращаем приложение в SLEEPING
                    try:
                        await self.state_manager.set_mode(AppMode.SLEEPING)
                    except Exception:
                        pass
                except Exception as e:
                    await self._handle_error(e, where="speech.drain_stop", severity="warning")
            asyncio.create_task(_drain_and_stop())
        except Exception as e:
            await self._handle_error(e, where="speech.on_grpc_completed", severity="warning")

    async def _on_grpc_failed(self, event):
        try:
            data = (event or {}).get("data", {})
            sid = data.get("session_id")
            if self._player:
                try:
                    self._player.stop_playback()
                except Exception:
                    pass
            await self.event_bus.publish("playback.failed", {"session_id": sid, "error": data.get("error")})
            # Возврат в SLEEPING
            try:
                await self.state_manager.set_mode(AppMode.SLEEPING)
            except Exception:
                pass
        except Exception as e:
            await self._handle_error(e, where="speech.on_grpc_failed", severity="warning")

    async def _on_interrupt(self, event):
        try:
            if self._player:
                self._player.stop_playback()
            await self.event_bus.publish("playback.cancelled", {"reason": "interrupt"})
            try:
                await self.state_manager.set_mode(AppMode.SLEEPING)
            except Exception:
                pass
        except Exception as e:
            await self._handle_error(e, where="speech.on_interrupt", severity="warning")

    async def _on_app_shutdown(self, event):
        await self.stop()

    # -------- Utils --------
    async def _handle_error(self, e: Exception, *, where: str, severity: str = "error"):
        if hasattr(self.error_handler, 'handle'):
            await self.error_handler.handle(
                error=e,
                category="speech_playback",
                severity=severity,
                context={"where": where}
            )
        else:
            logger.error(f"Speech playback error at {where}: {e}")

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "running": self._running,
            "player": (self._player.get_status() if self._player else {}),
        }

