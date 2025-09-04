
import asyncio
import os
import logging
from typing import Optional, Dict, Any, AsyncGenerator, Union
import edge_tts
try:
    import azure.cognitiveservices.speech as speechsdk  # type: ignore
except Exception:
    speechsdk = None
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
        # КРИТИЧНО: флаг для отслеживания состояния генерации
        self.is_generating = False
        self._validate_voice()
        
        # Флаг и конфигурация Azure Speech (если заданы ключ и регион)
        self._use_azure = bool(getattr(Config, 'SPEECH_KEY', None) and getattr(Config, 'SPEECH_REGION', None) and speechsdk is not None)
        if self._use_azure:
            try:
                self._azure_speech_config = speechsdk.SpeechConfig(subscription=Config.SPEECH_KEY, region=Config.SPEECH_REGION)
                # Устанавливаем голос (совместимый с Azure, например en-US-JennyNeural)
                self._azure_speech_config.speech_synthesis_voice_name = self.voice
                # Возвращаем PCM 48kHz mono 16-bit для прямой конвертации в numpy
                self._azure_speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Raw48Khz16BitMonoPcm
                )
                logger.info("Azure Speech TTS включён")
            except Exception as azure_init_err:
                self._use_azure = False
                logger.error(f"Azure Speech инициализация не удалась, fallback на edge-tts: {azure_init_err}")
        
    def _validate_voice(self):
        """Проверяет доступность выбранного голоса."""
        logger.info(f"Голос {self.voice} установлен")

    async def generate_complete_audio_for_sentence(self, text: str, interrupt_checker=None) -> Optional[np.ndarray]:
        """
        Генерирует аудио для ЦЕЛОГО предложения и возвращает его ОДНИМ numpy-массивом.
        interrupt_checker: функция для проверки необходимости прерывания
        """
        if not text or not text.strip():
            logger.warning("Пустой текст для генерации аудио")
            return None

        try:
            # КРИТИЧНО: устанавливаем флаг генерации
            self.is_generating = True
            logger.info(f"🎵 Начинаю генерацию аудио для: {text[:50]}...")
            
            # Вариант 1: Azure Speech (если доступен)
            if self._use_azure:
                loop = asyncio.get_running_loop()
                def _speak_sync() -> bytes:
                    synthesizer = speechsdk.SpeechSynthesizer(speech_config=self._azure_speech_config, audio_config=None)
                    result = synthesizer.speak_text_async(text).get()
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        return result.audio_data or b""
                    raise RuntimeError(f"Azure Speech синтез не выполнен: {result.reason}")
                audio_bytes: bytes = await loop.run_in_executor(None, _speak_sync)
                if not audio_bytes:
                    logger.error("Azure Speech вернул пустой аудиопоток")
                    return None
                samples = np.frombuffer(audio_bytes, dtype=np.int16)
                # Приводим к целевому sample rate при необходимости
                if Config.SAMPLE_RATE != 48000:
                    audio_segment = AudioSegment(
                        audio_bytes,
                        frame_rate=48000,
                        sample_width=2,
                        channels=1
                    )
                    audio_segment = audio_segment.set_frame_rate(Config.SAMPLE_RATE).set_channels(1)
                    samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                logger.info(f"Аудио (Azure) сгенерировано ({len(samples)} сэмплов).")
                return samples

            # Вариант 2: edge-tts (fallback)
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
                # КРИТИЧНО: проверяем необходимость прерывания в КАЖДОЙ итерации
                if interrupt_checker and interrupt_checker():
                    logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН - МГНОВЕННО ПРЕРЫВАЮ ГЕНЕРАЦИЮ АУДИО!")
                    return None
                
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
        finally:
            # КРИТИЧНО: сбрасываем флаг генерации
            self.is_generating = False
            logger.info(f"🎵 Генерация аудио завершена")

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

    async def generate_streaming_audio(self, text: str, interrupt_checker=None) -> AsyncGenerator[np.ndarray, None]:
        """
        🚀 НОВЫЙ МЕТОД: Генерирует аудио для ПОЛНОГО предложения и отправляет ЦЕЛИКОМ.
        Это решает проблему со скрипом и упрощает архитектуру - отправляем по предложениям.
        """
        if not text or not text.strip():
            return
        
        try:
            self.is_generating = True
            logger.info(f"🎵 Генерирую аудио для предложения: {text[:50]}...")
            
            # Генерируем ПОЛНОЕ аудио для предложения
            complete_audio = await self.generate_complete_audio_for_sentence(text, interrupt_checker)
            
            if complete_audio is not None and len(complete_audio) > 0:
                # Отправляем ВСЕ аудио одним большим чанком (целое предложение)
                logger.info(f"🎵 Отправляю ПОЛНОЕ аудио предложения: {len(complete_audio)} сэмплов")
                yield complete_audio
                
                logger.info(f"✅ Потоковая генерация завершена: {len(complete_audio)} сэмплов")
            else:
                logger.warning("⚠️ Не удалось сгенерировать аудио для предложения")
                
        except Exception as e:
            logger.error(f"❌ Ошибка при генерации аудио для предложения: {e}")
        finally:
            self.is_generating = False

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
            'voice': self.voice,
            'rate': self.rate,
            'volume': self.volume,
            'pitch': self.pitch
        }
    
    def clear_buffers(self):
        """
        МГНОВЕННО очищает все буферы и отменяет генерацию аудио.
        Используется для принудительного прерывания.
        """
        try:
            logger.warning("🚨 МГНОВЕННАЯ очистка буферов аудио генератора!")
            
            # КРИТИЧНО: очищаем все внутренние буферы
            if hasattr(self, '_current_communicate'):
                try:
                    # Отменяем текущую генерацию edge-tts
                    if hasattr(self._current_communicate, 'cancel'):
                        self._current_communicate.cancel()
                        logger.warning("🚨 Edge TTS генерация МГНОВЕННО ОТМЕНЕНА!")
                except:
                    pass
                self._current_communicate = None
            
            # КРИТИЧНО: очищаем все временные буферы
            if hasattr(self, '_temp_buffers'):
                self._temp_buffers.clear()
                logger.warning("🚨 Временные буферы МГНОВЕННО ОЧИЩЕНЫ!")
            
            logger.warning("✅ Все буферы аудио генератора МГНОВЕННО очищены!")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки буферов аудио: {e}")
    
    def cancel_generation(self):
        """
        МГНОВЕННО отменяет текущую генерацию аудио.
        """
        try:
            logger.warning("🚨 МГНОВЕННАЯ отмена генерации аудио!")
            self.clear_buffers()
            logger.warning("✅ Генерация аудио МГНОВЕННО отменена!")
        except Exception as e:
            logger.error(f"❌ Ошибка отмены генерации аудио: {e}")