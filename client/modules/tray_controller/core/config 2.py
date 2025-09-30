"""
Конфигурация для Tray Controller
"""

import yaml
import os
from typing import Dict, Any, Optional
from .tray_types import TrayConfig, TrayStatus

class TrayConfigManager:
    """Менеджер конфигурации трея"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._get_default_config_path()
        self._config: Optional[TrayConfig] = None
        self._default_config = self._get_default_config()
    
    def _get_default_config_path(self) -> str:
        """Получить путь к конфигурации по умолчанию"""
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
            "config", "tray_config.yaml"
        )
    
    def _get_default_config(self) -> TrayConfig:
        """Получить конфигурацию по умолчанию"""
        return TrayConfig(
            show_status=True,
            show_menu=True,
            enable_click_events=True,
            enable_right_click=True,
            auto_hide=False,
            animation_speed=0.5,
            icon_size=16,
            menu_font_size=13,
            enable_sound=False,
            debug_mode=False
        )
    
    def load_config(self) -> TrayConfig:
        """Загрузить конфигурацию"""
        if self._config is not None:
            return self._config
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                
                self._config = TrayConfig(**config_data)
            else:
                self._config = self._default_config
                self.save_config()
                
        except Exception as e:
            print(f"Ошибка загрузки конфигурации трея: {e}")
            self._config = self._default_config
        
        return self._config
    
    def save_config(self) -> bool:
        """Сохранить конфигурацию"""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            config_dict = {
                'show_status': self._config.show_status,
                'show_menu': self._config.show_menu,
                'enable_click_events': self._config.enable_click_events,
                'enable_right_click': self._config.enable_right_click,
                'auto_hide': self._config.auto_hide,
                'animation_speed': self._config.animation_speed,
                'icon_size': self._config.icon_size,
                'menu_font_size': self._config.menu_font_size,
                'enable_sound': self._config.enable_sound,
                'debug_mode': self._config.debug_mode
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            
            return True
            
        except Exception as e:
            print(f"Ошибка сохранения конфигурации трея: {e}")
            return False
    
    def get_config(self) -> TrayConfig:
        """Получить текущую конфигурацию"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_config(self, **kwargs) -> bool:
        """Обновить конфигурацию"""
        try:
            if self._config is None:
                self._config = self.load_config()
            
            for key, value in kwargs.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
            
            return self.save_config()
            
        except Exception as e:
            print(f"Ошибка обновления конфигурации трея: {e}")
            return False
    
    def reset_to_default(self) -> bool:
        """Сбросить к конфигурации по умолчанию"""
        self._config = self._default_config
        return self.save_config()










