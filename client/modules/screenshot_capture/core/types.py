"""
Типы данных для модуля захвата скриншотов на macOS
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, Tuple
import base64

class ScreenshotFormat(Enum):
    """Поддерживаемые форматы скриншотов (только JPEG для production)"""
    JPEG = "jpeg"
    PNG = "png"  # Не поддерживается в текущей реализации

class ScreenshotQuality(Enum):
    """Уровни качества скриншотов"""
    LOW = "low"           # 50% качество, быстро
    MEDIUM = "medium"     # 75% качество, сбалансированно
    HIGH = "high"         # 90% качество, качественно
    MAXIMUM = "maximum"   # 100% качество, медленно

class ScreenshotRegion(Enum):
    """Регионы захвата скриншотов"""
    FULL_SCREEN = "full_screen"           # Весь экран
    PRIMARY_MONITOR = "primary_monitor"   # Основной монитор
    ACTIVE_WINDOW = "active_window"       # Активное окно
    CUSTOM = "custom"                     # Пользовательский регион

@dataclass
class ScreenshotConfig:
    """Конфигурация для захвата скриншотов"""
    format: ScreenshotFormat = ScreenshotFormat.JPEG
    quality: ScreenshotQuality = ScreenshotQuality.MEDIUM
    region: ScreenshotRegion = ScreenshotRegion.FULL_SCREEN
    custom_region: Optional[Tuple[int, int, int, int]] = None  # (x, y, width, height)
    include_cursor: bool = False
    compress: bool = True
    max_width: Optional[int] = 1280  # Оптимизированный размер
    max_height: Optional[int] = 720  # Оптимизированный размер
    timeout: float = 5.0  # Таймаут в секундах

@dataclass
class ScreenshotData:
    """Данные скриншота"""
    base64_data: str
    format: ScreenshotFormat
    width: int
    height: int
    size_bytes: int
    mime_type: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертирует в словарь для совместимости с text_processor"""
        return {
            "mime_type": self.mime_type,
            "data": self.base64_data,
            "raw_bytes": None,
            "width": self.width,
            "height": self.height,
            "size_bytes": self.size_bytes,
            "format": self.format.value,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ScreenshotData':
        """Создает из словаря"""
        return cls(
            base64_data=data["data"],
            format=ScreenshotFormat(data.get("format", "jpeg")),
            width=data.get("width", 0),
            height=data.get("height", 0),
            size_bytes=data.get("size_bytes", len(data["data"])),
            mime_type=data["mime_type"],
            metadata=data.get("metadata", {})
        )

@dataclass
class ScreenInfo:
    """Информация об экране"""
    width: int
    height: int
    scale_factor: float = 1.0
    color_depth: int = 24
    refresh_rate: int = 60
    primary: bool = True
    monitor_name: str = "Unknown"

@dataclass
class ScreenshotResult:
    """Результат захвата скриншота"""
    success: bool
    data: Optional[ScreenshotData] = None
    error: Optional[str] = None
    screen_info: Optional[ScreenInfo] = None
    capture_time: float = 0.0  # Время захвата в секундах
    
    def is_valid(self) -> bool:
        """Проверяет валидность результата"""
        return self.success and self.data is not None and self.data.base64_data

class ScreenshotError(Exception):
    """Базовое исключение для модуля скриншотов"""
    pass

class ScreenshotPermissionError(ScreenshotError):
    """Ошибка прав доступа к экрану"""
    pass

class ScreenshotCaptureError(ScreenshotError):
    """Ошибка захвата скриншота"""
    pass

class ScreenshotFormatError(ScreenshotError):
    """Ошибка формата скриншота"""
    pass

class ScreenshotTimeoutError(ScreenshotError):
    """Ошибка таймаута захвата"""
    pass
