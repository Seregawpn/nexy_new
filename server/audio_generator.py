import asyncio
import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator
import edge_tts
import numpy as np
from pydub import AudioSegment
import io
from config import Config

logger = logging.getLogger(__name__)

class AudioGenerator:
    """
    Генерирует аудиопоток с помощью edge-tts и отдает его 
    в виде фрагментов (chunks) NumPy.
    """
    
    def __init__(self, voice: str = None, rate: str = None, volume: str = None, pitch: str = None):
        self.voice = voice or Config.DEFAULT_VOICE
        self.rate = rate or Config.AUDIO_RATE
        self.volume = volume or Config.AUDIO_VOLUME
        self.pitch = pitch or Config.AUDIO_PITCH
        self._validate_voice()
        
    def _validate_voice(self):
        """Проверяет доступность выбранного голоса."""
        # Эта проверка может быть упрощена, т.к. edge-tts сам выдаст ошибку
        logger.info(f"Голос {self.voice} установлен")

    async def generate_audio_stream(self, text: str) -> AsyncGenerator[np.ndarray, None]:
        """
        Генерирует аудио для текста и стримит его в виде NumPy чанков.
        """
        if not text or not text.strip():
            logger.warning("Пустой текст для генерации аудио")
            return

        try:
            communicate = edge_tts.Communicate(
                text, 
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch
            )

            logger.info(f"Начинаю стриминг аудио для: {text[:50]}...")

            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])
            
            audio_stream.seek(0)

            if audio_stream.getbuffer().nbytes > 0:
                audio_segment = AudioSegment.from_mp3(audio_stream)
                audio_segment = audio_segment.set_frame_rate(Config.SAMPLE_RATE).set_channels(1)
                
                samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                
                logger.info(f"Аудио сгенерировано ({len(samples)} сэмплов). Начинаю нарезку на чанки...")

                # Увеличиваем размер чанков для лучшей синхронизации
                chunk_size = 8192  # Увеличиваем с 2048 до 8192 для стабильности
                
                # Добавляем небольшую задержку перед началом стриминга
                await asyncio.sleep(0.1)
                
                for i in range(0, len(samples), chunk_size):
                    chunk = samples[i:i + chunk_size]
                    
                    # Убеждаемся, что чанк не пустой
                    if len(chunk) > 0:
                        yield chunk
                        
                        # Добавляем небольшую задержку между чанками для синхронизации
                        await asyncio.sleep(0.02)  # 20ms задержка между чанками
                    
                    # Даем возможность другим асинхронным задачам выполниться
                    await asyncio.sleep(0)

            else:
                logger.error("Ошибка генерации аудио: стрим не содержит данных.")

        except Exception as e:
            logger.error(f"Ошибка при генерации аудиопотока для текста '{text[:30]}...': {e}")

    def generate_audio_sync(self, text: str) -> list[np.ndarray]:
        """
        Синхронная версия генерации аудио для gRPC сервера.
        Возвращает список аудио чанков.
        """
        if not text or not text.strip():
            logger.warning("Пустой текст для генерации аудио")
            return []

        try:
            # Создаем event loop для асинхронной операции
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                # Запускаем асинхронную генерацию в синхронном контексте
                audio_chunks = loop.run_until_complete(self._generate_audio_chunks(text))
                return audio_chunks
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Ошибка при синхронной генерации аудио для текста '{text[:30]}...': {e}")
            return []

    async def _generate_audio_chunks(self, text: str) -> list[np.ndarray]:
        """
        Вспомогательный асинхронный метод для генерации чанков.
        """
        audio_chunks = []
        
        try:
            communicate = edge_tts.Communicate(
                text, 
                self.voice,
                rate=self.rate,
                volume=self.volume,
                pitch=self.pitch
            )

            logger.info(f"Начинаю генерацию аудио для: {text[:50]}...")

            audio_stream = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_stream.write(chunk["data"])
            
            audio_stream.seek(0)

            if audio_stream.getbuffer().nbytes > 0:
                audio_segment = AudioSegment.from_mp3(audio_stream)
                audio_segment = audio_segment.set_frame_rate(Config.SAMPLE_RATE).set_channels(1)
                
                samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                
                logger.info(f"Аудио сгенерировано ({len(samples)} сэмплов). Начинаю нарезку на чанки...")

                # Размер чанков для стабильности
                chunk_size = 8192
                
                for i in range(0, len(samples), chunk_size):
                    chunk = samples[i:i + chunk_size]
                    
                    # Убеждаемся, что чанк не пустой
                    if len(chunk) > 0:
                        audio_chunks.append(chunk)

            else:
                logger.error("Ошибка генерации аудио: стрим не содержит данных.")

        except Exception as e:
            logger.error(f"Ошибка при генерации аудио чанков для текста '{text[:30]}...': {e}")
        
        return audio_chunks

    def set_voice(self, voice: str):
        """Устанавливает новый голос."""
        if voice in Config.VOICES.values():
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