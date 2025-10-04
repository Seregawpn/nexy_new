"""
Утилиты для определения путей к ресурсам в упакованном приложении.

Поддерживает:
- Development режим (обычный запуск из репозитория)
- PyInstaller onefile (sys._MEIPASS)
- PyInstaller bundle (.app/Contents/Resources/)
"""

import sys
from pathlib import Path
from typing import Optional


def get_resource_base_path() -> Path:
    """
    Получить базовый путь к ресурсам приложения.
    
    Автоматически определяет правильный путь для:
    - Development режима (client/)
    - PyInstaller onefile (sys._MEIPASS)
    - PyInstaller bundle (.app/Contents/Resources/)
    
    Returns:
        Path: Базовый путь к ресурсам
    """
    # 1) PyInstaller onefile: временная распаковка в sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    
    # 2) PyInstaller bundle (.app): main.py находится в Contents/MacOS/
    #    Ресурсы в Contents/Resources/
    macos_dir = Path(sys.argv[0]).resolve().parent
    resources = macos_dir.parent / "Resources"
    
    # Проверяем, что это действительно bundle и Resources существует
    if resources.exists() and (resources / "assets").exists():
        return resources
    
    # 3) Development режим: определяем относительно структуры модуля
    #    __file__ = client/modules/welcome_message/utils/resource_path.py
    #    client_root = client/
    client_root = Path(__file__).parent.parent.parent.parent
    
    # Проверка, что мы в правильной директории
    if (client_root / "main.py").exists():
        return client_root
    
    # Fallback: текущая директория
    return Path.cwd()


def get_resource_path(relative_path: str, base_path: Optional[Path] = None) -> Path:
    """
    Получить полный путь к ресурсу.
    
    Args:
        relative_path: Относительный путь к ресурсу (например, "assets/audio/welcome_en.mp3")
        base_path: Базовый путь (если None, определяется автоматически)
    
    Returns:
        Path: Полный путь к ресурсу
    """
    if base_path is None:
        base_path = get_resource_base_path()
    
    return base_path / relative_path


def resource_exists(relative_path: str, base_path: Optional[Path] = None) -> bool:
    """
    Проверить существование ресурса.
    
    Args:
        relative_path: Относительный путь к ресурсу
        base_path: Базовый путь (если None, определяется автоматически)
    
    Returns:
        bool: True если ресурс существует
    """
    resource_path = get_resource_path(relative_path, base_path)
    return resource_path.exists()




