"""
Конфигурация по умолчанию для распознавания речи

ВАЖНО: Аудио параметры загружаются из централизованной конфигурации.
Используйте get_voice_recognition_config() из config.audio_config
"""

from ..core.types import RecognitionConfig
from config.unified_config_loader import unified_config

def _get_base_audio_config():
    """Получить базовые аудио параметры из централизованной конфигурации"""
    try:
        return unified_config.get_stt_config()
    except Exception:
        # Fallback значения
        return {'sample_rate': 16000, 'channels': 1, 'chunk_size': 1024}

_base_config = _get_base_audio_config()

# Конфигурация по умолчанию
DEFAULT_RECOGNITION_CONFIG = RecognitionConfig(
    # Основные настройки
    language="en-US",  # Только английский
    sample_rate=_base_config['sample_rate'],  # Из централизованной конфигурации
    chunk_size=_base_config['chunk_size'],    # Из централизованной конфигурации  
    channels=_base_config['channels'],        # Из централизованной конфигурации
    dtype='int16',  # STT всегда int16
    
    # Настройки микрофона
    energy_threshold=100,
    dynamic_energy_threshold=True,
    pause_threshold=0.5,
    phrase_threshold=0.3,
    non_speaking_duration=0.3,
    max_duration=30.0,
    
    # Настройки распознавания
    timeout=5.0,
    phrase_timeout=0.3,
    max_alternatives=1,
    show_all=False,
    
    # Дополнительные настройки
    enable_logging=True,
    enable_metrics=True,
    auto_start=True
)

# Конфигурация для высокого качества
HIGH_QUALITY_CONFIG = RecognitionConfig(
    language="en-US",  # Только английский
    sample_rate=_base_config['sample_rate'],  # Из централизованной конфигурации
    chunk_size=2048,  # Специфично для высокого качества
    channels=_base_config['channels'],        # Из централизованной конфигурации
    dtype='int16',  # STT всегда int16
    
    energy_threshold=50,
    dynamic_energy_threshold=True,
    pause_threshold=0.8,
    phrase_threshold=0.5,
    non_speaking_duration=0.5,
    max_duration=60.0,
    
    timeout=10.0,
    phrase_timeout=0.5,
    max_alternatives=3,
    show_all=True,
    
    enable_logging=True,
    enable_metrics=True,
    auto_start=True
)

# Конфигурация для быстрого распознавания
FAST_CONFIG = RecognitionConfig(
    language="en-US",  # Только английский
    sample_rate=_base_config['sample_rate'],  # Из централизованной конфигурации
    chunk_size=512,   # Специфично для быстрого распознавания
    channels=_base_config['channels'],        # Из централизованной конфигурации
    dtype='int16',  # STT всегда int16
    
    energy_threshold=200,
    dynamic_energy_threshold=False,
    pause_threshold=0.3,
    phrase_threshold=0.2,
    non_speaking_duration=0.2,
    max_duration=15.0,
    
    timeout=3.0,
    phrase_timeout=0.2,
    max_alternatives=1,
    show_all=False,
    
    enable_logging=True,
    enable_metrics=True,
    auto_start=True
)

# Словарь конфигураций
CONFIG_PRESETS = {
    "default": DEFAULT_RECOGNITION_CONFIG,
    "high_quality": HIGH_QUALITY_CONFIG,
    "fast": FAST_CONFIG
}

def get_config(preset: str = "default") -> RecognitionConfig:
    """Возвращает конфигурацию по имени пресета"""
    return CONFIG_PRESETS.get(preset, DEFAULT_RECOGNITION_CONFIG)

def create_custom_config(**kwargs) -> RecognitionConfig:
    """Создает пользовательскую конфигурацию"""
    return RecognitionConfig(**kwargs)
