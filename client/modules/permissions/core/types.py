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


class PermissionStatus(Enum):
    """Статусы разрешений"""
    GRANTED = "granted"
    DENIED = "denied"
    NOT_DETERMINED = "not_determined"
    ERROR = "error"


@dataclass
class PermissionInfo:
    """Информация о разрешении"""
    type: PermissionType
    status: PermissionStatus
    required: bool
    description: str
    instructions: str
    last_checked: Optional[float] = None


@dataclass
class PermissionResult:
    """Результат проверки/запроса разрешения"""
    success: bool
    permission: PermissionType
    status: PermissionStatus
    message: str
    error: Optional[Exception] = None


@dataclass
class PermissionEvent:
    """Событие изменения разрешения"""
    permission: PermissionType
    old_status: PermissionStatus
    new_status: PermissionStatus
    timestamp: float


@dataclass
class PermissionConfig:
    """Конфигурация разрешений"""
    required_permissions: List[PermissionType]
    check_interval: int = 30
    auto_open_preferences: bool = True
    show_instructions: bool = True


@dataclass
class PermissionManagerState:
    """Состояние менеджера разрешений"""
    permissions: Dict[PermissionType, PermissionInfo] = None
    callbacks: List[Callable[[PermissionEvent], None]] = None
    config: Optional[PermissionConfig] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = {}
        if self.callbacks is None:
            self.callbacks = []
    
    def set_permission(self, perm_type: PermissionType, info: PermissionInfo):
        """Установить информацию о разрешении"""
        self.permissions[perm_type] = info
    
    def get_permission(self, perm_type: PermissionType) -> Optional[PermissionInfo]:
        """Получить информацию о разрешении"""
        return self.permissions.get(perm_type)
    
    def get_all_permissions(self) -> Dict[PermissionType, PermissionInfo]:
        """Получить все разрешения"""
        return self.permissions.copy()
    
    def add_callback(self, callback: Callable[[PermissionEvent], None]):
        """Добавить callback"""
        self.callbacks.append(callback)
    
    async def notify_callbacks(self, event: PermissionEvent):
        """Уведомить callbacks"""
        for callback in self.callbacks:
            try:
                callback(event)
            except Exception as e:
                print(f"Ошибка в callback: {e}")
    
    def get_required_permissions_status(self) -> bool:
        """Проверить статус обязательных разрешений"""
        if not self.config:
            return False
        
        for perm_type in self.config.required_permissions:
            info = self.permissions.get(perm_type)
            if not info or info.status != PermissionStatus.GRANTED:
                return False
        return True
