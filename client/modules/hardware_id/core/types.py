"""
Типы данных для модуля hardware_id
Упрощенная версия - только Hardware UUID для macOS
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class HardwareIdStatus(Enum):
    """Статус получения Hardware ID"""
    SUCCESS = "success"
    CACHED = "cached"
    ERROR = "error"
    NOT_FOUND = "not_found"


@dataclass
class HardwareIdResult:
    """Результат получения Hardware ID"""
    uuid: str
    status: HardwareIdStatus
    source: str  # "cache", "system_profiler", "fallback"
    cached: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class HardwareIdConfig:
    """Конфигурация для получения Hardware ID"""
    cache_enabled: bool = True
    cache_file_path: str = "~/.voice_assistant/hardware_id_cache.json"
    cache_ttl_seconds: int = 86400 * 30  # 30 дней
    system_profiler_timeout: int = 5
    validate_uuid_format: bool = True
    fallback_to_random: bool = False


@dataclass
class CacheInfo:
    """Информация о кэше"""
    exists: bool
    size_bytes: int
    created_at: str
    modified_at: str
    ttl_remaining: int
    is_valid: bool


class HardwareIdError(Exception):
    """Базовое исключение для модуля hardware_id"""
    pass


class HardwareIdNotFoundError(HardwareIdError):
    """Hardware ID не найден"""
    pass


class HardwareIdValidationError(HardwareIdError):
    """Ошибка валидации Hardware ID"""
    pass


class HardwareIdCacheError(HardwareIdError):
    """Ошибка работы с кэшем"""
    pass
