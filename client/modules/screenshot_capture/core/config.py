"""
Конфигурация для модуля захвата скриншотов
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any
from .types import ScreenshotConfig, ScreenshotFormat, ScreenshotQuality, ScreenshotRegion

class ScreenshotConfigManager:
    """Менеджер конфигурации для скриншотов"""
    
    def __init__(self, config_path: str = None):
        """
        Инициализирует менеджер конфигурации
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config_path = config_path or self._get_default_config_path()
        self._config_cache = None
    
    def _get_default_config_path(self) -> str:
        """Получает путь к конфигурации по умолчанию"""
        # Ищем конфигурацию в корне проекта
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / "config" / "app_config.yaml"
        return str(config_path)
    
    def load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию из файла"""
        if self._config_cache is not None:
            return self._config_cache
        
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    self._config_cache = config
                    return config
            else:
                return self._get_default_config()
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфигурации: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "screen_capture": {
                "quality": 40,  # Уменьшено до 40 для очень быстрой передачи
                "format": "jpeg",
                "max_width": 960,   # Уменьшено до 960 для быстрой передачи
                "max_height": 540,  # Уменьшено до 540 для быстрой передачи
                "include_cursor": False,
                "compress": True,
                "timeout": 3.0  # Уменьшен таймаут
            }
        }
    
    def get_screenshot_config(self) -> ScreenshotConfig:
        """Получает конфигурацию скриншотов"""
        config = self.load_config()
        screen_config = config.get("screen_capture", {})
        
        # Маппинг качества
        quality_map = {
            "low": ScreenshotQuality.LOW,
            "medium": ScreenshotQuality.MEDIUM,
            "high": ScreenshotQuality.HIGH,
            "maximum": ScreenshotQuality.MAXIMUM
        }
        
        # Маппинг формата
        format_map = {
            "jpeg": ScreenshotFormat.JPEG,
            "png": ScreenshotFormat.PNG
        }
        
        # Получаем качество
        quality_value = screen_config.get("quality", 40)
        if isinstance(quality_value, int):
            if quality_value <= 40:
                quality = ScreenshotQuality.LOW
            elif quality_value <= 60:
                quality = ScreenshotQuality.MEDIUM
            elif quality_value <= 80:
                quality = ScreenshotQuality.HIGH
            else:
                quality = ScreenshotQuality.MAXIMUM
        else:
            quality = quality_map.get(quality_value, ScreenshotQuality.MEDIUM)
        
        # Получаем формат
        format_value = screen_config.get("format", "jpeg")
        format_type = format_map.get(format_value, ScreenshotFormat.JPEG)
        
        return ScreenshotConfig(
            format=format_type,
            quality=quality,
            region=ScreenshotRegion.FULL_SCREEN,
            include_cursor=screen_config.get("include_cursor", False),
            compress=screen_config.get("compress", True),
            max_width=screen_config.get("max_width", 1920),
            max_height=screen_config.get("max_height", 1080),
            timeout=screen_config.get("timeout", 5.0)
        )

# Глобальный экземпляр менеджера конфигурации
config_manager = ScreenshotConfigManager()

def get_screenshot_config() -> ScreenshotConfig:
    """Получает конфигурацию скриншотов"""
    return config_manager.get_screenshot_config()
