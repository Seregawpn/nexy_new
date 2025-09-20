"""
Работа с DMG файлами для системы обновлений
Монтирование, размонтирование, поиск .app файлов
"""

import subprocess
import os
import tempfile
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def mount_dmg(dmg_path: str) -> str:
    """
    Монтирование DMG файла
    
    Args:
        dmg_path: Путь к DMG файлу
        
    Returns:
        str: Путь к точке монтирования
        
    Raises:
        RuntimeError: Если не удалось смонтировать
    """
    # Создаем временную директорию для монтирования
    mount_point = tempfile.mkdtemp(prefix="nexy_update_")
    
    try:
        logger.info(f"Монтирование DMG: {dmg_path} -> {mount_point}")
        
        # Монтируем DMG
        result = subprocess.run([
            "/usr/bin/hdiutil", 
            "attach", 
            "-nobrowse", 
            "-mountpoint", 
            mount_point, 
            dmg_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Ошибка монтирования DMG: {result.stderr}")
        
        logger.info(f"✅ DMG смонтирован в {mount_point}")
        return mount_point
        
    except Exception as e:
        # Очищаем временную директорию при ошибке
        try:
            os.rmdir(mount_point)
        except:
            pass
        raise RuntimeError(f"Не удалось смонтировать DMG: {e}")

def unmount_dmg(mount_point: str):
    """
    Размонтирование DMG
    
    Args:
        mount_point: Путь к точке монтирования
        
    Raises:
        RuntimeError: Если не удалось размонтировать
    """
    try:
        logger.info(f"Размонтирование DMG: {mount_point}")
        
        result = subprocess.run([
            "/usr/bin/hdiutil", 
            "detach", 
            mount_point
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.warning(f"Предупреждение при размонтировании: {result.stderr}")
            # Не выбрасываем исключение, так как DMG может быть уже размонтирован
        
        logger.info(f"✅ DMG размонтирован: {mount_point}")
        
    except Exception as e:
        logger.error(f"Ошибка размонтирования DMG: {e}")
        # Не выбрасываем исключение, чтобы не блокировать процесс обновления

def find_app_in_dmg(mount_point: str, app_name: str = "Nexy.app") -> Optional[str]:
    """
    Поиск .app файла в DMG
    
    Args:
        mount_point: Путь к точке монтирования
        app_name: Имя искомого приложения
        
    Returns:
        str: Путь к .app файлу или None если не найден
    """
    try:
        logger.info(f"Поиск {app_name} в {mount_point}")
        
        # Прямой поиск в корне DMG
        app_path = os.path.join(mount_point, app_name)
        if os.path.isdir(app_path):
            logger.info(f"✅ Найден {app_name} в корне DMG")
            return app_path
        
        # Рекурсивный поиск по всей структуре DMG
        for root, dirs, files in os.walk(mount_point):
            for dir_name in dirs:
                if dir_name.endswith(".app"):
                    found_app = os.path.join(root, dir_name)
                    logger.info(f"✅ Найден .app файл: {found_app}")
                    return found_app
        
        logger.warning(f"❌ {app_name} не найден в DMG")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка поиска .app файла в DMG: {e}")
        return None

def get_dmg_info(dmg_path: str) -> dict:
    """
    Получение информации о DMG файле
    
    Args:
        dmg_path: Путь к DMG файлу
        
    Returns:
        dict: Информация о DMG
    """
    try:
        # Получаем информацию о DMG
        result = subprocess.run([
            "/usr/bin/hdiutil", 
            "imageinfo", 
            dmg_path
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return {"error": result.stderr}
        
        info = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                info[key.strip()] = value.strip()
        
        # Добавляем размер файла
        info['file_size'] = os.path.getsize(dmg_path)
        
        logger.info(f"DMG информация: {info.get('Format', 'unknown')}, {info['file_size']} байт")
        return info
        
    except Exception as e:
        logger.error(f"Ошибка получения информации о DMG: {e}")
        return {"error": str(e)}

def cleanup_mount_points():
    """
    Очистка всех точек монтирования nexy_update_
    """
    try:
        import tempfile
        temp_dir = tempfile.gettempdir()
        
        for item in os.listdir(temp_dir):
            if item.startswith("nexy_update_"):
                mount_path = os.path.join(temp_dir, item)
                if os.path.isdir(mount_path):
                    try:
                        unmount_dmg(mount_path)
                        os.rmdir(mount_path)
                        logger.info(f"Очищена точка монтирования: {mount_path}")
                    except:
                        pass
        
    except Exception as e:
        logger.error(f"Ошибка очистки точек монтирования: {e}")

def verify_dmg_structure(mount_point: str) -> bool:
    """
    Проверка структуры DMG
    
    Args:
        mount_point: Путь к точке монтирования
        
    Returns:
        bool: True если структура корректна
    """
    try:
        # Проверяем, что это действительно DMG
        if not os.path.isdir(mount_point):
            return False
        
        # Проверяем наличие .app файла
        app_found = find_app_in_dmg(mount_point)
        
        if app_found:
            # Проверяем структуру .app
            contents_path = os.path.join(app_found, "Contents")
            if os.path.isdir(contents_path):
                info_plist = os.path.join(contents_path, "Info.plist")
                macos_dir = os.path.join(contents_path, "MacOS")
                
                if os.path.exists(info_plist) and os.path.isdir(macos_dir):
                    logger.info("✅ Структура DMG корректна")
                    return True
        
        logger.warning("❌ Структура DMG некорректна")
        return False
        
    except Exception as e:
        logger.error(f"Ошибка проверки структуры DMG: {e}")
        return False
