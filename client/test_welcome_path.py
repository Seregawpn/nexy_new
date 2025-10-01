#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправления путей к аудио файлам
"""

import sys
from pathlib import Path

# Добавляем пути
CLIENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(CLIENT_ROOT))
sys.path.insert(0, str(CLIENT_ROOT / "modules"))

def test_audio_path():
    """Тестирует поиск аудио файла"""
    print("🔍 ТЕСТ ПОИСКА АУДИО ФАЙЛА")
    print("=" * 40)
    
    try:
        from modules.welcome_message.core.types import WelcomeConfig
        
        config = WelcomeConfig()
        audio_path = config.get_audio_path()
        
        print(f"📁 Найденный путь: {audio_path}")
        print(f"✅ Файл существует: {audio_path.exists()}")
        
        if audio_path.exists():
            print(f"📊 Размер файла: {audio_path.stat().st_size} байт")
        else:
            print("❌ Файл не найден!")
            
            # Показываем альтернативные пути
            print("\n🔍 Проверяю альтернативные пути:")
            
            # Dev путь
            dev_path = Path(__file__).parent / "assets" / "audio" / "welcome_en.mp3"
            print(f"   Dev путь: {dev_path} - {'✅' if dev_path.exists() else '❌'}")
            
            # PyInstaller bundle путь (если мы в .app)
            if "Contents/MacOS" in str(Path(__file__).resolve()):
                bundle_path = Path(__file__).resolve().parent.parent / "Resources" / "assets" / "audio" / "welcome_en.mp3"
                print(f"   Bundle путь: {bundle_path} - {'✅' if bundle_path.exists() else '❌'}")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio_path()
