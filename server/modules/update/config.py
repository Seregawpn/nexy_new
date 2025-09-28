"""
Конфигурация Update Module
"""

import os
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path


@dataclass
class UpdateConfig:
    """Конфигурация модуля обновлений"""
    
    # Основные настройки
    enabled: bool = True
    port: int = 8081
    host: str = "0.0.0.0"
    
    # Пути к директориям
    updates_dir: Optional[str] = None
    downloads_dir: Optional[str] = None
    keys_dir: Optional[str] = None
    manifests_dir: Optional[str] = None
    
    # Настройки сервера
    cors_enabled: bool = True
    cache_control: str = "no-cache, no-store, must-revalidate"
    
    # Настройки манифестов
    default_version: str = "1.0.0"
    default_build: int = 10000
    default_arch: str = "universal2"
    default_min_os: str = "11.0"
    
    # Безопасность
    require_https: bool = False  # Для тестирования
    verify_signatures: bool = True
    
    # Логирование
    log_requests: bool = True
    log_downloads: bool = True
    
    def __post_init__(self):
        """Инициализация путей"""
        if self.updates_dir is None:
            # Определяем путь к директории updates относительно этого файла
            current_file_dir = Path(__file__).parent.parent.parent
            self.updates_dir = str(current_file_dir / "updates")
        
        if self.downloads_dir is None:
            self.downloads_dir = str(Path(self.updates_dir) / "downloads")
        
        if self.keys_dir is None:
            self.keys_dir = str(Path(self.updates_dir) / "keys")
        
        if self.manifests_dir is None:
            self.manifests_dir = str(Path(self.updates_dir) / "manifests")
        
        # Создаем директории если не существуют
        Path(self.downloads_dir).mkdir(parents=True, exist_ok=True)
        Path(self.keys_dir).mkdir(parents=True, exist_ok=True)
        Path(self.manifests_dir).mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'UpdateConfig':
        """Создание конфигурации из словаря"""
        return cls(**config_dict)
    
    @classmethod
    def from_env(cls) -> 'UpdateConfig':
        """Создание конфигурации из переменных окружения"""
        return cls(
            enabled=os.getenv('UPDATE_ENABLED', 'true').lower() == 'true',
            port=int(os.getenv('UPDATE_PORT', '8081')),
            host=os.getenv('UPDATE_HOST', '0.0.0.0'),
            updates_dir=os.getenv('UPDATE_DIR'),
            cors_enabled=os.getenv('UPDATE_CORS', 'true').lower() == 'true',
            require_https=os.getenv('UPDATE_REQUIRE_HTTPS', 'false').lower() == 'true',
            verify_signatures=os.getenv('UPDATE_VERIFY_SIGNATURES', 'true').lower() == 'true',
            log_requests=os.getenv('UPDATE_LOG_REQUESTS', 'true').lower() == 'true',
            log_downloads=os.getenv('UPDATE_LOG_DOWNLOADS', 'true').lower() == 'true'
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return {
            'enabled': self.enabled,
            'port': self.port,
            'host': self.host,
            'updates_dir': self.updates_dir,
            'downloads_dir': self.downloads_dir,
            'keys_dir': self.keys_dir,
            'manifests_dir': self.manifests_dir,
            'cors_enabled': self.cors_enabled,
            'cache_control': self.cache_control,
            'default_version': self.default_version,
            'default_build': self.default_build,
            'default_arch': self.default_arch,
            'default_min_os': self.default_min_os,
            'require_https': self.require_https,
            'verify_signatures': self.verify_signatures,
            'log_requests': self.log_requests,
            'log_downloads': self.log_downloads
        }
    
    def is_valid(self) -> bool:
        """Проверка валидности конфигурации"""
        try:
            # Проверяем порт
            if not (1 <= self.port <= 65535):
                return False
            
            # Проверяем директории
            if not Path(self.updates_dir).exists():
                return False
            
            return True
        except Exception:
            return False



