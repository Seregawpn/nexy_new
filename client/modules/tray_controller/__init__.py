"""
Tray Controller Module для macOS
Управление иконкой в меню-баре и отображение статуса приложения
"""

from .core.tray_controller import TrayController
from .core.tray_types import TrayIcon, TrayMenu, TrayStatus, TrayConfig
from .core.tray_types import TrayConfig

__all__ = [
    'TrayController',
    'TrayIcon', 
    'TrayMenu',
    'TrayStatus',
    'TrayConfig',
]

__version__ = "1.0.0"
__author__ = "Nexy Team"








