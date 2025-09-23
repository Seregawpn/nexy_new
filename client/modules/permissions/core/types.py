"""
Типы данных для модуля permissions
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Callable
from enum import Enum
import time


class PermissionType(Enum):
    """Типы разрешений"""
    MICROPHONE = "microphone"
    SCREEN_CAPTURE = "screen_capture"
    CAMERA = "camera"
    NETWORK = "network"
    NOTIFICATIONS = "notifications"
    ACCESSIBILITY = "accessibility"  # Добавлено для Accessibility


class PermissionStatus(Enum):
    """Статусы разрешений"""
    GRANTED = "granted"
    DENIED = "denied"
    NOT_DETERMINED = "not_determined"
    ERROR = "error"


@dataclass
class PermissionInfo:
    """Информация о разрешении"""
    permission_type: PermissionType
    status: PermissionStatus
    granted: bool
    message: str
    last_checked: float
    error: Optional[Exception] = None


@dataclass
class PermissionResult:
    """Результат проверки разрешения"""
    success: bool
    permission: PermissionType
    status: PermissionStatus
    message: str
    error: Optional[Exception] = None


@dataclass
class PermissionEvent:
    """Событие разрешения"""
    event_type: str
    permission: PermissionType
    status: PermissionStatus
    message: str
    timestamp: float
    data: Optional[Dict] = None


@dataclass
class PermissionState:
    """Состояние разрешений"""
    permissions: Dict[PermissionType, PermissionInfo]
    last_updated: float
    
    def get_permission(self, permission_type: PermissionType) -> Optional[PermissionInfo]:
        """Получить информацию о разрешении"""
        return self.permissions.get(permission_type)
    
    def set_permission(self, permission_type: PermissionType, info: PermissionInfo):
        """Установить информацию о разрешении"""
        self.permissions[permission_type] = info
        self.last_updated = time.time()
    
    def is_granted(self, permission_type: PermissionType) -> bool:
        """Проверить, предоставлено ли разрешение"""
        info = self.get_permission(permission_type)
        return info is not None and info.granted
    
    def get_granted_permissions(self) -> List[PermissionType]:
        """Получить список предоставленных разрешений"""
        return [
            perm_type for perm_type, info in self.permissions.items()
            if info.granted
        ]
    
    def get_denied_permissions(self) -> List[PermissionType]:
        """Получить список отклоненных разрешений"""
        return [
            perm_type for perm_type, info in self.permissions.items()
            if not info.granted and info.status != PermissionStatus.ERROR
        ]
    
    def get_error_permissions(self) -> List[PermissionType]:
        """Получить список разрешений с ошибками"""
        return [
            perm_type for perm_type, info in self.permissions.items()
            if info.status == PermissionStatus.ERROR
        ]


@dataclass
class PermissionConfig:
    """Конфигурация разрешений"""
    auto_open_preferences: bool = True
    check_interval: float = 30.0
    required_permissions: List[PermissionType] = None
    retry_attempts: int = 3
    retry_delay: float = 5.0
    show_instructions: bool = True
    
    def __post_init__(self):
        if self.required_permissions is None:
            self.required_permissions = [
                PermissionType.MICROPHONE,
                PermissionType.SCREEN_CAPTURE,
                PermissionType.ACCESSIBILITY,  # Добавлено
            ]


@dataclass
class PermissionManagerState:
    """Состояние менеджера разрешений"""
    is_running: bool = False
    is_initialized: bool = False
    last_check: float = 0.0
    total_checks: int = 0
    successful_checks: int = 0
    failed_checks: int = 0
    permissions: Dict[PermissionType, PermissionInfo] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {}
    
    def get_permission(self, permission_type: PermissionType) -> Optional[PermissionInfo]:
        """Получить информацию о разрешении"""
        return self.permissions.get(permission_type)
    
    def set_permission(self, permission_type: PermissionType, info: PermissionInfo):
        """Установить информацию о разрешении"""
        self.permissions[permission_type] = info
        self.last_check = time.time()
    
    async def notify_callbacks(self, event: 'PermissionEvent'):
        """Уведомить callbacks о событии (заглушка)"""
        # Метод-заглушка для совместимости
        pass
