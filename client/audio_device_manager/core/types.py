"""
Типы данных для модуля управления аудио устройствами
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class DeviceType(Enum):
    """Типы аудио устройств"""
    INPUT = "input"      # Микрофоны, встроенный микрофон
    OUTPUT = "output"    # Наушники, колонки, встроенные динамики
    BOTH = "both"        # Гарнитуры, USB устройства


class DevicePriority(Enum):
    """Приоритеты устройств"""
    HIGHEST = 1          # Bluetooth наушники, AirPods
    HIGH = 2             # Гарнитуры, USB наушники
    MEDIUM = 3           # Беспроводные устройства
    NORMAL = 4           # Внешние колонки
    LOW = 5              # USB аудио устройства
    LOWEST = 6           # Встроенные динамики, микрофон


class DeviceStatus(Enum):
    """Статусы устройств"""
    AVAILABLE = "available"      # Доступно для использования
    UNAVAILABLE = "unavailable"  # Недоступно
    BUSY = "busy"                # Занято другим приложением
    ERROR = "error"              # Ошибка устройства


@dataclass
class AudioDevice:
    """Аудио устройство"""
    id: str
    name: str
    type: DeviceType
    is_default: bool = False
    is_available: bool = True
    status: DeviceStatus = DeviceStatus.AVAILABLE
    priority: DevicePriority = DevicePriority.NORMAL
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    last_seen: Optional[datetime] = None
    
    def __str__(self) -> str:
        return f"{self.name} ({self.type.value})"
    
    def __repr__(self) -> str:
        return f"AudioDevice(id='{self.id}', name='{self.name}', type={self.type.value})"


@dataclass
class DeviceChange:
    """Изменение в устройствах"""
    added: List[AudioDevice]
    removed: List[AudioDevice]
    current_devices: Dict[str, AudioDevice]
    timestamp: datetime
    change_type: str  # "connected", "disconnected", "updated"
    
    def __str__(self) -> str:
        return f"DeviceChange(added={len(self.added)}, removed={len(self.removed)})"


@dataclass
class DeviceMetrics:
    """Метрики устройств"""
    total_devices: int = 0
    available_devices: int = 0
    unavailable_devices: int = 0
    total_switches: int = 0
    successful_switches: int = 0
    failed_switches: int = 0
    last_switch_time: Optional[datetime] = None
    average_switch_time: float = 0.0
    most_used_device: Optional[str] = None


@dataclass
class AudioDeviceManagerConfig:
    """Конфигурация менеджера аудио устройств"""
    auto_switch_enabled: bool = True
    monitoring_interval: float = 1.0
    switch_delay: float = 0.5
    device_priorities: Dict[str, int] = None
    user_preferences: Dict[str, Any] = None
    macos_settings: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.device_priorities is None:
            self.device_priorities = {
                'bluetooth_headphones': 1,
                'usb_headset': 2,
                'wireless_headphones': 3,
                'external_speakers': 4,
                'usb_audio': 5,
                'dock_station': 6,
                'builtin_speakers': 7,
                'builtin_microphone': 8,
                'default_device': 9
            }
        
        if self.user_preferences is None:
            self.user_preferences = {
                'preferred_devices': [],
                'blacklisted_devices': [],
                'auto_switch_delay': 0.5,
                'remember_user_choice': True
            }
        
        if self.macos_settings is None:
            self.macos_settings = {
                'use_switchaudio': True,
                'switchaudio_path': '/usr/local/bin/SwitchAudioSource',
                'core_audio_timeout': 5.0,
                'enable_notifications': True
            }


# Callback типы
DeviceChangeCallback = Callable[[DeviceChange], None]
DeviceSwitchCallback = Callable[[AudioDevice, bool], None]  # device, success
ErrorCallback = Callable[[Exception, str], None]  # error, context
MetricsCallback = Callable[[DeviceMetrics], None]
