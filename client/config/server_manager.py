"""
Централизованный менеджер серверов для Nexy AI Assistant
Единственное место для управления всеми серверными настройками
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ServerInfo:
    """Информация о сервере"""
    name: str
    host: str
    port: int
    ssl: bool
    timeout: int
    retry_attempts: int
    retry_delay: float
    description: str
    enabled: bool = True


class ServerManager:
    """Централизованный менеджер серверов"""
    
    def __init__(self, config_path: str = "config/unified_config.yaml"):
        self.config_path = config_path
        self._config = None
        self._load_config()
    
    def _load_config(self):
        """Загружает конфигурацию из файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить конфигурацию из {self.config_path}: {e}")
    
    def _save_config(self):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            raise RuntimeError(f"Не удалось сохранить конфигурацию в {self.config_path}: {e}")
    
    def get_all_servers(self) -> Dict[str, ServerInfo]:
        """Получает информацию о всех серверах"""
        servers = {}
        grpc_data = self._config.get('grpc', {})
        servers_config = grpc_data.get('servers', {})
        
        for server_name, server_config in servers_config.items():
            servers[server_name] = ServerInfo(
                name=server_name,
                host=server_config.get('host', '127.0.0.1'),
                port=server_config.get('port', 50051),
                ssl=server_config.get('ssl', False),
                timeout=server_config.get('timeout', 30),
                retry_attempts=server_config.get('retry_attempts', 3),
                retry_delay=server_config.get('retry_delay', 1.0),
                description=server_config.get('description', ''),
                enabled=server_config.get('enabled', True)
            )
        
        return servers
    
    def get_server(self, server_name: str) -> Optional[ServerInfo]:
        """Получает информацию о конкретном сервере"""
        servers = self.get_all_servers()
        return servers.get(server_name)
    
    def update_server(self, server_name: str, **kwargs) -> bool:
        """Обновляет настройки сервера"""
        try:
            if 'grpc' not in self._config:
                self._config['grpc'] = {}
            if 'servers' not in self._config['grpc']:
                self._config['grpc']['servers'] = {}
            
            if server_name not in self._config['grpc']['servers']:
                self._config['grpc']['servers'][server_name] = {}
            
            # Обновляем только переданные параметры
            for key, value in kwargs.items():
                if key in ['host', 'port', 'ssl', 'timeout', 'retry_attempts', 'retry_delay', 'description', 'enabled']:
                    self._config['grpc']['servers'][server_name][key] = value
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка обновления сервера {server_name}: {e}")
            return False
    
    def add_server(self, server_name: str, host: str, port: int, **kwargs) -> bool:
        """Добавляет новый сервер"""
        default_config = {
            'ssl': False,
            'timeout': 30,
            'retry_attempts': 3,
            'retry_delay': 1.0,
            'description': f'Сервер {server_name}',
            'enabled': True
        }
        default_config.update(kwargs)
        
        return self.update_server(server_name, host=host, port=port, **default_config)
    
    def remove_server(self, server_name: str) -> bool:
        """Удаляет сервер"""
        try:
            if 'grpc' in self._config and 'servers' in self._config['grpc']:
                if server_name in self._config['grpc']['servers']:
                    del self._config['grpc']['servers'][server_name]
                    self._save_config()
                    return True
            return False
        except Exception as e:
            print(f"Ошибка удаления сервера {server_name}: {e}")
            return False
    
    def set_default_server(self, server_name: str) -> bool:
        """Устанавливает сервер по умолчанию"""
        try:
            # Обновляем настройку в секции integrations.grpc_client
            if 'integrations' not in self._config:
                self._config['integrations'] = {}
            if 'grpc_client' not in self._config['integrations']:
                self._config['integrations']['grpc_client'] = {}
            
            self._config['integrations']['grpc_client']['server'] = server_name
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка установки сервера по умолчанию {server_name}: {e}")
            return False
    
    def get_default_server(self) -> Optional[str]:
        """Получает сервер по умолчанию"""
        try:
            return self._config.get('integrations', {}).get('grpc_client', {}).get('server')
        except:
            return None
    
    def list_servers(self) -> List[str]:
        """Возвращает список всех серверов"""
        return list(self.get_all_servers().keys())
    
    def validate_server(self, server_name: str) -> bool:
        """Проверяет, что сервер существует и настроен корректно"""
        server = self.get_server(server_name)
        if not server:
            return False
        
        # Проверяем обязательные поля
        required_fields = ['host', 'port']
        for field in required_fields:
            if not hasattr(server, field) or getattr(server, field) is None:
                return False
        
        return True


# Глобальный экземпляр для использования в приложении
server_manager = ServerManager()


def get_server_manager() -> ServerManager:
    """Получает глобальный экземпляр ServerManager"""
    return server_manager


# Удобные функции для быстрого доступа
def get_all_servers() -> Dict[str, ServerInfo]:
    """Получает все серверы"""
    return server_manager.get_all_servers()


def get_server(server_name: str) -> Optional[ServerInfo]:
    """Получает информацию о сервере"""
    return server_manager.get_server(server_name)


def update_server(server_name: str, **kwargs) -> bool:
    """Обновляет настройки сервера"""
    return server_manager.update_server(server_name, **kwargs)


def set_default_server(server_name: str) -> bool:
    """Устанавливает сервер по умолчанию"""
    return server_manager.set_default_server(server_name)


def get_default_server() -> Optional[str]:
    """Получает сервер по умолчанию"""
    return server_manager.get_default_server()


if __name__ == "__main__":
    # Пример использования
    manager = ServerManager()
    
    print("=== ВСЕ СЕРВЕРЫ ===")
    for name, server in manager.get_all_servers().items():
        print(f"{name}: {server.host}:{server.port} (SSL: {server.ssl}) - {server.description}")
    
    print(f"\n=== СЕРВЕР ПО УМОЛЧАНИЮ ===")
    default = manager.get_default_server()
    print(f"По умолчанию: {default}")
    
    print(f"\n=== ДОСТУПНЫЕ СЕРВЕРЫ ===")
    print(f"Список: {manager.list_servers()}")
