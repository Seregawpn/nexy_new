"""
Модуль hardware_id для получения Hardware UUID на macOS
Упрощенная версия - только Hardware UUID
"""

from .core.hardware_identifier import HardwareIdentifier
from .core.types import (
    HardwareIdResult, HardwareIdStatus, HardwareIdConfig,
    HardwareIdError, HardwareIdNotFoundError, HardwareIdValidationError,
    CacheInfo
)
from .core.config import get_hardware_id_config, HardwareIdConfigManager

# Глобальный экземпляр для переиспользования
_hardware_identifier = None

def get_hardware_identifier() -> HardwareIdentifier:
    """Получает глобальный экземпляр HardwareIdentifier"""
    global _hardware_identifier
    if _hardware_identifier is None:
        _hardware_identifier = HardwareIdentifier()
    return _hardware_identifier

def get_hardware_id(force_regenerate: bool = False) -> str:
    """
    Получает Hardware ID (синглтон) с кэшированием
    
    Args:
        force_regenerate: Принудительно пересоздать ID
        
    Returns:
        str: Hardware ID
    """
    identifier = get_hardware_identifier()
    result = identifier.get_hardware_id(force_regenerate)
    return result.uuid

def get_hardware_id_result(force_regenerate: bool = False) -> HardwareIdResult:
    """
    Получает полный результат получения Hardware ID
    
    Args:
        force_regenerate: Принудительно пересоздать ID
        
    Returns:
        HardwareIdResult: Полный результат
    """
    identifier = get_hardware_identifier()
    return identifier.get_hardware_id(force_regenerate)

def get_hardware_info() -> dict:
    """Получает информацию об оборудовании"""
    identifier = get_hardware_identifier()
    return identifier.get_hardware_info()

def clear_hardware_id_cache():
    """Очищает кэш Hardware ID"""
    identifier = get_hardware_identifier()
    identifier.clear_cache()

def get_cache_info() -> dict:
    """Получает информацию о кэше"""
    identifier = get_hardware_identifier()
    return identifier.get_cache_info()

def validate_hardware_id(uuid_str: str) -> bool:
    """Валидирует Hardware ID"""
    identifier = get_hardware_identifier()
    return identifier.validate_hardware_id(uuid_str)

def is_available() -> bool:
    """Проверяет доступность модуля"""
    identifier = get_hardware_identifier()
    return identifier.is_available()

# Экспортируемые классы и функции
__all__ = [
    # Основные классы
    'HardwareIdentifier',
    'HardwareIdConfigManager',
    
    # Типы данных
    'HardwareIdResult',
    'HardwareIdStatus', 
    'HardwareIdConfig',
    'HardwareIdError',
    'HardwareIdNotFoundError',
    'HardwareIdValidationError',
    'CacheInfo',
    
    # Основные функции
    'get_hardware_id',
    'get_hardware_id_result',
    'get_hardware_info',
    'clear_hardware_id_cache',
    'get_cache_info',
    'validate_hardware_id',
    'is_available',
    'get_hardware_identifier',
    'get_hardware_id_config'
]
