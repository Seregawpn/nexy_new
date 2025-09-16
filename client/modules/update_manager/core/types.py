"""
Типы данных для модуля обновлений
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Callable, List
import time

class UpdateStatus(Enum):
    """Статусы обновления"""
    IDLE = "idle"                    # Ожидание
    CHECKING = "checking"            # Проверка обновлений
    DOWNLOADING = "downloading"      # Скачивание
    INSTALLING = "installing"        # Установка
    RESTARTING = "restarting"        # Перезапуск
    FAILED = "failed"               # Ошибка
    COMPLETED = "completed"         # Завершено

@dataclass
class UpdateInfo:
    """Информация об обновлении"""
    version: str
    build_number: int
    release_notes: str
    download_url: str
    file_size: int
    signature: str
    pub_date: str
    is_mandatory: bool = False
    min_system_version: str = "10.15"  # macOS 10.15+

@dataclass
class UpdateConfig:
    """Конфигурация обновлений"""
    enabled: bool = True
    check_interval: int = 24  # часов
    check_time: str = "02:00"  # время проверки
    auto_install: bool = True
    announce_updates: bool = False  # Отключаем уведомления
    check_on_startup: bool = True
    appcast_url: str = ""
    retry_attempts: int = 3
    retry_delay: int = 300  # секунд
    silent_mode: bool = True  # Полностью тихий режим
    log_updates: bool = True  # Только в логах

@dataclass
class UpdateResult:
    """Результат операции обновления"""
    success: bool
    status: UpdateStatus
    message: str
    update_info: Optional[UpdateInfo] = None
    error: Optional[Exception] = None

@dataclass
class UpdateEvent:
    """Событие обновления"""
    event_type: str
    status: UpdateStatus
    update_info: Optional[UpdateInfo] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
