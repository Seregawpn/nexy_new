"""
Конфигурация модуля управления аудио устройствами
"""

from .device_priorities import (
    DEFAULT_DEVICE_PRIORITIES,
    DEVICE_TYPE_KEYWORDS,
    PRIORITY_KEYWORDS,
    get_device_priority,
    is_headphone_device,
    is_speaker_device,
    is_external_device,
    is_builtin_device,
    get_device_type_from_name,
    sort_devices_by_priority,
    get_priority_name
)

__all__ = [
    "DEFAULT_DEVICE_PRIORITIES",
    "DEVICE_TYPE_KEYWORDS", 
    "PRIORITY_KEYWORDS",
    "get_device_priority",
    "is_headphone_device",
    "is_speaker_device",
    "is_external_device",
    "is_builtin_device",
    "get_device_type_from_name",
    "sort_devices_by_priority",
    "get_priority_name"
]
