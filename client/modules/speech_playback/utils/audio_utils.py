"""
Audio Utils - Утилиты для обработки аудио

ОСНОВНЫЕ ФУНКЦИИ:
1. Resampling - пересчет частоты дискретизации
2. Channel conversion - конвертация каналов
3. Audio normalization - нормализация аудио
4. Format conversion - конвертация форматов
"""

import logging
import numpy as np
from typing import Union, Optional
from scipy import signal

logger = logging.getLogger(__name__)

def resample_audio(audio_data: np.ndarray, target_sample_rate: int, original_sample_rate: int = 48000) -> np.ndarray:
    """
    Пересчет частоты дискретизации аудио
    
    Args:
        audio_data: Аудио данные
        target_sample_rate: Целевая частота дискретизации
        original_sample_rate: Исходная частота дискретизации
        
    Returns:
        Пересчитанные аудио данные
    """
    try:
        if original_sample_rate == target_sample_rate:
            return audio_data
        
        # Вычисляем коэффициент пересчета
        ratio = target_sample_rate / original_sample_rate
        
        # Пересчитываем
        resampled_data = signal.resample(audio_data, int(len(audio_data) * ratio))
        
        # Приводим к правильному типу
        if audio_data.dtype == np.int16:
            resampled_data = resampled_data.astype(np.int16)
        elif audio_data.dtype == np.float32:
            resampled_data = resampled_data.astype(np.float32)
        
        logger.debug(f"🔄 Resampling: {original_sample_rate}Hz → {target_sample_rate}Hz (ratio: {ratio:.3f})")
        
        return resampled_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка resampling: {e}")
        return audio_data

def convert_channels(audio_data: np.ndarray, target_channels: int) -> np.ndarray:
    """
    Конвертация количества каналов
    
    Args:
        audio_data: Аудио данные (1D или 2D массив)
        target_channels: Целевое количество каналов
        
    Returns:
        Конвертированные аудио данные
    """
    try:
        # Если данные уже в правильном формате
        if len(audio_data.shape) == 2 and audio_data.shape[1] == target_channels:
            return audio_data
        
        # Если моно (1D) и нужен моно
        if len(audio_data.shape) == 1 and target_channels == 1:
            return audio_data.reshape(-1, 1)
        
        # Если моно (1D) и нужен стерео
        if len(audio_data.shape) == 1 and target_channels == 2:
            return np.column_stack([audio_data, audio_data])
        
        # Если стерео (2D) и нужен моно
        if len(audio_data.shape) == 2 and audio_data.shape[1] == 2 and target_channels == 1:
            return np.mean(audio_data, axis=1)
        
        # Если стерео (2D) и нужен стерео
        if len(audio_data.shape) == 2 and audio_data.shape[1] == 2 and target_channels == 2:
            return audio_data  # Возвращаем 2D массив как есть
        
        # Для других случаев - дублируем первый канал
        if len(audio_data.shape) == 1:
            mono_data = audio_data
        else:
            mono_data = audio_data[:, 0] if audio_data.shape[1] > 0 else audio_data.flatten()
        
        if target_channels == 1:
            return mono_data
        else:
            return np.column_stack([mono_data] * target_channels).flatten()
        
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации каналов: {e}")
        return audio_data

def normalize_audio(audio_data: np.ndarray, target_level: float = 0.8) -> np.ndarray:
    """
    Нормализация аудио по уровню
    
    Args:
        audio_data: Аудио данные
        target_level: Целевой уровень (0.0 - 1.0)
        
    Returns:
        Нормализованные аудио данные
    """
    try:
        # Находим максимальное значение
        max_val = np.max(np.abs(audio_data))
        
        if max_val == 0:
            return audio_data
        
        # Вычисляем коэффициент нормализации
        norm_factor = target_level / max_val
        
        # Нормализуем
        normalized_data = audio_data * norm_factor
        
        # Приводим к правильному типу
        if audio_data.dtype == np.int16:
            normalized_data = np.clip(normalized_data, -32768, 32767).astype(np.int16)
        elif audio_data.dtype == np.float32:
            normalized_data = np.clip(normalized_data, -1.0, 1.0).astype(np.float32)
        
        logger.debug(f"🎵 Нормализация: max={max_val:.3f} → {target_level:.3f} (factor: {norm_factor:.3f})")
        
        return normalized_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка нормализации: {e}")
        return audio_data

def apply_fade_in(audio_data: np.ndarray, fade_samples: int = 1000) -> np.ndarray:
    """
    Применение fade-in эффекта
    
    Args:
        audio_data: Аудио данные
        fade_samples: Количество сэмплов для fade-in
        
    Returns:
        Аудио данные с fade-in
    """
    try:
        if len(audio_data) <= fade_samples:
            return audio_data
        
        # Создаем fade-in маску
        fade_mask = np.linspace(0, 1, fade_samples)
        
        # Применяем к началу данных
        if len(audio_data.shape) == 1:
            audio_data[:fade_samples] *= fade_mask
        else:
            audio_data[:fade_samples, :] *= fade_mask.reshape(-1, 1)
        
        logger.debug(f"🎵 Fade-in применен: {fade_samples} сэмплов")
        
        return audio_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка применения fade-in: {e}")
        return audio_data

def apply_fade_out(audio_data: np.ndarray, fade_samples: int = 1000) -> np.ndarray:
    """
    Применение fade-out эффекта
    
    Args:
        audio_data: Аудио данные
        fade_samples: Количество сэмплов для fade-out
        
    Returns:
        Аудио данные с fade-out
    """
    try:
        if len(audio_data) <= fade_samples:
            return audio_data
        
        # Создаем fade-out маску
        fade_mask = np.linspace(1, 0, fade_samples)
        
        # Применяем к концу данных
        if len(audio_data.shape) == 1:
            audio_data[-fade_samples:] *= fade_mask
        else:
            audio_data[-fade_samples:, :] *= fade_mask.reshape(-1, 1)
        
        logger.debug(f"🎵 Fade-out применен: {fade_samples} сэмплов")
        
        return audio_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка применения fade-out: {e}")
        return audio_data

def detect_silence(audio_data: np.ndarray, threshold: float = 0.01) -> bool:
    """
    Детекция тишины в аудио
    
    Args:
        audio_data: Аудио данные
        threshold: Порог тишины
        
    Returns:
        True если тишина, False если есть звук
    """
    try:
        # Вычисляем RMS (Root Mean Square)
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
        
        is_silent = rms < threshold
        
        logger.debug(f"🔍 Детекция тишины: RMS={rms:.6f}, threshold={threshold}, silent={is_silent}")
        
        return is_silent
        
    except Exception as e:
        logger.error(f"❌ Ошибка детекции тишины: {e}")
        return False

def trim_silence(audio_data: np.ndarray, silence_threshold: float = 0.01, 
                min_silence_duration: int = 1000) -> np.ndarray:
    """
    Обрезка тишины в начале и конце
    
    Args:
        audio_data: Аудио данные
        silence_threshold: Порог тишины
        min_silence_duration: Минимальная длительность тишины для обрезки
        
    Returns:
        Обрезанные аудио данные
    """
    try:
        if len(audio_data) == 0:
            return audio_data
        
        # Находим индексы начала и конца звука
        rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2, axis=1 if len(audio_data.shape) > 1 else 0))
        
        # Находим первый и последний не-тихий сэмпл
        non_silent = rms > silence_threshold
        
        if not np.any(non_silent):
            # Если весь сигнал тихий
            return audio_data[:0] if len(audio_data.shape) == 1 else audio_data[:0, :]
        
        start_idx = np.argmax(non_silent)
        end_idx = len(non_silent) - np.argmax(non_silent[::-1])
        
        # Обрезаем
        trimmed_data = audio_data[start_idx:end_idx]
        
        logger.debug(f"✂️ Обрезка тишины: {len(audio_data)} → {len(trimmed_data)} сэмплов")
        
        return trimmed_data
        
    except Exception as e:
        logger.error(f"❌ Ошибка обрезки тишины: {e}")
        return audio_data
