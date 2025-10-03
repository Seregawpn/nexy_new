"""
Welcome Player — воспроизведение приветствия, сгенерированного на сервере.
"""

import logging
from typing import Optional, Callable, Dict, Any
import numpy as np

from .types import WelcomeConfig, WelcomeState, WelcomeResult
from .audio_generator import WelcomeAudioGenerator

logger = logging.getLogger(__name__)


class WelcomePlayer:
    """Плеер для воспроизведения приветственного сообщения"""
    
    def __init__(self, config: WelcomeConfig):
        self.config = config
        self.state = WelcomeState.IDLE
        self.audio_generator = WelcomeAudioGenerator(config)
        
        # Коллбеки
        self._on_started: Optional[Callable[[], None]] = None
        self._on_completed: Optional[Callable[[WelcomeResult], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        
        # Последнее подготовленное аудио и метаданные
        self._last_audio: Optional[np.ndarray] = None
        self._last_metadata: Optional[Dict[str, Any]] = None
    
    def set_callbacks(
        self,
        on_started: Optional[Callable[[], None]] = None,
        on_completed: Optional[Callable[[WelcomeResult], None]] = None,
        on_error: Optional[Callable[[str], None]] = None
    ):
        """Установить коллбеки для событий"""
        self._on_started = on_started
        self._on_completed = on_completed
        self._on_error = on_error
    
    async def play_welcome(self) -> WelcomeResult:
        """
        Воспроизводит приветственное сообщение
        
        Returns:
            WelcomeResult с результатом воспроизведения
        """
        try:
            logger.info("🎵 [WELCOME_PLAYER] Начинаю воспроизведение приветствия")
            self.state = WelcomeState.LOADING
            self._last_audio = None
            self._last_metadata = None
            
            # Проверяем, включен ли модуль
            if not self.config.enabled:
                error_msg = "Модуль приветствия отключен в конфигурации"
                logger.info(f"🔇 [WELCOME_PLAYER] {error_msg}")
                self.state = WelcomeState.ERROR
                
                result = WelcomeResult(
                    success=False,
                    method="none",
                    duration_sec=0.0,
                    error=error_msg
                )
                
                if self._on_error:
                    self._on_error(error_msg)
                if self._on_completed:
                    self._on_completed(result)
                
                return result
            
            # Уведомляем о начале
            if self._on_started:
                self._on_started()
            
            if not self.config.use_server:
                error_msg = "Серверное воспроизведение приветствия отключено в конфигурации"
                logger.error(f"❌ [WELCOME_PLAYER] {error_msg}")
                self.state = WelcomeState.ERROR

                result = WelcomeResult(
                    success=False,
                    method="none",
                    duration_sec=0.0,
                    error=error_msg
                )

                if self._on_error:
                    self._on_error(error_msg)
                if self._on_completed:
                    self._on_completed(result)

                return result

            server_result = await self._play_server_audio()
            if server_result.success:
                logger.info("✅ [WELCOME_PLAYER] Серверное приветствие воспроизведено успешно")
                self.state = WelcomeState.COMPLETED
                if self._on_completed:
                    self._on_completed(server_result)
                return server_result

            error_msg = server_result.error or "Серверное воспроизведение приветствия не удалось"
            logger.error(f"❌ [WELCOME_PLAYER] {error_msg}")
            self.state = WelcomeState.ERROR
            
            result = WelcomeResult(
                success=False,
                method="none",
                duration_sec=0.0,
                error=error_msg
            )
            
            if self._on_error:
                self._on_error(error_msg)
            if self._on_completed:
                self._on_completed(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Критическая ошибка воспроизведения приветствия: {e}"
            logger.error(f"❌ [WELCOME_PLAYER] {error_msg}")
            self.state = WelcomeState.ERROR
            
            result = WelcomeResult(
                success=False,
                method="error",
                duration_sec=0.0,
                error=error_msg
            )
            
            if self._on_error:
                self._on_error(error_msg)
            if self._on_completed:
                self._on_completed(result)
            
            return result
    
    async def _play_server_audio(self) -> WelcomeResult:
        """Пытается воспроизвести приветствие, сгенерированное на сервере"""
        try:
            audio_data = await self.audio_generator.generate_server_audio(self.config.text)
            if audio_data is None:
                return WelcomeResult(
                    success=False,
                    method="server",
                    duration_sec=0.0,
                    error="Серверная генерация вернула пустой результат"
                )

            server_metadata = self.audio_generator.get_last_server_metadata()
            sample_rate = server_metadata.get('sample_rate', self.config.sample_rate)
            channels = server_metadata.get('channels', self.config.channels)

            total_samples = int(audio_data.size if hasattr(audio_data, 'size') else len(audio_data))
            if audio_data.ndim > 1:
                frame_count = audio_data.shape[0]
            else:
                frame_count = total_samples // max(1, channels)
            duration_sec = frame_count / float(sample_rate)

            metadata = {
                "sample_rate": sample_rate,
                "channels": channels,
                "samples": total_samples,
                "frames": frame_count,
                "method": server_metadata.get('method', 'server'),
                "duration_sec": server_metadata.get('duration_sec', duration_sec),
            }

            self._last_audio = audio_data
            self._last_metadata = metadata

            return WelcomeResult(
                success=True,
                method="server",
                duration_sec=duration_sec,
                metadata=metadata
            )

        except Exception as e:
            return WelcomeResult(
                success=False,
                method="server",
                duration_sec=0.0,
                error=f"Ошибка серверной генерации: {e}"
            )

    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """Получить аудио данные для воспроизведения"""
        return self._last_audio

    def get_audio_metadata(self) -> Optional[Dict[str, Any]]:
        """Получить метаданные последнего аудио"""
        return self._last_metadata
    
    def is_ready(self) -> bool:
        """Проверить, готов ли плеер к воспроизведению"""
        return self.state in [WelcomeState.IDLE, WelcomeState.COMPLETED]
    
    def reset(self):
        """Сбросить состояние плеера"""
        self.state = WelcomeState.IDLE
        self._last_audio = None
        self._last_metadata = None
