"""
Модуль захвата скриншотов для macOS
"""

from .core.screenshot_capture import ScreenshotCapture
from .core.types import (
    ScreenshotConfig,
    ScreenshotData,
    ScreenshotResult,
    ScreenshotFormat,
    ScreenshotQuality,
    ScreenshotRegion,
    ScreenInfo,
    ScreenshotError,
    ScreenshotPermissionError,
    ScreenshotCaptureError,
    ScreenshotFormatError,
    ScreenshotTimeoutError
)

__all__ = [
    # Основные классы
    'ScreenshotCapture',
    # глобальные синглтоны удалены
    
    # Типы данных
    'ScreenshotConfig',
    'ScreenshotData',
    'ScreenshotResult',
    'ScreenshotFormat',
    'ScreenshotQuality',
    'ScreenshotRegion',
    'ScreenInfo',
    
    # Исключения
    'ScreenshotError',
    'ScreenshotPermissionError',
    'ScreenshotCaptureError',
    'ScreenshotFormatError',
    'ScreenshotTimeoutError',
    
]

# Версия модуля
__version__ = "1.0.0"
__author__ = "Nexy Development Team"
__description__ = "Модуль захвата скриншотов для macOS с поддержкой JPEG"
