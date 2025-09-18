"""
Централизованная конфигурация аудио для всего проекта Nexy
==========================================================

ЕДИНЫЙ ИСТОЧНИК ИСТИНЫ для всех аудио настроек:
- Speech Playback (воспроизведение TTS)
- Voice Recognition (распознавание речи)
- Audio Device Management (управление устройствами)
- gRPC Audio Streaming (передача аудио)

Все модули должны использовать ТОЛЬКО этот класс для получения аудио настроек.
"""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import numpy as np

from .unified_config_loader import UnifiedConfigLoader

logger = logging.getLogger(__name__)

@dataclass
class AudioConfig:
    """
    Централизованная конфигурация аудио для всего проекта
    
    Загружается из unified_config.yaml и предоставляет единый интерфейс
    для всех аудио компонентов проекта.
    """
    
    # === ОСНОВНЫЕ ПАРАМЕТРЫ ===
    sample_rate: int = 48000
    channels: int = 1  
    format: str = 'int16'  # int16 | float32
    chunk_size: int = 1024
    buffer_size: int = 512
    
    # === УСТРОЙСТВА ===
    follow_system_default: bool = False
    auto_switch_to_best: bool = True
    auto_switch_to_headphones: bool = True
    preflush_on_switch: bool = False
    settle_ms: int = 100
    retries: int = 2
    
    # === ПРОИЗВОДИТЕЛЬНОСТЬ ===
    max_memory_mb: int = 256
    use_coreaudio_listeners: bool = True
    
    # === УСТРОЙСТВА - ПРИОРИТЕТЫ ===
    device_priorities: Dict[str, int] = None
    
    # === УСТРОЙСТВА - МОНИТОРИНГ ===
    monitoring_interval: float = 3.0
    switch_cooldown: float = 2.0
    cache_timeout: float = 5.0
    exclude_virtual_devices: bool = True
    virtual_device_keywords: List[str] = None
    
    def __post_init__(self):
        """Инициализация значений по умолчанию"""
        if self.device_priorities is None:
            self.device_priorities = {
                'airpods': 100,
                'beats': 95,
                'bluetooth_headphones': 90,
                'usb_headphones': 85,
                'bluetooth_speakers': 70,
                'usb_audio': 60,
                'system_speakers': 40,
                'built_in': 20,
                'other': 10,
                'microphone': 5,
                'virtual_device': 1
            }
        
        if self.virtual_device_keywords is None:
            self.virtual_device_keywords = [
                'blackhole', 'soundflower', 'loopback', 'virtual',
                'aggregate', 'multi-output', 'sound source', 'audio hijack'
            ]
    
    @property
    def numpy_dtype(self) -> np.dtype:
        """Получить numpy dtype для аудио данных"""
        if self.format.lower() in ('int16', 'short'):
            return np.int16
        elif self.format.lower() in ('float32', 'float'):
            return np.float32
        else:
            logger.warning(f"Неизвестный аудио формат: {self.format}, используем int16")
            return np.int16
    
    @property
    def sounddevice_dtype(self) -> str:
        """Получить dtype для sounddevice"""
        return self.format
    
    @property
    def bytes_per_sample(self) -> int:
        """Количество байт на сэмпл"""
        if self.format.lower() in ('int16', 'short'):
            return 2
        elif self.format.lower() in ('float32', 'float'):
            return 4
        else:
            return 2
    
    @property
    def max_value(self) -> float:
        """Максимальное значение для данного формата"""
        if self.format.lower() in ('int16', 'short'):
            return 32767.0
        elif self.format.lower() in ('float32', 'float'):
            return 1.0
        else:
            return 32767.0
    
    @property
    def min_value(self) -> float:
        """Минимальное значение для данного формата"""
        if self.format.lower() in ('int16', 'short'):
            return -32768.0
        elif self.format.lower() in ('float32', 'float'):
            return -1.0
        else:
            return -32768.0
    
    def validate(self) -> bool:
        """Валидация конфигурации"""
        try:
            # Проверка sample_rate
            if not (8000 <= self.sample_rate <= 192000):
                logger.error(f"Недопустимая частота дискретизации: {self.sample_rate}")
                return False
            
            # Проверка channels
            if not (1 <= self.channels <= 8):
                logger.error(f"Недопустимое количество каналов: {self.channels}")
                return False
            
            # Проверка format
            if self.format.lower() not in ('int16', 'short', 'float32', 'float'):
                logger.error(f"Недопустимый формат: {self.format}")
                return False
            
            # Проверка размеров буферов
            if not (64 <= self.chunk_size <= 8192):
                logger.warning(f"Необычный размер чанка: {self.chunk_size}")
            
            if not (64 <= self.buffer_size <= 8192):
                logger.warning(f"Необычный размер буфера: {self.buffer_size}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка валидации аудио конфигурации: {e}")
            return False
    
    def get_speech_playback_config(self) -> Dict[str, Any]:
        """Получить конфигурацию для модуля speech_playback"""
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'dtype': self.format,
            'buffer_size': self.buffer_size,
            'max_memory_mb': self.max_memory_mb,
            'auto_device_selection': self.auto_switch_to_best
        }
    
    def get_voice_recognition_config(self) -> Dict[str, Any]:
        """Получить конфигурацию для модуля voice_recognition"""
        return {
            'sample_rate': 16000,  # STT использует 16kHz
            'channels': 1,  # STT всегда моно
            'chunk_size': self.chunk_size
        }
    
    def get_audio_device_config(self) -> Dict[str, Any]:
        """Получить конфигурацию для модуля audio_device_manager"""
        return {
            'auto_switch_to_best': self.auto_switch_to_best,
            'auto_switch_to_headphones': self.auto_switch_to_headphones,
            'monitoring_interval': self.monitoring_interval,
            'switch_cooldown': self.switch_cooldown,
            'cache_timeout': self.cache_timeout,
            'device_priorities': self.device_priorities.copy(),
            'exclude_virtual_devices': self.exclude_virtual_devices,
            'virtual_device_keywords': self.virtual_device_keywords.copy(),
            'preflush_on_switch': self.preflush_on_switch,
            'settle_ms': self.settle_ms,
            'retries': self.retries,
            'use_coreaudio_listeners': self.use_coreaudio_listeners
        }
    
    def get_grpc_audio_config(self) -> Dict[str, Any]:
        """Получить конфигурацию для gRPC аудио стриминга"""
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'format': self.format,
            'chunk_size': self.chunk_size
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для логирования/отладки"""
        return {
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'format': self.format,
            'chunk_size': self.chunk_size,
            'buffer_size': self.buffer_size,
            'max_memory_mb': self.max_memory_mb,
            'numpy_dtype': str(self.numpy_dtype),
            'bytes_per_sample': self.bytes_per_sample,
            'max_value': self.max_value,
            'min_value': self.min_value
        }


# === ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР ===
_global_audio_config: Optional[AudioConfig] = None

def get_audio_config() -> AudioConfig:
    """
    Получить глобальный экземпляр аудио конфигурации
    
    Загружается из unified_config.yaml при первом вызове.
    Все последующие вызовы возвращают кешированный экземпляр.
    
    Returns:
        AudioConfig: Централизованная конфигурация аудио
    """
    global _global_audio_config
    
    if _global_audio_config is None:
        _global_audio_config = load_audio_config()
    
    return _global_audio_config

def load_audio_config() -> AudioConfig:
    """
    Загрузить аудио конфигурацию из unified_config.yaml
    
    Returns:
        AudioConfig: Конфигурация аудио
    """
    try:
        # Загружаем unified_config.yaml
        config_loader = UnifiedConfigLoader()
        config = config_loader._load_config()
        audio_section = config.get('audio', {})
        
        # Создаем AudioConfig с данными из файла
        audio_config = AudioConfig(
            sample_rate=audio_section.get('sample_rate', 48000),
            channels=audio_section.get('channels', 1),
            format=audio_section.get('format', 'int16'),
            chunk_size=audio_section.get('chunk_size', 1024),
            buffer_size=audio_section.get('buffer_size', 512),
            
            follow_system_default=audio_section.get('follow_system_default', False),
            auto_switch_to_best=audio_section.get('device_manager', {}).get('auto_switch_to_best', True),
            auto_switch_to_headphones=audio_section.get('device_manager', {}).get('auto_switch_to_headphones', True),
            preflush_on_switch=audio_section.get('preflush_on_switch', False),
            settle_ms=audio_section.get('settle_ms', 100),
            retries=audio_section.get('retries', 2),
            
            max_memory_mb=config.get('performance', {}).get('max_memory', '512MB').replace('MB', '').replace('mb', ''),
            use_coreaudio_listeners=audio_section.get('use_coreaudio_listeners', True),
            
            monitoring_interval=audio_section.get('device_manager', {}).get('monitoring_interval', 3.0),
            switch_cooldown=audio_section.get('device_manager', {}).get('switch_cooldown', 2.0),
            cache_timeout=audio_section.get('device_manager', {}).get('cache_timeout', 5.0),
            exclude_virtual_devices=audio_section.get('device_manager', {}).get('exclude_virtual_devices', True),
            virtual_device_keywords=audio_section.get('device_manager', {}).get('virtual_device_keywords', []),
            device_priorities=audio_section.get('device_manager', {}).get('device_priorities', {})
        )
        
        # Конвертируем max_memory в int если это строка
        if isinstance(audio_config.max_memory_mb, str):
            try:
                audio_config.max_memory_mb = int(audio_config.max_memory_mb.replace('MB', '').replace('mb', ''))
            except ValueError:
                audio_config.max_memory_mb = 256
        
        # Валидация
        if not audio_config.validate():
            logger.warning("Аудио конфигурация не прошла валидацию, используем значения по умолчанию")
            audio_config = AudioConfig()  # Fallback к defaults
        
        logger.info(f"✅ Аудио конфигурация загружена: {audio_config.to_dict()}")
        return audio_config
        
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки аудио конфигурации: {e}")
        logger.info("🔄 Используем конфигурацию по умолчанию")
        return AudioConfig()  # Fallback к defaults

def reload_audio_config() -> AudioConfig:
    """
    Принудительно перезагрузить аудио конфигурацию
    
    Returns:
        AudioConfig: Обновленная конфигурация
    """
    global _global_audio_config
    _global_audio_config = None
    return get_audio_config()

# === УТИЛИТЫ ===

def convert_audio_format(data: np.ndarray, target_format: str) -> np.ndarray:
    """
    Конвертировать аудио данные в целевой формат
    
    Args:
        data: Исходные аудио данные
        target_format: Целевой формат ('int16' или 'float32')
    
    Returns:
        np.ndarray: Конвертированные данные
    """
    if target_format.lower() in ('int16', 'short'):
        if data.dtype == np.float32:
            return np.clip(data, -1.0, 1.0) * 32767.0
        elif data.dtype != np.int16:
            return data.astype(np.int16)
        else:
            return data
    
    elif target_format.lower() in ('float32', 'float'):
        if data.dtype == np.int16:
            return data.astype(np.float32) / 32767.0
        elif data.dtype != np.float32:
            return data.astype(np.float32)
        else:
            return data
    
    else:
        logger.warning(f"Неизвестный целевой формат: {target_format}")
        return data

def normalize_audio_data(data: np.ndarray, target_format: str) -> np.ndarray:
    """
    Нормализовать аудио данные под целевой формат
    
    Args:
        data: Аудио данные
        target_format: Целевой формат
    
    Returns:
        np.ndarray: Нормализованные данные
    """
    try:
        if target_format.lower() in ('int16', 'short'):
            # Нормализуем в диапазон int16
            if data.dtype == np.float32:
                return np.clip(data * 32767.0, -32768, 32767).astype(np.int16)
            else:
                return np.clip(data, -32768, 32767).astype(np.int16)
        
        elif target_format.lower() in ('float32', 'float'):
            # Нормализуем в диапазон [-1.0, 1.0]
            if data.dtype == np.int16:
                return np.clip(data.astype(np.float32) / 32767.0, -1.0, 1.0)
            else:
                return np.clip(data, -1.0, 1.0).astype(np.float32)
        
        else:
            return data
            
    except Exception as e:
        logger.error(f"Ошибка нормализации аудио: {e}")
        return data
