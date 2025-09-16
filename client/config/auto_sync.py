"""
Автоматическая синхронизация конфигурации
Обновляет все файлы при изменении unified_config.yaml
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from unified_config_loader import unified_config

class ConfigAutoSync:
    """Автоматическая синхронизация конфигурации"""
    
    def __init__(self):
        self.config_dir = Path("config")
        self.unified_config_file = self.config_dir / "unified_config.yaml"
    
    def sync_all_configs(self):
        """Синхронизирует все конфигурационные файлы"""
        print("🔄 Синхронизация конфигурации...")
        
        # Синхронизируем app_config.yaml
        self._sync_app_config()
        
        # Синхронизируем logging_config.yaml
        self._sync_logging_config()
        
        # Синхронизируем network_config.yaml
        self._sync_network_config()
        
        # Обновляем все файлы с версиями
        self._update_version_in_files()
        
        # Обновляем все файлы с AppCast URL
        self._update_appcast_url_in_files()
        
        print("✅ Синхронизация завершена!")
    
    def _sync_app_config(self):
        """Синхронизирует app_config.yaml с unified_config.yaml"""
        legacy_config = unified_config.get_legacy_app_config()
        
        # Сохраняем в app_config.yaml
        with open(self.config_dir / "app_config.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(legacy_config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print("✅ app_config.yaml синхронизирован")
    
    def _sync_logging_config(self):
        """Синхронизирует logging_config.yaml с unified_config.yaml"""
        logging_config = unified_config.get_logging_config()
        
        # Создаем конфигурацию в формате Python logging
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'standard': {
                    'format': logging_config.format,
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'detailed': {
                    'format': f"%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
                    'datefmt': '%Y-%m-%d %H:%M:%S'
                },
                'simple': {
                    'format': '%(levelname)s - %(message)s'
                }
            },
            'handlers': {
                'file_handler': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': logging_config.level,
                    'formatter': 'detailed',
                    'filename': logging_config.file,
                    'maxBytes': 10485760,  # 10MB
                    'backupCount': logging_config.backup_count,
                    'encoding': 'utf8'
                },
                'console_handler': {
                    'class': 'logging.StreamHandler',
                    'level': logging_config.level,
                    'formatter': 'standard',
                    'stream': 'ext://sys.stdout'
                },
                'error_file_handler': {
                    'class': 'logging.handlers.RotatingFileHandler',
                    'level': 'ERROR',
                    'formatter': 'detailed',
                    'filename': logging_config.error_file,
                    'maxBytes': 5242880,  # 5MB
                    'backupCount': 3,
                    'encoding': 'utf8'
                }
            },
            'loggers': {
                logging_config.loggers['main']: {
                    'level': logging_config.level,
                    'handlers': ['file_handler', 'console_handler', 'error_file_handler'],
                    'propagate': False
                },
                logging_config.loggers['audio']: {
                    'level': logging_config.level,
                    'handlers': ['file_handler'],
                    'propagate': False
                },
                logging_config.loggers['stt']: {
                    'level': logging_config.level,
                    'handlers': ['file_handler'],
                    'propagate': False
                },
                logging_config.loggers['grpc']: {
                    'level': logging_config.level,
                    'handlers': ['file_handler'],
                    'propagate': False
                },
                logging_config.loggers['screen_capture']: {
                    'level': logging_config.level,
                    'handlers': ['file_handler'],
                    'propagate': False
                },
                logging_config.loggers['accessibility']: {
                    'level': logging_config.level,
                    'handlers': ['file_handler', 'console_handler'],
                    'propagate': False
                }
            },
            'root': {
                'level': 'WARNING',
                'handlers': ['system_handler']
            }
        }
        
        # Сохраняем в logging_config.yaml
        with open(self.config_dir / "logging_config.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print("✅ logging_config.yaml синхронизирован")
    
    def _sync_network_config(self):
        """Синхронизирует network_config.yaml с unified_config.yaml"""
        network_config = unified_config.get_network_config()
        
        # Создаем конфигурацию в старом формате
        config = {
            'grpc_servers': {
                name: {
                    'host': server.host,
                    'port': server.port,
                    'ssl': server.ssl,
                    'timeout': server.timeout,
                    'retry_attempts': server.retry_attempts,
                    'retry_delay': server.retry_delay
                }
                for name, server in network_config.grpc_servers.items()
            },
            'appcast': network_config.appcast,
            'network': {
                'connection_check_interval': network_config.connection_check_interval,
                'auto_fallback': network_config.auto_fallback,
                'ping_timeout': network_config.ping_timeout,
                'ping_hosts': network_config.ping_hosts
            }
        }
        
        # Сохраняем в network_config.yaml
        with open(self.config_dir / "network_config.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
        
        print("✅ network_config.yaml синхронизирован")
    
    def _update_version_in_files(self):
        """Обновляет версию во всех файлах"""
        version = unified_config.get_version()
        
        # Файлы для обновления версии
        files_to_update = [
            "modules/update_manager/macos/sparkle_handler.py",
            "test_update_with_mock_sparkle.py",
            "test_update_standalone.py",
            "test_update_manager.py"
        ]
        
        for file_path in files_to_update:
            self._update_version_in_file(file_path, version)
    
    def _update_version_in_file(self, file_path: str, version: str):
        """Обновляет версию в конкретном файле"""
        if not Path(file_path).exists():
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем и заменяем версию
        import re
        pattern = r'version="[^"]*"'
        new_content = re.sub(pattern, f'version="{version}"', content)
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ Версия обновлена в {file_path}")
    
    def _update_appcast_url_in_files(self):
        """Обновляет AppCast URL во всех файлах"""
        appcast_url = unified_config.get_appcast_url()
        
        # Файлы для обновления AppCast URL
        files_to_update = [
            "integration/core/simple_module_coordinator.py",
            "test_update_standalone.py",
            "test_update_manager.py",
            "modules/update_manager/core/config.py",
            "test_update_with_mock_sparkle.py"
        ]
        
        for file_path in files_to_update:
            self._update_appcast_url_in_file(file_path, appcast_url)
    
    def _update_appcast_url_in_file(self, file_path: str, appcast_url: str):
        """Обновляет AppCast URL в конкретном файле"""
        if not Path(file_path).exists():
            return
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Ищем и заменяем AppCast URL
        import re
        pattern = r'appcast_url="[^"]*"'
        new_content = re.sub(pattern, f'appcast_url="{appcast_url}"', content)
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✅ AppCast URL обновлен в {file_path}")

def sync_config():
    """Функция для синхронизации конфигурации"""
    syncer = ConfigAutoSync()
    syncer.sync_all_configs()

if __name__ == "__main__":
    sync_config()
