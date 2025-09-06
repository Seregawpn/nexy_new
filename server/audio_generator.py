#!/usr/bin/env python3
"""
AudioGenerator with Azure Speech Services
High-quality TTS with proper authentication
"""

import asyncio
import logging
import tempfile
import os
from typing import Optional, AsyncGenerator
import numpy as np
from pydub import AudioSegment
import io
import azure.cognitiveservices.speech as speechsdk
from config import Config
from utils.text_utils import split_into_sentences

logger = logging.getLogger(__name__)

class AudioGenerator:
    """
    Audio generator with Azure Speech Services
    High-quality TTS with proper authentication
    """
    
    def __init__(self, voice: str = "en-US-JennyNeural"):
        self.voice = voice
        self.is_generating = False
        
        # Проверяем конфигурацию Azure
        if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
            raise ValueError("Azure Speech Services не настроены. Проверьте SPEECH_KEY и SPEECH_REGION в config.env")
        
        # Настраиваем Azure Speech Services
        self.speech_config = speechsdk.SpeechConfig(
            subscription=Config.SPEECH_KEY,
            region=Config.SPEECH_REGION
        )
        self.speech_config.speech_synthesis_voice_name = self.voice
        
        # Настраиваем формат аудио для возврата 48000Hz 16-bit mono PCM
        self.speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
        )
        
        logger.info(f"🎵 AudioGenerator initialized with voice: {self.voice}")
        logger.info(f"✅ Using Azure Speech Services - Region: {Config.SPEECH_REGION}")
        logger.info(f"🎵 Audio format: 48000Hz 16-bit mono PCM")
    
    def _is_russian_text(self, text: str) -> bool:
        """
        Проверяет, содержит ли текст русские символы
        NOTE: This method is kept for compatibility but always returns False
        since we only work with English now.
        """
        return False  # Always use English/Azure TTS
    
    async def generate_audio(self, text: str) -> Optional[np.ndarray]:
        """
        Генерирует аудио для текста и возвращает numpy массив
        """
        logger.info(f"🎵 [AUDIO_GEN] generate_audio() вызван для текста: '{text[:50]}...'")
        
        if not text or not text.strip():
            logger.warning("⚠️ [AUDIO_GEN] Пустой текст для генерации аудио")
            return None
        
        try:
            self.is_generating = True
            logger.info(f"🎵 [AUDIO_GEN] Generating audio for: {text[:50]}...")
            
            # Используем Azure Speech Services
            logger.info("🇺🇸 [AUDIO_GEN] Using Azure Speech Services for all text")
            result = await self._generate_with_azure_tts(text)
            logger.info(f"🎵 [AUDIO_GEN] generate_audio() завершен, результат: {len(result) if result is not None else 'None'} сэмплов")
            return result
            
        except Exception as e:
            logger.error(f"❌ Audio generation error: {e}")
            return None
        finally:
            self.is_generating = False
    
    async def _generate_with_azure_tts(self, text: str) -> Optional[np.ndarray]:
        """Генерирует аудио с помощью Azure Speech Services"""
        logger.info(f"🎵 [AZURE_TTS] _generate_with_azure_tts() вызван для: '{text[:30]}...'")
        
        try:
            # Создаем синтезатор речи
            logger.info(f"🎵 [AZURE_TTS] Создаю синтезатор речи...")
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # Будем получать аудио в память
            )
            
            # Выполняем синтез речи
            logger.info(f"🎵 [AZURE_TTS] Выполняю синтез речи...")
            result = synthesizer.speak_text_async(text).get()
            logger.info(f"🎵 [AZURE_TTS] Результат синтеза: {result.reason}")
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Получаем аудио данные
                audio_data = result.audio_data
                logger.info(f"🎵 [AZURE_TTS] Получены аудио данные: {len(audio_data)} байт")
                
                if len(audio_data) == 0:
                    logger.error("❌ [AZURE_TTS] Не получены аудио данные")
                    return None
                
                # Конвертируем в numpy массив
                logger.info(f"🎵 [AZURE_TTS] Конвертирую в AudioSegment...")
                audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
                logger.info(f"🎵 [AZURE_TTS] Исходный AudioSegment: {audio_segment.frame_rate}Hz, {audio_segment.channels}ch, {len(audio_segment)}ms")
                
                # Azure TTS уже настроен на 48000Hz 16-bit mono, конвертируем только каналы если нужно
                if audio_segment.channels != 1:
                    audio_segment = audio_segment.set_channels(1)
                    logger.info(f"🎵 [AZURE_TTS] Конвертирован в моно: {audio_segment.frame_rate}Hz, {audio_segment.channels}ch, {len(audio_segment)}ms")
                else:
                    logger.info(f"🎵 [AZURE_TTS] Аудио уже в правильном формате: {audio_segment.frame_rate}Hz, {audio_segment.channels}ch, {len(audio_segment)}ms")
                
                samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                logger.info(f"✅ [AZURE_TTS] Аудио сгенерировано: {len(samples)} сэмплов")
                logger.info(f"📊 [AZURE_TTS] Статистика сэмплов: min={samples.min()}, max={samples.max()}, mean={samples.mean():.2f}")
                return samples
                
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                logger.error(f"❌ Azure TTS отменен: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"❌ Ошибка: {cancellation_details.error_details}")
                return None
            else:
                logger.error(f"❌ Azure TTS: Неожиданный результат: {result.reason}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Azure TTS ошибка: {e}")
            raise
    
    async def generate_streaming_audio(self, text: str) -> AsyncGenerator[np.ndarray, None]:
        """
        Генерирует аудио по частям для потоковой передачи
        """
        logger.info(f"🎵 [STREAM_GEN] generate_streaming_audio() вызван для: '{text[:50]}...'")
        
        if not text or not text.strip():
            logger.warning("⚠️ [STREAM_GEN] Пустой текст для потоковой генерации")
            return
        
        try:
            self.is_generating = True
            logger.info(f"🎵 [STREAM_GEN] Streaming generation for: {text[:50]}...")
            
            # Split text into sentences
            sentences = split_into_sentences(text)
            logger.info(f"📝 [STREAM_GEN] Split into {len(sentences)} sentences")
            
            valid_sentences = 0
            generated_chunks = 0
            
            for i, sentence in enumerate(sentences):
                # КРИТИЧНО: Пропускаем пустые предложения
                if not sentence or not sentence.strip():
                    logger.debug(f"🔇 [STREAM_GEN] Пропускаю пустое предложение {i+1}")
                    continue
                
                valid_sentences += 1
                logger.info(f"🎵 [STREAM_GEN] Generating sentence {valid_sentences}/{len(sentences)}: {sentence[:30]}...")
                
                # Generate audio for sentence
                logger.info(f"🎵 [STREAM_GEN] Вызываю generate_audio() для предложения {valid_sentences}")
                audio = await self.generate_audio(sentence)
                logger.info(f"🎵 [STREAM_GEN] generate_audio() вернул: {len(audio) if audio is not None else 'None'} сэмплов")
                
                # КРИТИЧНО: Проверяем, что аудио не пустое перед отправкой
                if audio is not None and len(audio) > 0:
                    generated_chunks += 1
                    logger.info(f"✅ [STREAM_GEN] Sentence {valid_sentences} ready: {len(audio)} samples - ОТПРАВЛЯЮ")
                    yield audio
                else:
                    logger.warning(f"⚠️ [STREAM_GEN] Failed to generate audio for sentence {valid_sentences} - НЕ ОТПРАВЛЯЮ пустой чанк")
            
            logger.info(f"✅ [STREAM_GEN] Streaming generation completed: {generated_chunks} чанков из {valid_sentences} предложений")
            
        except Exception as e:
            logger.error(f"❌ [STREAM_GEN] Streaming generation error: {e}")
        finally:
            self.is_generating = False
            logger.info(f"🎵 [STREAM_GEN] generate_streaming_audio() завершен")
    
    def set_voice(self, voice: str):
        """
        Sets new voice
        """
        if voice and voice.strip():
            self.voice = voice
            self.speech_config.speech_synthesis_voice_name = voice
            logger.info(f"🎵 Voice changed to: {voice}")
        else:
            logger.warning(f"⚠️ Invalid voice: {voice}")
    
    def get_voice(self) -> str:
        """
        Returns current voice
        """
        return self.voice
    
    def stop_generation(self):
        """
        Stops audio generation
        """
        logger.info("🛑 Stopping audio generation")
        self.is_generating = False
    
    def is_busy(self) -> bool:
        """
        Checks if audio is being generated
        """
        return self.is_generating

