"""
Конфигурация системы обновлений
"""

from dataclasses import dataclass
import os
from typing import Optional

@dataclass
class UpdaterConfig:
    """Конфигурация системы обновлений"""
    enabled: bool = True
    manifest_url: str = ""
    check_interval: int = 3600
    check_on_startup: bool = True
    auto_install: bool = True
    public_key: str = ""
    timeout: int = 30  # Увеличено для DMG
    retries: int = 3
    show_notifications: bool = True
    auto_download: bool = True
    
    def __post_init__(self):
        """Валидация конфигурации"""
        # Проверка HTTPS (отключена для тестирования и Azure VM)
        if self.manifest_url and not self.manifest_url.startswith('https://') and not self.manifest_url.startswith('http://localhost') and not self.manifest_url.startswith('http://20.151.51.172'):
            raise ValueError("manifest_url должен использовать HTTPS (кроме localhost и Azure VM для тестирования)")
        
        # Проверка интервала
        if self.check_interval < 300:  # Минимум 5 минут
            raise ValueError("check_interval должен быть не менее 300 секунд")
        
        # Проверка таймаута
        if self.timeout < 10:
            raise ValueError("timeout должен быть не менее 10 секунд")
    
    def is_valid(self) -> bool:
        """Проверка валидности конфигурации"""
        try:
            self.__post_init__()
            return True
        except ValueError:
            return False
    
    def get_user_app_path(self) -> str:
        """Получение пути к пользовательской папке Applications"""
        user_home = os.path.expanduser("~")
        user_apps = os.path.join(user_home, "Applications")
        os.makedirs(user_apps, exist_ok=True)
        return os.path.join(user_apps, "Nexy.app")
    
    def get_log_path(self) -> str:
        """Получение пути к логам обновлений"""
        log_dir = os.path.expanduser("~/Library/Logs/Nexy")
        os.makedirs(log_dir, exist_ok=True)
        return os.path.join(log_dir, "updater.log")
