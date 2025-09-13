"""
Конфигурация для модуля hardware_id
Упрощенная версия - только Hardware UUID для macOS
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from .types import HardwareIdConfig

logger = logging.getLogger(__name__)


class HardwareIdConfigManager:
    """Менеджер конфигурации для hardware_id"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_file()
        self._config: Optional[HardwareIdConfig] = None
    
    def _get_default_config_file(self) -> str:
        """Получает путь к файлу конфигурации по умолчанию"""
        return os.path.join(os.path.expanduser("~"), ".voice_assistant", "hardware_id_config.json")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию по умолчанию"""
        return {
            "hardware_id": {
                "cache_enabled": True,
                "cache_file_path": "~/.voice_assistant/hardware_id_cache.json",
                "cache_ttl_seconds": 86400 * 30,  # 30 дней
                "system_profiler_timeout": 5,
                "validate_uuid_format": True,
                "fallback_to_random": False
            }
        }
    
    def load_config(self) -> HardwareIdConfig:
        """Загружает конфигурацию из файла или создает по умолчанию"""
        if self._config is not None:
            return self._config
        
        try:
            # Пытаемся загрузить из файла
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Извлекаем конфигурацию hardware_id
                hardware_config = config_data.get("hardware_id", {})
                
                self._config = HardwareIdConfig(
                    cache_enabled=hardware_config.get("cache_enabled", True),
                    cache_file_path=hardware_config.get("cache_file_path", "~/.voice_assistant/hardware_id_cache.json"),
                    cache_ttl_seconds=hardware_config.get("cache_ttl_seconds", 86400 * 30),
                    system_profiler_timeout=hardware_config.get("system_profiler_timeout", 5),
                    validate_uuid_format=hardware_config.get("validate_uuid_format", True),
                    fallback_to_random=hardware_config.get("fallback_to_random", False)
                )
                
                logger.info("✅ Конфигурация hardware_id загружена из файла")
                return self._config
            
            else:
                # Создаем конфигурацию по умолчанию
                logger.info("📝 Создаем конфигурацию hardware_id по умолчанию")
                return self._create_default_config()
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка загрузки конфигурации: {e}")
            return self._create_default_config()
    
    def _create_default_config(self) -> HardwareIdConfig:
        """Создает конфигурацию по умолчанию"""
        self._config = HardwareIdConfig()
        
        # Создаем файл конфигурации
        try:
            config_dir = Path(self.config_file).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_data = self._get_default_config()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Конфигурация по умолчанию создана: {self.config_file}")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать файл конфигурации: {e}")
        
        return self._config
    
    def save_config(self, config: HardwareIdConfig) -> bool:
        """Сохраняет конфигурацию в файл"""
        try:
            config_dir = Path(self.config_file).parent
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_data = {
                "hardware_id": {
                    "cache_enabled": config.cache_enabled,
                    "cache_file_path": config.cache_file_path,
                    "cache_ttl_seconds": config.cache_ttl_seconds,
                    "system_profiler_timeout": config.system_profiler_timeout,
                    "validate_uuid_format": config.validate_uuid_format,
                    "fallback_to_random": config.fallback_to_random
                }
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            self._config = config
            logger.info("✅ Конфигурация hardware_id сохранена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка сохранения конфигурации: {e}")
            return False
    
    def get_config(self) -> HardwareIdConfig:
        """Получает текущую конфигурацию"""
        if self._config is None:
            return self.load_config()
        return self._config
    
    def update_config(self, **kwargs) -> bool:
        """Обновляет конфигурацию"""
        try:
            current_config = self.get_config()
            
            # Обновляем только переданные параметры
            for key, value in kwargs.items():
                if hasattr(current_config, key):
                    setattr(current_config, key, value)
            
            return self.save_config(current_config)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления конфигурации: {e}")
            return False


# Глобальный экземпляр менеджера конфигурации
_config_manager = None

def get_config_manager() -> HardwareIdConfigManager:
    """Получает глобальный экземпляр менеджера конфигурации"""
    global _config_manager
    if _config_manager is None:
        _config_manager = HardwareIdConfigManager()
    return _config_manager

def get_hardware_id_config() -> HardwareIdConfig:
    """Получает конфигурацию hardware_id"""
    return get_config_manager().get_config()
