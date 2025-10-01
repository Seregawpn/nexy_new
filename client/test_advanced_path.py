#!/usr/bin/env python3
"""
Продвинутый тест для проверки логики поиска путей к аудио файлам
"""

import sys
from pathlib import Path

def test_path_logic():
    """Тестирует логику поиска путей в разных сценариях"""
    print("🔍 ПРОДВИНУТЫЙ ТЕСТ ПОИСКА ПУТЕЙ")
    print("=" * 50)
    
    audio_file = "assets/audio/welcome_en.mp3"
    
    # Симулируем логику из исправленного _find_base_path
    def find_base_path():
        # 1. PyInstaller onefile/onedir
        if hasattr(sys, "_MEIPASS"):
            candidate = Path(sys._MEIPASS)
            audio_path = candidate / audio_file
            print(f"🔍 Проверяю PyInstaller _MEIPASS: {audio_path}")
            if audio_path.exists():
                print(f"✅ Найден в _MEIPASS: {audio_path}")
                return candidate
            
            # Частый случай: ресурсы лежат в подкаталоге Resources
            resources_candidate = candidate / "Resources"
            audio_path = resources_candidate / audio_file
            print(f"🔍 Проверяю _MEIPASS/Resources: {audio_path}")
            if audio_path.exists():
                print(f"✅ Найден в _MEIPASS/Resources: {audio_path}")
                return resources_candidate
        
        # 2. PyInstaller bundle (.app): ищем каталог MacOS -> Contents -> Resources
        resolved_path = Path(__file__).resolve()
        macos_dir = None
        for parent in resolved_path.parents:
            if parent.name == "MacOS":
                macos_dir = parent
                break
        
        if macos_dir is not None:
            contents_dir = macos_dir.parent  # MacOS -> Contents
            resources_path = contents_dir / "Resources"  # Contents -> Resources
            audio_path = resources_path / audio_file
            print(f"🔍 Проверяю bundle Resources: {audio_path}")
            if audio_path.exists():
                print(f"✅ Найден в bundle: {audio_path}")
                return resources_path
        
        # 3. Dev-режим (репозиторий)
        dev_path = Path(__file__).parent
        audio_path = dev_path / audio_file
        print(f"🔍 Проверяю dev-режим: {audio_path}")
        if audio_path.exists():
            print(f"✅ Найден в dev-режиме: {audio_path}")
            return dev_path
        
        # 4. Fallback
        print(f"❌ Файл не найден нигде!")
        return dev_path
    
    # Тестируем текущий сценарий
    print("\n📋 ТЕКУЩИЙ СЦЕНАРИЙ:")
    print(f"   Файл: {Path(__file__).resolve()}")
    print(f"   PyInstaller onefile: {hasattr(sys, '_MEIPASS')}")
    
    # Проверяем, находимся ли мы в bundle
    resolved_path = Path(__file__).resolve()
    macos_dir = None
    for parent in resolved_path.parents:
        if parent.name == "MacOS":
            macos_dir = parent
            break
    
    if macos_dir is not None:
        print(f"   В bundle: Да (MacOS: {macos_dir})")
        contents_dir = macos_dir.parent
        resources_path = contents_dir / "Resources"
        print(f"   Contents: {contents_dir}")
        print(f"   Resources: {resources_path}")
        print(f"   Resources существует: {resources_path.exists()}")
    else:
        print(f"   В bundle: Нет")
    
    print(f"   Dev-режим: {Path(__file__).parent / audio_file}")
    print(f"   Dev файл существует: {(Path(__file__).parent / audio_file).exists()}")
    
    # Запускаем поиск
    print("\n🔍 ЗАПУСК ПОИСКА:")
    result = find_base_path()
    print(f"\n✅ РЕЗУЛЬТАТ: {result}")

if __name__ == "__main__":
    test_path_logic()
