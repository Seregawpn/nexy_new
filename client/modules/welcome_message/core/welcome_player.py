"""
Welcome Player

Основной плеер для воспроизведения приветственного сообщения.
Поддерживает предзаписанное аудио и fallback на TTS.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Callable, Any
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
        
        # Кэш для предзаписанного аудио
        self._prerecorded_audio: Optional[np.ndarray] = None
        self._prerecorded_loaded = False
        # Последнее подготовленное аудио (prerecorded или tts)
        self._last_audio: Optional[np.ndarray] = None
    
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
            
            # Сначала пробуем предзаписанное аудио
            result = await self._play_prerecorded()
            if result.success:
                logger.info("✅ [WELCOME_PLAYER] Предзаписанное аудио воспроизведено успешно")
                self.state = WelcomeState.COMPLETED
                if self._on_completed:
                    self._on_completed(result)
                return result
            
            logger.warning(f"⚠️ [WELCOME_PLAYER] Предзаписанное аудио не удалось: {result.error}")
            
            # Fallback на TTS
            if self.config.fallback_to_tts:
                logger.info("🎵 [WELCOME_PLAYER] Переключаюсь на TTS fallback")
                result = await self._play_tts_fallback()
                if result.success:
                    logger.info("✅ [WELCOME_PLAYER] TTS fallback воспроизведен успешно")
                    self.state = WelcomeState.COMPLETED
                    if self._on_completed:
                        self._on_completed(result)
                    return result
                
                logger.error(f"❌ [WELCOME_PLAYER] TTS fallback не удался: {result.error}")
            
            # Все методы не удались
            error_msg = "Все методы воспроизведения приветствия не удались"
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
    
    async def _play_prerecorded(self) -> WelcomeResult:
        """Воспроизводит предзаписанное аудио"""
        try:
            # Загружаем предзаписанное аудио если еще не загружено
            if not self._prerecorded_loaded:
                await self._load_prerecorded_audio()
            
            if self._prerecorded_audio is None:
                return WelcomeResult(
                    success=False,
                    method="prerecorded",
                    duration_sec=0.0,
                    error="Предзаписанное аудио не найдено"
                )
            
            # Воспроизводим через SpeechPlaybackIntegration
            # (это будет реализовано в интеграции)
            duration_sec = len(self._prerecorded_audio) / self.config.sample_rate
            
            logger.info(f"🎵 [WELCOME_PLAYER] Предзаписанное аудио готово: {len(self._prerecorded_audio)} сэмплов, {duration_sec:.1f}s")
            # Сохраняем как последнее подготовленное аудио
            self._last_audio = self._prerecorded_audio
            
            return WelcomeResult(
                success=True,
                method="prerecorded",
                duration_sec=duration_sec,
                metadata={
                    "samples": len(self._prerecorded_audio),
                    "sample_rate": self.config.sample_rate,
                    "channels": self.config.channels
                }
            )
            
        except Exception as e:
            return WelcomeResult(
                success=False,
                method="prerecorded",
                duration_sec=0.0,
                error=f"Ошибка воспроизведения предзаписанного аудио: {e}"
            )
    
    async def _play_tts_fallback(self) -> WelcomeResult:
        """Воспроизводит через TTS fallback"""
        try:
            logger.info(f"🎵 [WELCOME_PLAYER] Генерирую TTS для: '{self.config.text[:30]}...'")
            
            # Генерируем аудио
            audio_data = await self.audio_generator.generate_audio(self.config.text)
            if audio_data is None:
                return WelcomeResult(
                    success=False,
                    method="tts",
                    duration_sec=0.0,
                    error="Не удалось сгенерировать TTS аудио"
                )
            
            # Воспроизводим через SpeechPlaybackIntegration
            # (это будет реализовано в интеграции)
            duration_sec = len(audio_data) / self.config.sample_rate
            
            logger.info(f"🎵 [WELCOME_PLAYER] TTS аудио готово: {len(audio_data)} сэмплов, {duration_sec:.1f}s")
            # Сохраняем как последнее подготовленное аудио
            self._last_audio = audio_data
            
            return WelcomeResult(
                success=True,
                method="tts",
                duration_sec=duration_sec,
                metadata={
                    "samples": len(audio_data),
                    "sample_rate": self.config.sample_rate,
                    "channels": self.config.channels
                }
            )
            
        except Exception as e:
            return WelcomeResult(
                success=False,
                method="tts",
                duration_sec=0.0,
                error=f"Ошибка TTS fallback: {e}"
            )
    
    async def _load_prerecorded_audio(self):
        """Загружает предзаписанное аудио из файла"""
        try:
            audio_path = self.config.get_audio_path()
            logger.info(f"🔍 [WELCOME_PLAYER] Ищу предзаписанное аудио: {audio_path}")
            
            if not audio_path.exists():
                logger.warning(f"⚠️ [WELCOME_PLAYER] Предзаписанное аудио не найдено: {audio_path}")
                logger.warning(f"⚠️ [WELCOME_PLAYER] Будет использован TTS fallback")
                self._prerecorded_loaded = True  # Помечаем как загруженное, чтобы не пытаться снова
                return
            
            logger.info(f"🎵 [WELCOME_PLAYER] Загружаю предзаписанное аудио: {audio_path}")
            
            # Загружаем аудио файл
            from pydub import AudioSegment
            audio_segment = AudioSegment.from_file(str(audio_path))
            
            # Конвертируем в нужный формат
            if audio_segment.frame_rate != self.config.sample_rate:
                audio_segment = audio_segment.set_frame_rate(self.config.sample_rate)
            if audio_segment.channels != self.config.channels:
                audio_segment = audio_segment.set_channels(self.config.channels)
            
            # Конвертируем в numpy массив
            self._prerecorded_audio = np.array(audio_segment.get_array_of_samples(), dtype=np.int16)
            self._prerecorded_loaded = True
            # Обновляем последний подготовленный буфер
            self._last_audio = self._prerecorded_audio
            
            duration_sec = len(self._prerecorded_audio) / self.config.sample_rate
            logger.info(f"✅ [WELCOME_PLAYER] Предзаписанное аудио загружено: {len(self._prerecorded_audio)} сэмплов, {duration_sec:.1f}s")
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_PLAYER] Ошибка загрузки предзаписанного аудио: {e}")
            self._prerecorded_loaded = True  # Помечаем как загруженное, чтобы не пытаться снова
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """Получить аудио данные для воспроизведения"""
        return self._last_audio
    
    def is_ready(self) -> bool:
        """Проверить, готов ли плеер к воспроизведению"""
        return self.state in [WelcomeState.IDLE, WelcomeState.COMPLETED]
    
    def reset(self):
        """Сбросить состояние плеера"""
        self.state = WelcomeState.IDLE
        self._prerecorded_audio = None
        self._prerecorded_loaded = False
        self._last_audio = None
