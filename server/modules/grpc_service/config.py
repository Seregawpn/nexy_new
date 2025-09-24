"""
Конфигурация gRPC Service Module
"""

import os
from typing import Dict, Any

class GrpcServiceConfig:
    """Конфигурация gRPC сервиса"""
    
    def __init__(self):
        """Инициализация конфигурации"""
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации"""
        return {
            # gRPC настройки
            "grpc_host": os.getenv("GRPC_HOST", "0.0.0.0"),
            "grpc_port": int(os.getenv("GRPC_PORT", "50051")),
            "use_tls": os.getenv("USE_TLS", "false").lower() == "true",
            
            # Настройки сессий
            "max_sessions": int(os.getenv("MAX_SESSIONS", "100")),
            "session_timeout": int(os.getenv("SESSION_TIMEOUT", "300")),  # 5 минут
            
            # Настройки прерывания
            "interrupt_check_interval": float(os.getenv("INTERRUPT_CHECK_INTERVAL", "0.1")),  # 100ms
            "max_processing_time": int(os.getenv("MAX_PROCESSING_TIME", "30")),  # 30 секунд
            
            # Настройки логирования
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "log_requests": os.getenv("LOG_REQUESTS", "true").lower() == "true",
            
            # Настройки производительности
            "max_concurrent_requests": int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")),
            "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "60")),  # 60 секунд
            
            # Настройки модулей
            "modules": {
                "text_processing": {
                    "enabled": True,
                    "timeout": 30
                },
                "audio_generation": {
                    "enabled": True,
                    "timeout": 15
                },
                "session_management": {
                    "enabled": True,
                    "timeout": 5
                },
                "database": {
                    "enabled": True,
                    "timeout": 10
                },
                "memory_management": {
                    "enabled": True,
                    "timeout": 10
                }
            }
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
    
    def is_module_enabled(self, module_name: str) -> bool:
        """Проверка, включен ли модуль"""
        module_config = self.get_module_config(module_name)
        return module_config.get("enabled", False)
    
    def get_module_timeout(self, module_name: str) -> int:
        """Получение таймаута модуля"""
        module_config = self.get_module_config(module_name)
        return module_config.get("timeout", 30)
    
    def get_grpc_settings(self) -> Dict[str, Any]:
        """Получение настроек gRPC"""
        return {
            "host": self.config["grpc_host"],
            "port": self.config["grpc_port"],
            "use_tls": self.config["use_tls"]
        }
    
    def get_session_settings(self) -> Dict[str, Any]:
        """Получение настроек сессий"""
        return {
            "max_sessions": self.config["max_sessions"],
            "session_timeout": self.config["session_timeout"]
        }
    
    def get_interrupt_settings(self) -> Dict[str, Any]:
        """Получение настроек прерывания"""
        return {
            "check_interval": self.config["interrupt_check_interval"],
            "max_processing_time": self.config["max_processing_time"]
        }
