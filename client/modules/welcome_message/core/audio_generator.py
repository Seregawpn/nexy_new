"""
Welcome Audio Generator

Локальный генератор аудио для приветственного сообщения.
Использует серверный AudioGenerator (Azure TTS) с fallback на macOS say.
"""

import asyncio
import logging
import subprocess
import tempfile
import sys
from pathlib import Path
from typing import Optional, Tuple
import numpy as np
from pydub import AudioSegment

from .types import WelcomeConfig

# Импортируем серверный AudioGenerator
try:
    server_path = Path(__file__).parent.parent.parent.parent.parent / "server"
    sys.path.append(str(server_path))
    from audio_generator import AudioGenerator as ServerAudioGenerator
    from config import Config as ServerConfig
    _SERVER_AUDIO_GEN_AVAILABLE = True
except Exception:
    ServerAudioGenerator = None
    ServerConfig = None
    _SERVER_AUDIO_GEN_AVAILABLE = False

logger = logging.getLogger(__name__)


class WelcomeAudioGenerator:
    """Генератор аудио для приветственного сообщения"""
    
    def __init__(self, config: WelcomeConfig):
        self.config = config
        self._cache: Optional[np.ndarray] = None
        self._cache_path: Optional[Path] = None
        
        # Серверный генератор (если доступен)
        self._server_generator: Optional[ServerAudioGenerator] = None
        if _SERVER_AUDIO_GEN_AVAILABLE:
            try:
                self._server_generator = ServerAudioGenerator(voice=config.voice)
                logger.info("✅ [WELCOME_AUDIO] Серверный AudioGenerator доступен (Azure TTS)")
            except Exception as e:
                logger.warning(f"⚠️ [WELCOME_AUDIO] Не удалось создать серверный генератор: {e}")
                self._server_generator = None
    
    async def generate_audio(self, text: str) -> Optional[np.ndarray]:
        """
        Генерирует аудио для текста приветствия
        
        Args:
            text: Текст для генерации
            
        Returns:
            numpy массив аудио данных или None при ошибке
        """
        try:
            logger.info(f"🎵 [WELCOME_AUDIO] Генерация аудио для: '{text[:30]}...'")
            
            # Сначала пробуем серверный AudioGenerator (Azure TTS)
            if self._server_generator:
                logger.info("🎵 [WELCOME_AUDIO] Пробуем серверный AudioGenerator (Azure TTS)")
                audio_data = await self._generate_with_server_generator(text)
                if audio_data is not None:
                    logger.info(f"✅ [WELCOME_AUDIO] Успешно сгенерировано через Azure TTS: {len(audio_data)} сэмплов")
                    return audio_data
                logger.warning("⚠️ [WELCOME_AUDIO] Серверный генератор не удался, переключаемся на fallback")
            
            # Fallback на macOS say command
            logger.info("🎵 [WELCOME_AUDIO] Пробуем macOS say fallback")
            audio_data = await self._generate_with_macos_say(text)
            if audio_data is not None:
                logger.info(f"✅ [WELCOME_AUDIO] Успешно сгенерировано через macOS say: {len(audio_data)} сэмплов")
                return audio_data
            
            # Последний fallback на простой tone
            logger.warning("⚠️ [WELCOME_AUDIO] macOS say недоступен, используем fallback tone")
            audio_data = self._generate_fallback_tone(text)
            if audio_data is not None:
                logger.info(f"✅ [WELCOME_AUDIO] Fallback tone создан: {len(audio_data)} сэмплов")
                return audio_data
            
            logger.error("❌ [WELCOME_AUDIO] Не удалось сгенерировать аудио")
            return None
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_AUDIO] Ошибка генерации: {e}")
            return None
    
    async def _generate_with_server_generator(self, text: str) -> Optional[np.ndarray]:
        """Генерация аудио через серверный AudioGenerator (Azure TTS)"""
        try:
            if not self._server_generator:
                return None
            
            logger.info(f"🎵 [WELCOME_AUDIO] Генерация через серверный AudioGenerator для: '{text[:30]}...'")
            
            # Используем серверный генератор
            audio_data = await self._server_generator.generate_audio(text)
            
            if audio_data is not None:
                # Серверный генератор уже возвращает правильный формат (48000Hz 16-bit mono)
                logger.info(f"✅ [WELCOME_AUDIO] Серверный генератор успешно: {len(audio_data)} сэмплов")
                return audio_data
            else:
                logger.warning("⚠️ [WELCOME_AUDIO] Серверный генератор вернул None")
                return None
                
        except Exception as e:
            logger.error(f"❌ [WELCOME_AUDIO] Ошибка серверного генератора: {e}")
            return None
    
    async def _generate_with_macos_say(self, text: str) -> Optional[np.ndarray]:
        """Генерация аудио через macOS say command"""
        try:
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
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and Path(temp_path).exists():
                    # Конвертируем в нужный формат
                    seg = AudioSegment.from_file(temp_path)
                    
                    # Приводим к стандартному формату: 48000Hz mono
                    if seg.frame_rate != self.config.sample_rate:
                        seg = seg.set_frame_rate(self.config.sample_rate)
                    if seg.channels != self.config.channels:
                        seg = seg.set_channels(self.config.channels)
                    
                    # Конвертируем в numpy int16
                    samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                    
                    logger.info(f"✅ [WELCOME_AUDIO] macOS say успешно: {len(samples)} сэмплов, {len(samples)/self.config.sample_rate:.1f}s")
                    return samples
                    
                else:
                    logger.error(f"❌ [WELCOME_AUDIO] macOS say ошибка: {result.stderr}")
                    return None
                    
            finally:
                # Удаляем временный файл
                try:
                    Path(temp_path).unlink(missing_ok=True)
                except Exception:
                    pass
                    
        except subprocess.TimeoutExpired:
            logger.error("⏰ [WELCOME_AUDIO] macOS say таймаут 10s")
            return None
        except Exception as e:
            logger.error(f"❌ [WELCOME_AUDIO] macOS say ошибка: {e}")
            return None
    
    def _generate_fallback_tone(self, text: str) -> Optional[np.ndarray]:
        """
        Fallback генератор: создает короткий приветственный tone
        """
        try:
            logger.info("🎛️ [WELCOME_AUDIO] Создаю fallback tone")
            
            sr = self.config.sample_rate
            
            # Короткий приветственный tone (1.5 секунды)
            duration_sec = 1.5
            total_samples = int(sr * duration_sec)
            
            # Создаем мелодичный tone
            t = np.linspace(0, duration_sec, total_samples, endpoint=False, dtype=np.float32)
            
            # Простая мелодия: две ноты
            note1_dur = 0.6  # Первая нота
            note2_dur = 0.6  # Вторая нота
            pause_dur = 0.3  # Пауза между нотами
            
            audio = np.zeros(total_samples, dtype=np.float32)
            
            # Первая нота (A4 = 440Hz)
            note1_samples = int(sr * note1_dur)
            note1 = 0.3 * np.sin(2 * np.pi * 440 * t[:note1_samples])
            # Мягкий fade-in/out
            fade_samples = int(0.05 * sr)  # 50ms fade
            note1[:fade_samples] *= np.linspace(0, 1, fade_samples)
            note1[-fade_samples:] *= np.linspace(1, 0, fade_samples)
            audio[:note1_samples] = note1
            
            # Вторая нота (C5 = 523Hz) после паузы
            note2_start = int(sr * (note1_dur + pause_dur))
            note2_samples = int(sr * note2_dur)
            if note2_start + note2_samples <= total_samples:
                note2 = 0.3 * np.sin(2 * np.pi * 523 * t[:note2_samples])
                note2[:fade_samples] *= np.linspace(0, 1, fade_samples)
                note2[-fade_samples:] *= np.linspace(1, 0, fade_samples)
                audio[note2_start:note2_start + note2_samples] = note2
            
            # Конвертируем в int16
            audio_int16 = np.asarray(audio * 32767, dtype=np.int16)
            
            logger.info(f"✅ [WELCOME_AUDIO] Fallback tone создан: {len(audio_int16)} сэмплов, {duration_sec:.1f}s")
            return audio_int16
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_AUDIO] Fallback tone ошибка: {e}")
            return None
    
    async def save_audio_to_file(self, audio_data: np.ndarray, output_path: Path) -> bool:
        """
        Сохраняет аудио данные в файл
        
        Args:
            audio_data: numpy массив аудио данных
            output_path: путь для сохранения
            
        Returns:
            True если успешно сохранено
        """
        try:
            # Создаем директорию если не существует
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Конвертируем в AudioSegment
            audio_segment = AudioSegment(
                audio_data.tobytes(),
                frame_rate=self.config.sample_rate,
                sample_width=2,  # 16-bit
                channels=self.config.channels
            )
            
            # Сохраняем в нужном формате
            if output_path.suffix.lower() == '.mp3':
                audio_segment.export(output_path, format="mp3")
            elif output_path.suffix.lower() == '.wav':
                audio_segment.export(output_path, format="wav")
            else:
                # По умолчанию WAV
                audio_segment.export(output_path.with_suffix('.wav'), format="wav")
            
            logger.info(f"✅ [WELCOME_AUDIO] Аудио сохранено: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ [WELCOME_AUDIO] Ошибка сохранения: {e}")
            return False
