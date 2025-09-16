"""
Конфигурация для модуля permissions
"""

import yaml
from pathlib import Path
from typing import List, Optional
from .types import PermissionConfig, PermissionType


class PermissionConfigManager:
    """Менеджер конфигурации разрешений"""
    
    def __init__(self, config_path: str = "config/permissions_config.yaml"):
        self.config_path = Path(config_path)
    
    def get_config(self) -> PermissionConfig:
        """Получить конфигурацию"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return self._parse_config(data)
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}")
            return self._get_default_config()
    
    def _parse_config(self, data: dict) -> PermissionConfig:
        """Распарсить конфигурацию из YAML"""
        required_perms = [PermissionType(perm) for perm in data.get('required_permissions', [])]
        
        return PermissionConfig(
            required_permissions=required_perms,
            check_interval=data.get('check_interval', 30),
            auto_open_preferences=data.get('auto_open_preferences', True),
            show_instructions=data.get('show_instructions', True)
        )
    
    def _get_default_config(self) -> PermissionConfig:
        """Получить конфигурацию по умолчанию"""
        return PermissionConfig(
            required_permissions=[
                PermissionType.MICROPHONE,
                PermissionType.SCREEN_CAPTURE,
                PermissionType.NETWORK
            ],
            check_interval=30,
            auto_open_preferences=True,
            show_instructions=True
        )
