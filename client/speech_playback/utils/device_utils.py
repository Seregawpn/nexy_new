"""
Device Utils - Утилиты для работы с аудио устройствами
"""

import logging
import sounddevice as sd
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class AudioDevice:
    """Информация об аудио устройстве"""
    name: str
    portaudio_index: int
    channels: int
    sample_rate: float
    is_default: bool = False
    is_input: bool = False
    is_output: bool = True

def get_available_devices() -> List[AudioDevice]:
    """
    Получает список доступных аудио устройств
    
    Returns:
        Список AudioDevice объектов
    """
    try:
        devices = []
        device_list = sd.query_devices()
        
        for i, device_info in enumerate(device_list):
            # Проверяем, что устройство поддерживает вывод
            if device_info['max_output_channels'] > 0:
                device = AudioDevice(
                    name=device_info['name'],
                    portaudio_index=i,
                    channels=device_info['max_output_channels'],
                    sample_rate=device_info['default_samplerate'],
                    is_default=(i == sd.default.device[1]),  # default output device
                    is_input=device_info['max_input_channels'] > 0,
                    is_output=device_info['max_output_channels'] > 0
                )
                devices.append(device)
        
        logger.info(f"🎵 Найдено {len(devices)} аудио устройств")
        return devices
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка устройств: {e}")
        return []

def get_best_audio_device() -> Optional[AudioDevice]:
    """
    Выбирает лучшее аудио устройство для воспроизведения
    
    Returns:
        Лучшее AudioDevice или None
    """
    try:
        devices = get_available_devices()
        
        if not devices:
            logger.warning("⚠️ Нет доступных аудио устройств")
            return None
        
        # Приоритет выбора:
        # 1. Устройство по умолчанию
        # 2. Устройство с наибольшим количеством каналов
        # 3. Первое доступное устройство
        
        # Ищем устройство по умолчанию
        default_device = None
        for device in devices:
            if device.is_default:
                default_device = device
                break
        
        if default_device:
            logger.info(f"🎵 Выбрано устройство по умолчанию: {default_device.name}")
            return default_device
        
        # Ищем устройство с наибольшим количеством каналов
        best_device = max(devices, key=lambda d: d.channels)
        logger.info(f"🎵 Выбрано устройство с лучшими характеристиками: {best_device.name} ({best_device.channels} каналов)")
        
        return best_device
        
    except Exception as e:
        logger.error(f"❌ Ошибка выбора аудио устройства: {e}")
        return None

def test_audio_device(device_id: int) -> bool:
    """
    Тестирует аудио устройство
    
    Args:
        device_id: ID устройства для тестирования
        
    Returns:
        True если устройство работает, False иначе
    """
    try:
        # Генерируем тестовый сигнал
        import numpy as np
        sample_rate = 44100
        duration = 0.1  # 100ms
        frequency = 440  # A4
        
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        test_audio = np.sin(2 * np.pi * frequency * t)
        test_audio = (test_audio * 0.1).astype(np.float32)  # Тихий тест
        
        # Пробуем воспроизвести
        sd.play(test_audio, samplerate=sample_rate, device=device_id)
        sd.wait()  # Ждем завершения
        
        logger.info(f"✅ Устройство {device_id} работает корректно")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования устройства {device_id}: {e}")
        return False

def get_device_info(device_id: int) -> Optional[Dict[str, Any]]:
    """
    Получает подробную информацию об устройстве
    
    Args:
        device_id: ID устройства
        
    Returns:
        Словарь с информацией об устройстве или None
    """
    try:
        device_info = sd.query_devices(device_id)
        
        info = {
            'name': device_info['name'],
            'index': device_id,
            'channels_in': device_info['max_input_channels'],
            'channels_out': device_info['max_output_channels'],
            'sample_rate': device_info['default_samplerate'],
            'is_default': device_id == sd.default.device[1],
            'host_api': device_info['hostapi']
        }
        
        return info
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения информации об устройстве {device_id}: {e}")
        return None
