"""
Диагностический скрипт для проверки определения путей к ресурсам
"""

import sys
from pathlib import Path

# Добавляем пути к модулям
CLIENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(CLIENT_ROOT))
sys.path.insert(0, str(CLIENT_ROOT / "modules"))

from modules.welcome_message.utils.resource_path import (
    get_resource_base_path,
    get_resource_path,
    resource_exists
)
from modules.welcome_message.core.types import WelcomeConfig

def main():
    print("=" * 80)
    print("🔍 Диагностика путей к ресурсам")
    print("=" * 80)
    
    # Проверяем базовый путь
    base_path = get_resource_base_path()
    print(f"\n📁 Базовый путь: {base_path}")
    print(f"   Существует: {base_path.exists()}")
    
    # Проверяем sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        print(f"   🔹 PyInstaller режим (onefile): {sys._MEIPASS}")
    else:
        print(f"   🔹 Development режим")
    
    # Проверяем путь к main.py
    main_py = base_path / "main.py"
    print(f"\n📄 main.py: {main_py}")
    print(f"   Существует: {main_py.exists()}")
    
    # Проверяем путь к assets
    assets_audio = base_path / "assets" / "audio"
    print(f"\n📂 assets/audio: {assets_audio}")
    print(f"   Существует: {assets_audio.exists()}")
    
    if assets_audio.exists():
        audio_files = list(assets_audio.glob("welcome_*.mp3")) + list(assets_audio.glob("welcome_*.wav"))
        print(f"   Найдено аудио файлов: {len(audio_files)}")
        for audio_file in audio_files:
            print(f"      • {audio_file.name}")
    
    # Проверяем WelcomeConfig
    print(f"\n🎵 WelcomeConfig:")
    config = WelcomeConfig()
    audio_path = config.get_audio_path()
    print(f"   Конфигурация: audio_file='{config.audio_file}'")
    print(f"   Полный путь: {audio_path}")
    print(f"   Существует: {audio_path.exists()}")
    
    # Проверяем resource_exists
    print(f"\n✅ resource_exists():")
    test_paths = [
        "assets/audio/welcome_en.mp3",
        "assets/audio/welcome_en.wav",
        "assets/audio/welcome_en_old.mp3",
        "config/unified_config.yaml"
    ]
    for test_path in test_paths:
        exists = resource_exists(test_path)
        status = "✓" if exists else "✗"
        print(f"   {status} {test_path}")
    
    print("\n" + "=" * 80)
    
    # Финальный статус
    if audio_path.exists():
        print("✅ УСПЕХ: Аудио файл приветствия найден!")
    else:
        print("❌ ОШИБКА: Аудио файл приветствия не найден!")
        print("\n💡 Возможные причины:")
        print("   1. Файл не упакован в .app (проверьте Nexy.spec)")
        print("   2. Неправильное имя файла в конфигурации")
        print("   3. Файл отсутствует в assets/audio/")
    
    print("=" * 80)

if __name__ == "__main__":
    main()



