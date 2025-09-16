"""
Модуль управления аудио устройствами для macOS

Этот модуль предоставляет:
- Автоматическое переключение аудио устройств
- Мониторинг подключения/отключения устройств
- Управление приоритетами устройств
- Интеграцию с Core Audio и SwitchAudio
- Поддержку Bluetooth наушников и внешних устройств
"""

from .core.device_manager import AudioDeviceManager
from .core.types import (
    AudioDevice, DeviceChange, DeviceType, DeviceStatus, DevicePriority,
    DeviceMetrics, AudioDeviceManagerConfig,
    DeviceChangeCallback, DeviceSwitchCallback, ErrorCallback, MetricsCallback
)
from .config.device_priorities import (
    get_device_priority, is_headphone_device, is_speaker_device,
    is_external_device, is_builtin_device, get_device_type_from_name
)

# Версия модуля
__version__ = "1.0.0"

# Экспортируемые классы и функции
__all__ = [
    # Основные классы
    "AudioDeviceManager",
    
    # Типы данных
    "AudioDevice",
    "DeviceChange", 
    "DeviceType",
    "DeviceStatus",
    "DevicePriority",
    "DeviceMetrics",
    "AudioDeviceManagerConfig",
    
    # Callback типы
    "DeviceChangeCallback",
    "DeviceSwitchCallback", 
    "ErrorCallback",
    "MetricsCallback",
    
    # Утилиты
    "get_device_priority",
    "is_headphone_device",
    "is_speaker_device", 
    "is_external_device",
    "is_builtin_device",
    "get_device_type_from_name",
    
    # Версия
    "__version__"
]


def create_audio_device_manager(config: dict = None) -> AudioDeviceManager:
    """
    Создает экземпляр AudioDeviceManager с конфигурацией
    
    Args:
        config: Словарь конфигурации (опционально)
        
    Returns:
        AudioDeviceManager: Экземпляр менеджера устройств
    """
    from .core.types import AudioDeviceManagerConfig
    
    if config:
        manager_config = AudioDeviceManagerConfig(**config)
    else:
        manager_config = AudioDeviceManagerConfig()
    
    return AudioDeviceManager(manager_config)


def create_default_audio_device_manager() -> AudioDeviceManager:
    """
    Создает AudioDeviceManager с конфигурацией по умолчанию
    
    Returns:
        AudioDeviceManager: Экземпляр менеджера устройств
    """
    return create_audio_device_manager()


def create_audio_device_manager_with_priorities(priorities: dict) -> AudioDeviceManager:
    """
    Создает AudioDeviceManager с пользовательскими приоритетами
    
    Args:
        priorities: Словарь приоритетов устройств
        
    Returns:
        AudioDeviceManager: Экземпляр менеджера устройств
    """
    config = {
        'device_priorities': priorities
    }
    return create_audio_device_manager(config)
