"""
Permissions Module для macOS
Управление разрешениями системы
"""

from .core.permissions_manager import PermissionManager
from .core.types import (
    PermissionType, PermissionStatus, PermissionInfo, PermissionResult,
    PermissionEvent, PermissionConfig, PermissionManagerState
)
from .core.config import PermissionConfigManager

__all__ = [
    'PermissionManager',
    'PermissionType',
    'PermissionStatus', 
    'PermissionInfo',
    'PermissionResult',
    'PermissionEvent',
    'PermissionConfig',
    'PermissionManagerState',
    'PermissionConfigManager'
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
