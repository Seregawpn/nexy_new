"""
Конфигурация модуля управления состояниями
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from ..core.types import StateConfig


@dataclass
class DefaultStateConfig(StateConfig):
    """Конфигурация по умолчанию"""
    max_history_size: int = 100
    transition_timeout: float = 30.0
    recovery_attempts: int = 3
    recovery_delay: float = 1.0
    enable_monitoring: bool = True
    enable_recovery: bool = True
    log_transitions: bool = True


@dataclass
class HighPerformanceConfig(StateConfig):
    """Конфигурация для высокой производительности"""
    max_history_size: int = 50
    transition_timeout: float = 15.0
    recovery_attempts: int = 2
    recovery_delay: float = 0.5
    enable_monitoring: bool = True
    enable_recovery: bool = True
    log_transitions: bool = False


@dataclass
class DebugConfig(StateConfig):
    """Конфигурация для отладки"""
    max_history_size: int = 500
    transition_timeout: float = 60.0
    recovery_attempts: int = 5
    recovery_delay: float = 2.0
    enable_monitoring: bool = True
    enable_recovery: bool = True
    log_transitions: bool = True


def create_config(config_type: str = "default", **kwargs) -> StateConfig:
    """
    Создает конфигурацию по типу
    
    Args:
        config_type: Тип конфигурации (default, high_performance, debug)
        **kwargs: Дополнительные параметры
        
    Returns:
        StateConfig: Конфигурация
    """
    configs = {
        "default": DefaultStateConfig,
        "high_performance": HighPerformanceConfig,
        "debug": DebugConfig
    }
    
    config_class = configs.get(config_type, DefaultStateConfig)
    config = config_class()
    
    # Применяем дополнительные параметры
    for key, value in kwargs.items():
        if hasattr(config, key):
            setattr(config, key, value)
    
    return config


def load_config_from_dict(config_dict: Dict[str, Any]) -> StateConfig:
    """
    Загружает конфигурацию из словаря
    
    Args:
        config_dict: Словарь с конфигурацией
        
    Returns:
        StateConfig: Конфигурация
    """
    return StateConfig(**config_dict)


def save_config_to_dict(config: StateConfig) -> Dict[str, Any]:
    """
    Сохраняет конфигурацию в словарь
    
    Args:
        config: Конфигурация
        
    Returns:
        Dict[str, Any]: Словарь с конфигурацией
    """
    return {
        'max_history_size': config.max_history_size,
        'transition_timeout': config.transition_timeout,
        'recovery_attempts': config.recovery_attempts,
        'recovery_delay': config.recovery_delay,
        'enable_monitoring': config.enable_monitoring,
        'enable_recovery': config.enable_recovery,
        'log_transitions': config.log_transitions
    }
