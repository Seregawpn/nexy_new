"""
Централизованный загрузчик конфигурации
Единая точка для загрузки всех настроек приложения
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    """Централизованный загрузчик конфигурации"""
    
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._cache = {}
    
    def load_network_config(self) -> Dict[str, Any]:
        """Загружает сетевые настройки из network_config.yaml"""
        if 'network' not in self._cache:
            config_path = self.config_dir / "network_config.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._cache['network'] = yaml.safe_load(f)
        return self._cache['network']
    
    def load_app_config(self) -> Dict[str, Any]:
        """Загружает основные настройки приложения"""
        if 'app' not in self._cache:
            config_path = self.config_dir / "app_config.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._cache['app'] = yaml.safe_load(f)
        return self._cache['app']
    
    def load_logging_config(self) -> Dict[str, Any]:
        """Загружает настройки логирования"""
        if 'logging' not in self._cache:
            config_path = self.config_dir / "logging_config.yaml"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._cache['logging'] = yaml.safe_load(f)
        return self._cache['logging']
    
    def get_grpc_config(self, environment: str = "local") -> Dict[str, Any]:
        """Получает конфигурацию gRPC для указанного окружения"""
        network_config = self.load_network_config()
        grpc_servers = network_config.get('grpc_servers', {})
        
        if environment not in grpc_servers:
            raise ValueError(f"Environment '{environment}' not found in grpc_servers")
        
        return grpc_servers[environment]
    
    def get_appcast_config(self) -> Dict[str, Any]:
        """Получает конфигурацию AppCast"""
        network_config = self.load_network_config()
        return network_config.get('appcast', {})
    
    def get_network_config(self) -> Dict[str, Any]:
        """Получает общие сетевые настройки"""
        network_config = self.load_network_config()
        return network_config.get('network', {})
    
    def reload_all(self):
        """Перезагружает все конфигурации (очищает кэш)"""
        self._cache.clear()

# Глобальный экземпляр загрузчика
config_loader = ConfigLoader()

# Удобные функции для быстрого доступа
def get_grpc_config(environment: str = "local") -> Dict[str, Any]:
    """Быстрый доступ к конфигурации gRPC"""
    return config_loader.get_grpc_config(environment)

def get_appcast_config() -> Dict[str, Any]:
    """Быстрый доступ к конфигурации AppCast"""
    return config_loader.get_appcast_config()

def get_network_config() -> Dict[str, Any]:
    """Быстрый доступ к сетевым настройкам"""
    return config_loader.get_network_config()
