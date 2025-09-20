"""
Атомарная замена приложений с возможностью отката
"""

import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

def atomic_replace_app(new_app_path: str, target_app_path: str):
    """
    Атомарная замена приложения с возможностью отката
    
    Args:
        new_app_path: Путь к новому приложению
        target_app_path: Путь к целевому приложению
    """
    backup_path = target_app_path + ".backup"
    
    logger.info(f"Атомарная замена: {new_app_path} -> {target_app_path}")
    
    try:
        # Удаляем старый backup если есть
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path, ignore_errors=True)
        
        # Создаем backup текущего приложения
        os.rename(target_app_path, backup_path)
        logger.info(f"Создан backup: {backup_path}")
        
        # Копируем новое приложение
        subprocess.check_call(["/usr/bin/ditto", new_app_path, target_app_path])
        logger.info("✅ Приложение успешно обновлено")
        
        # Удаляем backup при успехе
        shutil.rmtree(backup_path, ignore_errors=True)
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления: {e}")
        
        # Откатываемся при ошибке
        if os.path.exists(target_app_path):
            shutil.rmtree(target_app_path, ignore_errors=True)
        
        if os.path.exists(backup_path):
            os.rename(backup_path, target_app_path)
            logger.info("Выполнен откат к предыдущей версии")
        
        raise
