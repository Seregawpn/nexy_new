"""
Конфигурация Interrupt Handling Module
"""

import os
from typing import Dict, Any

class InterruptHandlingConfig:
    """Конфигурация модуля обработки прерываний"""
    
    def __init__(self):
        """Инициализация конфигурации"""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        return {
            # Настройки глобальных флагов
            "global_interrupt_enabled": os.getenv("GLOBAL_INTERRUPT_ENABLED", "true").lower() == "true",
            "interrupt_check_interval": float(os.getenv("INTERRUPT_CHECK_INTERVAL", "0.1")),  # 100ms
            "interrupt_timeout": float(os.getenv("INTERRUPT_TIMEOUT", "5.0")),  # 5 секунд
            
            # Настройки сессий
            "session_cleanup_delay": float(os.getenv("SESSION_CLEANUP_DELAY", "2.0")),  # 2 секунды
            "max_active_sessions": int(os.getenv("MAX_ACTIVE_SESSIONS", "100")),
            "session_timeout": int(os.getenv("SESSION_TIMEOUT", "300")),  # 5 минут
            
            # Настройки прерывания модулей
            "modules": {
                "text_processing": {
                    "enabled": True,
                    "interrupt_methods": ["cancel_generation", "clear_buffers"],
                    "timeout": 2.0
                },
                "audio_generation": {
                    "enabled": True,
                    "interrupt_methods": ["stop_generation"],
                    "timeout": 1.0
                },
                "session_management": {
                    "enabled": True,
                    "interrupt_methods": ["interrupt_session"],
                    "timeout": 1.0
                },
                "database": {
                    "enabled": True,
                    "interrupt_methods": ["clear_cache"],
                    "timeout": 0.5
                },
                "memory_management": {
                    "enabled": True,
                    "interrupt_methods": ["clear_cache"],
                    "timeout": 0.5
                }
            },
            
            # Настройки логирования
            "log_interrupts": os.getenv("LOG_INTERRUPTS", "true").lower() == "true",
            "log_timing": os.getenv("LOG_TIMING", "true").lower() == "true",
            
            # Настройки производительности
            "interrupt_priority": "high",  # high, normal, low
            "cleanup_on_interrupt": True,
            "force_cleanup": True
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Получение значения конфигурации"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """Получение конфигурации модуля"""
        return self.config.get("modules", {}).get(module_name, {})
    
    def is_module_interrupt_enabled(self, module_name: str) -> bool:
        """Проверка, включено ли прерывание для модуля"""
        module_config = self.get_module_config(module_name)
        return module_config.get("enabled", False)
    
    def get_module_interrupt_methods(self, module_name: str) -> list:
        """Получение методов прерывания для модуля"""
        module_config = self.get_module_config(module_name)
        return module_config.get("interrupt_methods", [])
    
    def get_module_timeout(self, module_name: str) -> float:
        """Получение таймаута прерывания для модуля"""
        module_config = self.get_module_config(module_name)
        return module_config.get("timeout", 2.0)
    
    def get_global_settings(self) -> Dict[str, Any]:
        """Получение глобальных настроек"""
        return {
            "global_interrupt_enabled": self.config["global_interrupt_enabled"],
            "interrupt_check_interval": self.config["interrupt_check_interval"],
            "interrupt_timeout": self.config["interrupt_timeout"]
        }
    
    def get_session_settings(self) -> Dict[str, Any]:
        """Получение настроек сессий"""
        return {
            "session_cleanup_delay": self.config["session_cleanup_delay"],
            "max_active_sessions": self.config["max_active_sessions"],
            "session_timeout": self.config["session_timeout"]
        }
    
    def get_performance_settings(self) -> Dict[str, Any]:
        """Получение настроек производительности"""
        return {
            "interrupt_priority": self.config["interrupt_priority"],
            "cleanup_on_interrupt": self.config["cleanup_on_interrupt"],
            "force_cleanup": self.config["force_cleanup"]
        }
