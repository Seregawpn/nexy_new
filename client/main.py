"""
Nexy AI Assistant - Главный файл приложения
Только точка входа и инициализация SimpleModuleCoordinator
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем пути к модулям (централизованно)
CLIENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(CLIENT_ROOT))
sys.path.insert(0, str(CLIENT_ROOT / "modules"))
sys.path.insert(0, str(CLIENT_ROOT / "integration"))

# --- Ранняя инициализация pydub/ffmpeg (до любых вызовов pydub) ---
def init_ffmpeg_for_pydub():
    """Настраивает путь к встроенному ffmpeg для pydub.

    Порядок поиска:
    1) PyInstaller onefile: sys._MEIPASS/resources/ffmpeg/ffmpeg
    2) PyInstaller bundle:  Contents/Resources/resources/ffmpeg/ffmpeg
    3) Dev-режим:           resources/ffmpeg/ffmpeg (в корне проекта)
    """
    try:
        from pydub import AudioSegment  # noqa: F401
    except Exception:
        return

    ffmpeg_path = None
    # 1) onefile (временная распаковка)
    if hasattr(sys, "_MEIPASS"):
        cand = Path(getattr(sys, "_MEIPASS")) / "resources" / "ffmpeg" / "ffmpeg"
        if cand.exists():
            ffmpeg_path = cand
    # 2) bundle (.app): .../Contents/MacOS/main.py -> ../Resources/resources/ffmpeg/ffmpeg
    if ffmpeg_path is None:
        macos_dir = Path(__file__).resolve().parent
        resources_ffmpeg = macos_dir.parent / "Resources" / "resources" / "ffmpeg" / "ffmpeg"
        if resources_ffmpeg.exists():
            ffmpeg_path = resources_ffmpeg
        else:
            # Проверяем альтернативное расположение в Frameworks (PyInstaller иногда кладет туда)
            frameworks_ffmpeg = macos_dir.parent / "Frameworks" / "resources" / "ffmpeg" / "ffmpeg"
            if frameworks_ffmpeg.exists():
                ffmpeg_path = frameworks_ffmpeg
    # 3) dev-режим (репозиторий)
    if ffmpeg_path is None:
        dev_ffmpeg = Path(__file__).resolve().parent / "resources" / "ffmpeg" / "ffmpeg"
        if dev_ffmpeg.exists():
            ffmpeg_path = dev_ffmpeg

    if ffmpeg_path and ffmpeg_path.exists():
        try:
            from pydub import AudioSegment
            os.environ["FFMPEG_BINARY"] = str(ffmpeg_path)
            AudioSegment.converter = str(ffmpeg_path)
        except Exception:
            pass

# Выполняем инициализацию до импортов модулей, использующих pydub
init_ffmpeg_for_pydub()

# --- Фикс PyObjC для macOS (до импорта rumps) ---
# ВАЖНО: Должен быть выполнен ДО импорта любых модулей, использующих rumps
# Исправляет проблему "dlsym cannot find symbol NSMakeRect in CFBundle"
try:
    import AppKit
    import Foundation
    # Копируем NSMakeRect и другие символы из AppKit в Foundation
    if not hasattr(Foundation, "NSMakeRect"):
        Foundation.NSMakeRect = getattr(AppKit, "NSMakeRect", None)
    if not hasattr(Foundation, "NSMakePoint"):
        Foundation.NSMakePoint = getattr(AppKit, "NSMakePoint", None)
    if not hasattr(Foundation, "NSMakeSize"):
        Foundation.NSMakeSize = getattr(AppKit, "NSMakeSize", None)
    if not hasattr(Foundation, "NSMakeRange"):
        Foundation.NSMakeRange = getattr(AppKit, "NSMakeRange", None)
except Exception:
    # Если PyObjC недоступен или ошибка - продолжаем
    pass

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция"""
    try:
        # Импортируем SimpleModuleCoordinator
        from integration.core.simple_module_coordinator import SimpleModuleCoordinator
        
        # Создаем координатор
        coordinator = SimpleModuleCoordinator()
        
        # Запускаем (run() сам вызовет initialize() и проверку дублирования)
        await coordinator.run()                                                         
        
    except Exception as e:
        print(f"💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Создаем новый event loop для главного потока
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("\n⏹️ Приложение прервано пользователем")
    finally:
        loop.close()



                                                                                                 
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         