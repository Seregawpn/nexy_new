#!/usr/bin/env python3
"""
Тест для симуляции bundle сценария
"""

import sys
from pathlib import Path

def simulate_bundle_scenario():
    """Симулирует сценарий поиска в bundle"""
    print("🔍 СИМУЛЯЦИЯ BUNDLE СЦЕНАРИЯ")
    print("=" * 40)
    
    # Создаем временную структуру для тестирования
    temp_dir = Path("/tmp/nexy_bundle_test")
    temp_dir.mkdir(exist_ok=True)
    
    # Создаем структуру .app bundle
    app_dir = temp_dir / "Nexy.app"
    contents_dir = app_dir / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    
    # Создаем директории
    macos_dir.mkdir(parents=True)
    resources_dir.mkdir(parents=True)
    
    # Создаем тестовый аудио файл в Resources
    audio_dir = resources_dir / "assets" / "audio"
    audio_dir.mkdir(parents=True)
    test_audio = audio_dir / "welcome_en.mp3"
    test_audio.write_text("fake audio content")
    
    # Создаем тестовый Python файл в MacOS (симулируем types.py)
    modules_dir = macos_dir / "modules" / "welcome_message" / "core"
    modules_dir.mkdir(parents=True)
    test_py = modules_dir / "types.py"
    test_py.write_text("# Test file")
    
    print(f"📁 Создана тестовая структура:")
    print(f"   App: {app_dir}")
    print(f"   MacOS: {macos_dir}")
    print(f"   Resources: {resources_dir}")
    print(f"   Аудио файл: {test_audio}")
    print(f"   Test Python: {test_py}")
    
    # Тестируем логику поиска
    print(f"\n🔍 ТЕСТИРУЕМ ЛОГИКУ ПОИСКА:")
    
    # Симулируем, что мы находимся в test_py
    original_file = __file__
    
    # Временно заменяем __file__ для тестирования
    import types
    test_module = types.ModuleType('test_module')
    test_module.__file__ = str(test_py)
    
    # Тестируем поиск MacOS директории
    resolved_path = Path(test_py).resolve()
    macos_dir_found = None
    for parent in resolved_path.parents:
        if parent.name == "MacOS":
            macos_dir_found = parent
            break
    
    print(f"   Путь к файлу: {resolved_path}")
    print(f"   Найденная MacOS: {macos_dir_found}")
    
    if macos_dir_found is not None:
        contents_dir_found = macos_dir_found.parent
        resources_path_found = contents_dir_found / "Resources"
        audio_path = resources_path_found / "assets" / "audio" / "welcome_en.mp3"
        
        print(f"   Contents: {contents_dir_found}")
        print(f"   Resources: {resources_path_found}")
        print(f"   Аудио путь: {audio_path}")
        print(f"   Аудио существует: {audio_path.exists()}")
        
        if audio_path.exists():
            print(f"   ✅ УСПЕХ: Аудио файл найден!")
        else:
            print(f"   ❌ ОШИБКА: Аудио файл не найден!")
    else:
        print(f"   ❌ ОШИБКА: MacOS директория не найдена!")
    
    # Очистка
    import shutil
    shutil.rmtree(temp_dir)
    print(f"\n🧹 Тестовая структура удалена")

if __name__ == "__main__":
    simulate_bundle_scenario()
