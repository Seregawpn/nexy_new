"""
Autostart Manager Module

Модуль для управления автозапуском приложения.
"""

from .core.autostart_manager import AutostartManager
from .core.types import AutostartStatus, AutostartConfig
from .core.config import AutostartConfig as Config

__all__ = [
    'AutostartManager',
    'AutostartStatus',
    'AutostartConfig', 
    'Config'
]

