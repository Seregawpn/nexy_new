"""
Утилиты для работы с аудио в распознавании речи
"""

import numpy as np
import sounddevice as sd
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def normalize_audio(audio_data: np.ndarray, target_dtype: np.dtype = np.int16) -> np.ndarray:
    """Нормализует аудио данные"""
    try:
        if audio_data.dtype != target_dtype:
            # Конвертируем в float32 для нормализации
            if audio_data.dtype == np.int16:
                audio_float = audio_data.astype(np.float32) / 32767.0
            elif audio_data.dtype == np.int32:
                audio_float = audio_data.astype(np.float32) / 2147483647.0
            else:
                audio_float = audio_data.astype(np.float32)
            
            # Нормализуем
            max_val = np.max(np.abs(audio_float))
            if max_val > 0:
                audio_float = audio_float / max_val
            
            # Конвертируем в целевой тип
            if target_dtype == np.int16:
                return (audio_float * 32767).astype(np.int16)
            elif target_dtype == np.int32:
                return (audio_float * 2147483647).astype(np.int32)
            else:
                return audio_float.astype(target_dtype)
        else:
            return audio_data
            
    except Exception as e:
        logger.error(f"❌ Ошибка нормализации аудио: {e}")
        return audio_data

def resample_audio(audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
    """Изменяет частоту дискретизации аудио"""
    try:
        if original_rate == target_rate:
            return audio_data
            
        # Простое изменение частоты дискретизации
        ratio = target_rate / original_rate
        new_length = int(len(audio_data) * ratio)
        
        # Линейная интерполяция
        indices = np.linspace(0, len(audio_data) - 1, new_length)
        return np.interp(indices, np.arange(len(audio_data)), audio_data).astype(audio_data.dtype)
        
    except Exception as e:
        logger.error(f"❌ Ошибка изменения частоты дискретизации: {e}")
        return audio_data

def convert_channels(audio_data: np.ndarray, target_channels: int) -> np.ndarray:
    """Конвертирует количество каналов аудио"""
    try:
        if len(audio_data.shape) == 1:
            # Моно в стерео
            if target_channels == 2:
                return np.column_stack((audio_data, audio_data))
            else:
                return audio_data
        elif len(audio_data.shape) == 2:
            current_channels = audio_data.shape[1]
            if current_channels == target_channels:
                return audio_data
            elif current_channels == 1 and target_channels == 2:
                return np.column_stack((audio_data[:, 0], audio_data[:, 0]))
            elif current_channels == 2 and target_channels == 1:
                return np.mean(audio_data, axis=1)
            else:
                return audio_data
        else:
            return audio_data
            
    except Exception as e:
        logger.error(f"❌ Ошибка конвертации каналов: {e}")
        return audio_data

def detect_silence(audio_data: np.ndarray, threshold: float = 0.01) -> List[Tuple[int, int]]:
    """Обнаруживает тишину в аудио"""
    try:
        # Вычисляем энергию сигнала
        if len(audio_data.shape) == 2:
            energy = np.sqrt(np.mean(audio_data ** 2, axis=1))
        else:
            energy = np.abs(audio_data)
            
        # Находим участки тишины
        silence_mask = energy < threshold
        silence_regions = []
        
        in_silence = False
        start = 0
        
        for i, is_silent in enumerate(silence_mask):
            if is_silent and not in_silence:
                start = i
                in_silence = True
            elif not is_silent and in_silence:
                silence_regions.append((start, i))
                in_silence = False
                
        if in_silence:
            silence_regions.append((start, len(silence_mask)))
            
        return silence_regions
        
    except Exception as e:
        logger.error(f"❌ Ошибка обнаружения тишины: {e}")
        return []

def trim_silence(audio_data: np.ndarray, threshold: float = 0.01) -> np.ndarray:
    """Удаляет тишину с начала и конца аудио"""
    try:
        silence_regions = detect_silence(audio_data, threshold)
        
        if not silence_regions:
            return audio_data
            
        # Удаляем тишину с начала
        start_idx = 0
        for start, end in silence_regions:
            if start == 0:
                start_idx = end
            else:
                break
                
        # Удаляем тишину с конца
        end_idx = len(audio_data)
        for start, end in reversed(silence_regions):
            if end == len(audio_data):
                end_idx = start
            else:
                break
                
        return audio_data[start_idx:end_idx]
        
    except Exception as e:
        logger.error(f"❌ Ошибка удаления тишины: {e}")
        return audio_data

def get_audio_info(audio_data: np.ndarray, sample_rate: int) -> dict:
    """Возвращает информацию об аудио"""
    try:
        duration = len(audio_data) / sample_rate
        channels = 1 if len(audio_data.shape) == 1 else audio_data.shape[1]
        
        return {
            "duration": duration,
            "sample_rate": sample_rate,
            "channels": channels,
            "samples": len(audio_data),
            "dtype": str(audio_data.dtype),
            "shape": audio_data.shape
        }
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации об аудио: {e}")
        return {}

def list_audio_devices() -> List[dict]:
    """Возвращает список доступных аудио устройств"""
    try:
        devices = sd.query_devices()
        device_list = []
        
        for i, device in enumerate(devices):
            device_info = {
                "index": i,
                "name": device["name"],
                "channels": device["max_input_channels"],
                "sample_rate": device["default_samplerate"],
                "is_input": device["max_input_channels"] > 0,
                "is_output": device["max_output_channels"] > 0
            }
            device_list.append(device_info)
            
        return device_list
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка устройств: {e}")
        return []

def find_best_microphone() -> Optional[int]:
    """Находит лучшее микрофонное устройство"""
    try:
        devices = list_audio_devices()
        input_devices = [d for d in devices if d["is_input"]]
        
        if not input_devices:
            return None
            
        # Ищем устройство с наибольшим количеством каналов
        best_device = max(input_devices, key=lambda x: x["channels"])
        return best_device["index"]
        
    except Exception as e:
        logger.error(f"❌ Ошибка поиска лучшего микрофона: {e}")
        return None
