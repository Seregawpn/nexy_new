import asyncio
import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator, Union
import edge_tts
import numpy as np
from pydub import AudioSegment
import io
from config import Config

logger = logging.getLogger(__name__)

class AudioGenerator:
    """
    Генерирует аудио с помощью edge-tts.
    Может возвращать как поток, так и полный аудиофрагмент.
    """
    
    def __init__(self, voice: str = None, rate: str = None, volume: str = None, pitch: str = None):
        self.voice = voice or Config.EDGE_TTS_VOICE
        self.rate = rate or Config.EDGE_TTS_RATE
        self.volume = volume or Config.EDGE_TTS_VOLUME
        self.pitch = pitch or "+0Hz"
        self._validate_voice()
        
    def _validate_voice(self):
        """Проверяет доступность выбранного голоса."""
        logger.info(f"Голос {self.voice} установлен")

    async def generate_complete_audio_for_sentence(self, text: str) -> Optional[np.ndarray]:
        """
        Генерирует аудио для ЦЕЛОГО предложения и возвращает его ОДНИМ numpy-массивом.
        """
        if not text or not text.strip():
            logger.warning("Пустой текст для генерации аудио")
            return None

        try:
            communicate = edge_tts.Communicate(
                text, 
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch
            )

            logger.info(f"Начинаю полную генерацию аудио для предложения: {text[:50]}...")

            # 1. Накапливаем весь аудиопоток для предложения в памяти
            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])
            
            audio_stream.seek(0)

            if audio_stream.getbuffer().nbytes > 0:
                # 2. Декодируем MP3 и преобразуем в нужный формат
                audio_segment = AudioSegment.from_mp3(audio_stream)
                audio_segment = audio_segment.set_frame_rate(Config.SAMPLE_RATE).set_channels(1)
                
                samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                
                logger.info(f"Аудио для предложения сгенерировано ({len(samples)} сэмплов).")
                return samples
            else:
                logger.error("Ошибка генерации аудио: стрим не содержит данных.")
                return None

        except Exception as e:
            logger.error(f"Ошибка при генерации аудио для текста '{text[:30]}...': {e}")
            return None

    async def generate_audio_stream(self, text: str) -> AsyncGenerator[np.ndarray, None]:
        """
        (УСТАРЕВШИЙ МЕТОД) Генерирует аудио и отдает его маленькими чанками.
        Оставлен для обратной совместимости, если понадобится.
        """
        # Этот метод теперь просто обертка над новым для сохранения интерфейса
        complete_audio = await self.generate_complete_audio_for_sentence(text)
        if complete_audio is not None and len(complete_audio) > 0:
            # Для имитации стриминга можно разбивать, но сейчас просто отдаем целиком
            yield complete_audio

    def set_voice(self, voice: str):
        """Устанавливает новый голос."""
        if voice and voice.strip():
            self.voice = voice
            logger.info(f"Установлен голос: {voice}")
        else:
            logger.warning(f"Голос {voice} недоступен, используем текущий: {self.voice}")

    def set_audio_params(self, rate: str = None, volume: str = None, pitch: str = None):
        """Устанавливает параметры аудио."""
        if rate: self.rate = rate
        if volume: self.volume = volume
        if pitch: self.pitch = pitch
        logger.info(f"Параметры аудио: rate={self.rate}, volume={self.volume}, pitch={self.pitch}")

    def get_audio_params(self) -> dict:
        """Возвращает текущие параметры аудио."""
        return {
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch
        }