"""
Конфигурация по умолчанию для распознавания речи
"""

from ..core.types import RecognitionConfig

# Конфигурация по умолчанию
DEFAULT_RECOGNITION_CONFIG = RecognitionConfig(
    # Основные настройки
    language="en-US",  # Только английский
    sample_rate=16000,
    chunk_size=1024,
    channels=1,
    dtype='int16',
    
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
    sample_rate=44100,
    chunk_size=2048,
    channels=1,
    dtype='int16',
    
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
    sample_rate=8000,
    chunk_size=512,
    channels=1,
    dtype='int16',
    
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
