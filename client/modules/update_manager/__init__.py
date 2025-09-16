"""
Модуль для управления обновлениями приложения
Использует Sparkle Framework для автоматических обновлений macOS
"""

from .core.update_manager import UpdateManager
from .core.types import UpdateStatus, UpdateInfo, UpdateConfig, UpdateResult, UpdateEvent
from .core.config import UpdateConfigManager
from .macos.sparkle_handler import SparkleHandler

__all__ = [
    'UpdateManager',
    'UpdateStatus', 
    'UpdateInfo',
    'UpdateConfig',
    'UpdateResult',
    'UpdateEvent',
    'UpdateConfigManager',
    'SparkleHandler'
]
