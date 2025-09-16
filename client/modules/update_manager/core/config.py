"""
Конфигурация для модуля обновлений
"""

import yaml
from pathlib import Path
from typing import Optional
from .types import UpdateConfig

class UpdateConfigManager:
    """Менеджер конфигурации обновлений"""
    
    def __init__(self, config_path: str = "config/app_config.yaml"):
        self.config_path = Path(config_path)
    
    def get_config(self) -> UpdateConfig:
        """Получить конфигурацию обновлений"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                    return self._parse_config(data)
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"Ошибка загрузки конфигурации обновлений: {e}")
            return self._get_default_config()
    
    def _parse_config(self, data: dict) -> UpdateConfig:
        """Распарсить конфигурацию из YAML"""
        update_data = data.get('update_manager', {})
        
        return UpdateConfig(
            enabled=update_data.get('enabled', True),
            check_interval=update_data.get('check_interval', 24),
            check_time=update_data.get('check_time', '02:00'),
            auto_install=update_data.get('auto_install', True),
            announce_updates=update_data.get('announce_updates', False),
            check_on_startup=update_data.get('check_on_startup', True),
            appcast_url=update_data.get('appcast_url', ''),
            retry_attempts=update_data.get('retry_attempts', 3),
            retry_delay=update_data.get('retry_delay', 300),
            silent_mode=update_data.get('silent_mode', True),
            log_updates=update_data.get('log_updates', True)
        )
    
    def _get_default_config(self) -> UpdateConfig:
        """Получить конфигурацию по умолчанию"""
        return UpdateConfig(
            enabled=True,
            check_interval=24,
            check_time='02:00',
            auto_install=True,
            announce_updates=False,  # Тихий режим
            check_on_startup=True,
            appcast_url='https://your-server.com/appcast.xml',
            retry_attempts=3,
            retry_delay=300,
            silent_mode=True,  # Полностью тихий режим
            log_updates=True
        )
