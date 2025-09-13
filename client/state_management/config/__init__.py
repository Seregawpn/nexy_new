"""
Конфигурация модуля управления состояниями
"""

from .state_config import (
    create_config, load_config_from_dict, save_config_to_dict,
    DefaultStateConfig, HighPerformanceConfig, DebugConfig
)

__all__ = [
    "create_config",
    "load_config_from_dict", 
    "save_config_to_dict",
    "DefaultStateConfig",
    "HighPerformanceConfig",
    "DebugConfig"
]
