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
try:
    import azure.cognitiveservices.speech as speechsdk
    _AZURE_SDK_AVAILABLE = True
except Exception:
    speechsdk = None  # type: ignore
    _AZURE_SDK_AVAILABLE = False

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

        # Режимы работы - ТОЛЬКО AZURE TTS
        self._use_azure = bool(_AZURE_SDK_AVAILABLE and Config.SPEECH_KEY and Config.SPEECH_REGION)
        
        # Edge TTS отключен (генерирует пустые файлы)
        self._edge_tts_available = False
        self._use_edge_tts = False
        
        # macOS say fallback (только для экстренных случаев)
        self._use_macos_say = os.getenv('USE_MACOS_SAY', 'false').lower() == 'true'

        if self._use_azure:
            # Настраиваем Azure Speech Services
            self.speech_config = speechsdk.SpeechConfig(
                subscription=Config.SPEECH_KEY,
                region=Config.SPEECH_REGION
            )
            self.speech_config.speech_synthesis_voice_name = self.voice
            # Формат: 48000Hz 16-bit mono PCM
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
            )
            logger.info(f"🎵 AudioGenerator initialized with voice: {self.voice}")
            logger.info(f"✅ Using Azure Speech Services (PRIMARY) - Region: {Config.SPEECH_REGION}")
            logger.info(f"🎵 Audio format: 48000Hz 16-bit mono PCM")
            logger.info(f"🚫 Edge TTS отключен (генерирует пустые файлы)")
        else:
            self.speech_config = None
            if self._use_macos_say:
                logger.info("🍎 macOS say включен — используем встроенный TTS (fallback)")
            else:
                logger.warning("⚠️ Azure TTS недоступен — использую fallback методы")
    
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

            if self._use_azure:
                logger.info("🇺🇸 [AUDIO_GEN] Using Azure Speech Services (PRIMARY)")
                result = await self._generate_with_azure_tts(text)
                # Если Azure не сработал — используем fallback
                if result is None:
                    logger.warning("🎛️ [AUDIO_GEN] Azure failed — trying fallback methods")
                    if self._use_macos_say:
                        logger.info("🍎 [AUDIO_GEN] Trying macOS say fallback")
                        result = await self._generate_with_macos_say(text)
                    # Последняя страховка
                    if result is None:
                        logger.warning("🎛️ [AUDIO_GEN] All methods failed — using improved fallback")
                        result = self._generate_with_improved_fallback(text)
            elif self._use_macos_say:
                # Используем macOS say (если Azure недоступен)
                logger.info("🍎 [AUDIO_GEN] Using macOS say (Azure unavailable)")
                result = await self._generate_with_macos_say(text)
                if result is None:
                    logger.warning("🎛️ [AUDIO_GEN] macOS say failed — using improved fallback")
                    result = self._generate_with_improved_fallback(text)
            else:
                # Последний fallback
                logger.warning("🎛️ [AUDIO_GEN] No TTS available — using improved fallback")
                result = self._generate_with_improved_fallback(text)

            logger.info(f"🎵 [AUDIO_GEN] generate_audio() завершен, результат: {len(result) if isinstance(result, np.ndarray) else 'None'} сэмплов")
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
            # Возвращаем None, чтобы вызвать фолбэк (Edge TTS / sine)
            return None

    async def _generate_with_edge_tts(self, text: str) -> Optional[np.ndarray]:
        """Генерация аудио через edge-tts с retry механизмом."""
        import edge_tts
        import asyncio
        
        max_retries = 3
        retry_delay = 1.0
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    logger.info(f"🔄 [EDGE_TTS] Retry {attempt + 1}/{max_retries} через {retry_delay}s...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 1.5  # Экспоненциальная задержка
                
                # Создаем новое соединение для каждой попытки
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=self.voice,
                    rate=Config.EDGE_TTS_RATE,
                    volume=Config.EDGE_TTS_VOLUME,
                )
                
                audio_bytes = b""
                try:
                    async for chunk in communicate.stream():
                        if chunk["type"] == "audio":
                            audio_bytes += chunk["data"]
                except Exception as e:
                    logger.warning(f"⚠️ [EDGE_TTS] WebSocket ошибка на попытке {attempt + 1}: {e}")
                    continue
                
                if not audio_bytes:
                    logger.warning(f"⚠️ [EDGE_TTS] Empty audio data на попытке {attempt + 1}")
                    continue

                # Декодируем аудио с множественными попытками
                seg = None
                for format_attempt in ['auto', 'mp3', 'wav']:
                    try:
                        if format_attempt == 'auto':
                            seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
                        elif format_attempt == 'mp3':
                            seg = AudioSegment.from_mp3(io.BytesIO(audio_bytes))
                        elif format_attempt == 'wav':
                            seg = AudioSegment.from_wav(io.BytesIO(audio_bytes))
                        break
                    except Exception as e:
                        if format_attempt == 'wav':  # Последняя попытка
                            logger.warning(f"⚠️ [EDGE_TTS] Audio decode failed на попытке {attempt + 1}: {e}")
                            break
                        continue
                        
                if seg is None:
                    continue
                        
                # Конвертируем в нужный формат
                if seg.frame_rate != 48000:
                    seg = seg.set_frame_rate(48000)
                if seg.channels != 1:
                    seg = seg.set_channels(1)
                    
                samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                logger.info(f"✅ [EDGE_TTS] Success на попытке {attempt + 1}: {len(samples)} samples")
                return samples
                
            except Exception as e:
                logger.warning(f"⚠️ [EDGE_TTS] Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    logger.error(f"❌ [EDGE_TTS] All {max_retries} attempts failed")
                    return None
                continue
        
        return None

    async def _generate_with_macos_say(self, text: str) -> Optional[np.ndarray]:
        """Генерация аудио через встроенный macOS say command"""
        try:
            import subprocess
            import tempfile
            from pydub import AudioSegment
            
            logger.info(f"🍎 [MACOS_SAY] Генерация для: '{text[:50]}...'")
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Генерируем аудио через say
                cmd = [
                    'say',
                    '-v', 'Samantha',  # Качественный женский голос
                    '-r', '180',       # Скорость (слов в минуту)
                    '-o', temp_path,   # Выходной файл
                    text
                ]
                
                # Запускаем с таймаутом
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                
                if result.returncode == 0 and os.path.exists(temp_path):
                    # Конвертируем в нужный формат
                    seg = AudioSegment.from_file(temp_path)
                    
                    # Приводим к стандартному формату: 48000Hz mono
                    if seg.frame_rate != 48000:
                        seg = seg.set_frame_rate(48000)
                    if seg.channels != 1:
                        seg = seg.set_channels(1)
                    
                    # Конвертируем в numpy int16
                    samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                    
                    logger.info(f"✅ [MACOS_SAY] Успешно: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
                    return samples
                    
                else:
                    logger.error(f"❌ [MACOS_SAY] Ошибка выполнения: {result.stderr}")
                    return None
                    
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            logger.error("⏰ [MACOS_SAY] Таймаут 15s")
            return None
        except Exception as e:
            logger.error(f"❌ [MACOS_SAY] Ошибка: {e}")
            return None

    def _generate_with_improved_fallback(self, text: str) -> Optional[np.ndarray]:
        """
        Улучшенный локальный fallback: короткий beep вместо длинного тона
        Заменяет проблемный sine-wave на краткий сигнал уведомления
        """
        try:
            logger.warning(f"🎛️ [IMPROVED_FALLBACK] TTS недоступен, создаю короткий beep")
            logger.info(f"🎛️ [IMPROVED_FALLBACK] Исходный текст: '{text[:50]}...'")
            
            sr = 48000
            
            # Короткий двойной beep (0.6 секунды) вместо длинного тона
            beep1_dur = 0.15  # 150ms первый beep
            pause_dur = 0.1   # 100ms пауза
            beep2_dur = 0.15  # 150ms второй beep
            final_pause = 0.2 # 200ms финальная пауза
            
            total_duration = beep1_dur + pause_dur + beep2_dur + final_pause
            total_samples = int(sr * total_duration)
            
            # Создаем сигнал
            audio = np.zeros(total_samples, dtype=np.float32)
            
            # Первый beep (800Hz)
            beep1_samples = int(sr * beep1_dur)
            t1 = np.linspace(0, beep1_dur, beep1_samples, endpoint=False)
            beep1 = 0.3 * np.sin(2 * np.pi * 800 * t1)
            # Мягкий fade-in/out
            fade_samples = int(0.02 * sr)  # 20ms fade
            beep1[:fade_samples] *= np.linspace(0, 1, fade_samples)
            beep1[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            audio[:beep1_samples] = beep1
            
            # Второй beep (1000Hz) после паузы
            beep2_start = int(sr * (beep1_dur + pause_dur))
            beep2_samples = int(sr * beep2_dur)
            t2 = np.linspace(0, beep2_dur, beep2_samples, endpoint=False)
            beep2 = 0.3 * np.sin(2 * np.pi * 1000 * t2)
            beep2[:fade_samples] *= np.linspace(0, 1, fade_samples)
            beep2[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            audio[beep2_start:beep2_start + beep2_samples] = beep2
            
            # Конвертируем в int16
            audio_int16 = np.asarray(audio * 32767, dtype=np.int16)
            
            logger.info(f"✅ [IMPROVED_FALLBACK] Создан двойной beep: {len(audio_int16)} сэмплов, {total_duration:.1f}s")
            return audio_int16
            
        except Exception as e:
            logger.error(f"❌ [IMPROVED_FALLBACK] Ошибка: {e}")
            # Последняя страховка - тишина
            try:
                return np.zeros(int(0.5 * 48000), dtype=np.int16)  # 0.5 сек тишины
            except:
                return None

    def _generate_with_sine_fallback(self, text: str) -> Optional[np.ndarray]:
        """
        Локальный фолбэк-генератор: создает моно-сигнал 48kHz int16.
        Длительность пропорциональна длине текста (до 3.5с).
        """
        try:
            sr = 48000
            # 50 мс на символ, от 0.6с до 3.5с
            duration_sec = min(3.5, max(0.6, 0.05 * max(1, len(text.strip()))))
            t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False, dtype=np.float32)
            # Небольшая мелодия: A4 440 Гц с амплитудной огибающей
            freq = 440.0
            envelope = np.minimum(1.0, np.linspace(0, 1.0, int(0.1 * sr)))
            envelope = np.pad(envelope, (0, len(t) - len(envelope)), constant_values=(0, 1.0))
            wave = 0.2 * np.sin(2 * np.pi * freq * t) * envelope
            # Конвертация в int16 моно
            audio = np.asarray(wave * 32767, dtype=np.int16)
            return audio
        except Exception as e:
            logger.error(f"❌ Fallback synth error: {e}")
            return None
    
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
