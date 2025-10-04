"""
Единый загрузчик конфигурации Nexy AI Assistant
Автоматически синхронизирует все настройки из unified_config.yaml
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass

@dataclass
class AppConfig:
    """Основные настройки приложения"""
    name: str
    version: str
    debug: bool
    bundle_id: str
    team_id: str

@dataclass
class GrpcServerConfig:
    """Конфигурация gRPC сервера"""
    host: str
    port: int
    ssl: bool
    timeout: int
    retry_attempts: int
    retry_delay: float

@dataclass
class NetworkConfig:
    """Сетевые настройки"""
    grpc_servers: Dict[str, GrpcServerConfig]
    appcast: Dict[str, Any]
    connection_check_interval: int
    auto_fallback: bool
    ping_timeout: int
    ping_hosts: list

@dataclass
class LoggingConfig:
    """Настройки логирования"""
    level: str
    file: str
    error_file: str
    max_size: str
    backup_count: int
    format: str
    loggers: Dict[str, str]

class UnifiedConfigLoader:
    """Единый загрузчик конфигурации с автоматической синхронизацией"""
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        # По умолчанию используем файл, расположенный рядом с этим модулем,
        # чтобы не зависеть от текущего рабочего каталога запуска.
        if config_file is None:
            self.config_file = Path(__file__).resolve().parent / "unified_config.yaml"
        else:
            self.config_file = Path(config_file)
        self._config_cache: Optional[Dict[str, Any]] = None
        self._last_modified: Optional[float] = None
    
    def _load_config(self) -> Dict[str, Any]:
        """Загружает конфигурацию с проверкой изменений"""
        if self._config_cache is None or self._is_config_modified():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config_cache = yaml.safe_load(f)
            self._last_modified = self.config_file.stat().st_mtime
        return self._config_cache
    
    def _is_config_modified(self) -> bool:
        """Проверяет, был ли файл конфигурации изменен"""
        if not self.config_file.exists():
            return True
        current_mtime = self.config_file.stat().st_mtime
        return self._last_modified is None or current_mtime > self._last_modified
    
    def reload(self):
        """Принудительно перезагружает конфигурацию"""
        self._config_cache = None
        self._last_modified = None
    
    # =====================================================
    # ОСНОВНЫЕ НАСТРОЙКИ ПРИЛОЖЕНИЯ
    # =====================================================
    
    def get_app_config(self) -> AppConfig:
        """Получает основные настройки приложения"""
        config = self._load_config()
        app_data = config['app']
        return AppConfig(
            name=app_data['name'],
            version=app_data['version'],
            debug=app_data['debug'],
            bundle_id=app_data['bundle_id'],
            team_id=app_data['team_id']
        )
    
    def get_version(self) -> str:
        """Получает версию приложения (используется везде)"""
        return self.get_app_config().version
    
    def get_bundle_id(self) -> str:
        """Получает Bundle ID приложения"""
        return self.get_app_config().bundle_id
    
    def get_team_id(self) -> str:
        """Получает Team ID для подписи"""
        return self.get_app_config().team_id
    
    # =====================================================
    # СЕТЕВЫЕ НАСТРОЙКИ
    # =====================================================
    
    def get_network_config(self) -> NetworkConfig:
        """Получает сетевые настройки"""
        config = self._load_config()
        
        # Получаем gRPC настройки из секции grpc
        grpc_data = config.get('grpc', {})
        
        # Создаем конфигурации для всех серверов из централизованной конфигурации
        grpc_servers = {}
        servers_config = grpc_data.get('servers', {})
        
        for server_name, server_config in servers_config.items():
            grpc_servers[server_name] = GrpcServerConfig(
                host=server_config.get('host', '127.0.0.1'),
                port=server_config.get('port', 50051),
                ssl=server_config.get('ssl', False),
                timeout=server_config.get('timeout', grpc_data.get('connection_timeout', 30)),
                retry_attempts=server_config.get('retry_attempts', grpc_data.get('retry_attempts', 3)),
                retry_delay=server_config.get('retry_delay', grpc_data.get('retry_delay', 1.0))
            )
        
        # Получаем настройки сети (если есть)
        network_data = config.get('network', {})
        
        return NetworkConfig(
            grpc_servers=grpc_servers,
            appcast=network_data.get('appcast', {'base_url': 'https://updates.nexy.ai'}),
            connection_check_interval=network_data.get('connection_check_interval', 30),
            auto_fallback=network_data.get('auto_fallback', True),
            ping_timeout=network_data.get('ping_timeout', 5),
            ping_hosts=network_data.get('ping_hosts', ['8.8.8.8', '1.1.1.1'])
        )
    
    def get_grpc_config(self, environment: str = "local") -> GrpcServerConfig:
        """Получает конфигурацию gRPC для указанного окружения"""
        network_config = self.get_network_config()
        if environment not in network_config.grpc_servers:
            raise ValueError(f"Environment '{environment}' not found")
        return network_config.grpc_servers[environment]
    
    def get_appcast_url(self) -> str:
        """Получает URL AppCast (используется везде)"""
        network_config = self.get_network_config()
        return network_config.appcast['base_url'] + "/appcast.xml"
    
    def get_grpc_host(self, environment: str = "local") -> str:
        """Получает хост gRPC сервера"""
        return self.get_grpc_config(environment).host
    
    def get_grpc_port(self, environment: str = "local") -> int:
        """Получает порт gRPC сервера"""
        return self.get_grpc_config(environment).port
    
    # =====================================================
    # НАСТРОЙКИ ЛОГИРОВАНИЯ
    # =====================================================
    
    def get_logging_config(self) -> LoggingConfig:
        """Получает настройки логирования"""
        config = self._load_config()
        logging_data = config['logging']
        return LoggingConfig(
            level=logging_data['level'],
            file=logging_data['file'],
            error_file=logging_data['error_file'],
            max_size=logging_data['max_size'],
            backup_count=logging_data['backup_count'],
            format=logging_data['format'],
            loggers=logging_data['loggers']
        )
    
    def get_log_file(self) -> str:
        """Получает путь к файлу логов (используется везде)"""
        return self.get_logging_config().file
    
    def get_error_log_file(self) -> str:
        """Получает путь к файлу ошибок"""
        return self.get_logging_config().error_file
    
    # =====================================================
    # ДРУГИЕ НАСТРОЙКИ
    # =====================================================
    
    def get_audio_config(self) -> Dict[str, Any]:
        """Получает настройки аудио"""
        config = self._load_config()
        return config['audio']
    
    def get_speech_playback_config(self) -> Dict[str, Any]:
        """Получает настройки воспроизведения речи"""
        audio_config = self.get_audio_config()
        return audio_config.get('speech_playback', {
            'sample_rate': 48000,
            'channels': 1,
            'dtype': 'int16',
            'buffer_size': 512,
            'max_memory_mb': 50,
            'auto_device_selection': True
        })
    
    def get_stt_config(self) -> Dict[str, Any]:
        """Получает настройки распознавания речи"""
        config = self._load_config()
        return config['stt']

    def get_stt_language(self, default: str = "en-US") -> str:
        """Получает язык распознавания речи (централизованно)"""
        try:
            stt = self.get_stt_config()
            return stt.get('language', default) or default
        except Exception:
            return default
    
    def get_screen_capture_config(self) -> Dict[str, Any]:
        """Получает настройки захвата экрана"""
        config = self._load_config()
        return config['screen_capture']
    
    def get_update_manager_config(self) -> Dict[str, Any]:
        """Получает настройки менеджера обновлений"""
        config = self._load_config()
        update_config = config['update_manager'].copy()
        # Автоматически подставляем AppCast URL
        update_config['appcast_url'] = self.get_appcast_url()
        return update_config
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Получает настройки производительности"""
        config = self._load_config()
        return config['performance']
    
    def get_security_config(self) -> Dict[str, Any]:
        """Получает настройки безопасности"""
        config = self._load_config()
        return config['security']
    
    # =====================================================
    # УТИЛИТЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
    # =====================================================
    
    def get_legacy_app_config(self) -> Dict[str, Any]:
        """Возвращает конфигурацию в старом формате для обратной совместимости"""
        config = self._load_config()
        
        # Создаем конфигурацию в старом формате
        legacy_config = {
            'app': config['app'],
            'audio': config['audio'],
            'stt': config['stt'],
            'screen_capture': config['screen_capture'],
            'grpc': {
                'config_file': 'config/unified_config.yaml',
                'server_priority': ['local', 'production', 'fallback'],
                'auto_fallback': config['network']['auto_fallback'],
                'connection_check_interval': config['network']['connection_check_interval']
            },
            'logging': config['logging'],
            'accessibility': config['accessibility'],
            'autostart': config['autostart'],
            'performance': config['performance'],
            'security': config['security'],
            'update_manager': self.get_update_manager_config()
        }
        
        return legacy_config

# Глобальный экземпляр загрузчика
unified_config = UnifiedConfigLoader()

# Удобные функции для быстрого доступа
def get_version() -> str:
    """Получает версию приложения"""
    return unified_config.get_version()

def get_appcast_url() -> str:
    """Получает URL AppCast"""
    return unified_config.get_appcast_url()

def get_grpc_host(environment: str = "local") -> str:
    """Получает хост gRPC сервера"""
    return unified_config.get_grpc_host(environment)

def get_grpc_port(environment: str = "local") -> int:
    """Получает порт gRPC сервера"""
    return unified_config.get_grpc_port(environment)

def get_log_file() -> str:
    """Получает путь к файлу логов"""
    return unified_config.get_log_file()

def get_bundle_id() -> str:
    """Получает Bundle ID"""
    return unified_config.get_bundle_id()

def get_team_id() -> str:
    """Получает Team ID"""
    return unified_config.get_team_id()
