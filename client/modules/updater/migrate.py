"""
Вспомогательные функции путей приложения.
Политика установки: системный домен /Applications.
"""

import os
import subprocess
import shutil
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def get_current_app_path() -> str:
    """Получение пути к текущему приложению"""
    try:
        from Cocoa import NSBundle
        bundle_path = NSBundle.mainBundle().bundlePath()
        if bundle_path and bundle_path.endswith(".app"):
            return bundle_path
    except ImportError:
        pass
    
    # Fallback на стандартный путь
    return "/Applications/Nexy.app"

def get_user_app_path() -> str:
    """Возвращает целевой путь установки приложения (системный домен)."""
    return "/Applications/Nexy.app"

def migrate_to_user_directory() -> bool:
    """
    Миграция приложения в пользовательскую папку
    
    Returns:
        bool: True если миграция выполнена
    """
    current_path = get_current_app_path()
    user_path = get_user_app_path()
    
    # Если уже в пользовательской папке, ничего не делаем
    if os.path.realpath(current_path) == os.path.realpath(user_path):
        logger.info("Приложение уже в пользовательской папке")
        return False
    
    logger.info(f"Миграция из {current_path} в {user_path}")
    
    try:
        # Удаляем старое приложение в пользовательской папке если есть
        if os.path.exists(user_path):
            shutil.rmtree(user_path, ignore_errors=True)
        
        # Копируем приложение
        subprocess.check_call(["/usr/bin/ditto", current_path, user_path])
        logger.info("✅ Приложение скопировано в ~/Applications")
        
        # Запускаем из нового места
        subprocess.Popen(["/usr/bin/open", "-a", user_path])
        logger.info("✅ Приложение запущено из ~/Applications")
        
        # Завершаем текущий процесс
        logger.info("🔚 Migration: exiting current process after relaunch")
        os._exit(0)
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции: {e}")
        return False
    
    return True
