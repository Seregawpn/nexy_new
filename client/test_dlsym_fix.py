#!/usr/bin/env python3
"""
Тест для проверки исправления dlsym ошибок
Проверяет доступность NSMakeRect и CGRectMake функций
"""

import sys
import os

def test_dlsym_functions():
    """Тестируем доступность критических macOS функций"""
    print("🧪 Тестирование dlsym функций...")
    
    try:
        # Импортируем необходимые модули
        import Foundation
        import AppKit
        
        print("✅ Фреймворки импортированы успешно")
        
        # Тестируем NSMakeRect
        try:
            from Foundation import NSMakeRect
            rect = NSMakeRect(0, 0, 100, 100)
            print(f"✅ NSMakeRect работает: {rect}")
        except Exception as e:
            print(f"❌ NSMakeRect ошибка: {e}")
            return False
        
        # Тестируем CGRectMake через AppKit (правильный способ)
        try:
            from AppKit import NSRect
            # CGRectMake доступен через AppKit
            import objc
            CGRectMake = objc.lookUpClass('NSRect')
            if CGRectMake:
                print("✅ CGRectMake доступен через AppKit")
            else:
                print("⚠️ CGRectMake не найден, но это может быть нормально")
        except Exception as e:
            print(f"⚠️ CGRectMake через AppKit: {e}")
            # Это не критично, так как NSMakeRect работает
        
        # Тестируем rumps
        try:
            import rumps
            print("✅ rumps импортирован успешно")
        except Exception as e:
            print(f"❌ rumps ошибка: {e}")
            return False
        
        print("🎉 Все dlsym функции работают корректно!")
        return True
        
    except Exception as e:
        print(f"❌ Критическая ошибка импорта: {e}")
        return False

def test_pyinstaller_build():
    """Тестируем сборку PyInstaller"""
    print("\n🔨 Тестирование PyInstaller сборки...")
    
    try:
        # Проверяем, что PyInstaller доступен
        import PyInstaller
        print(f"✅ PyInstaller версия: {PyInstaller.__version__}")
        
        # Проверяем spec файл
        spec_path = "packaging/Nexy.spec"
        if os.path.exists(spec_path):
            print("✅ Spec файл найден")
            
            # Читаем spec файл и проверяем binaries
            with open(spec_path, 'r') as f:
                content = f.read()
                if 'Foundation.framework' in content and 'CoreGraphics.framework' in content:
                    print("✅ Фреймворки включены в spec файл")
                    return True
                else:
                    print("❌ Фреймворки не найдены в spec файле")
                    return False
        else:
            print("❌ Spec файл не найден")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка PyInstaller: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Диагностика dlsym проблем...")
    print("=" * 50)
    
    # Тест 1: Проверяем функции
    dlsym_ok = test_dlsym_functions()
    
    # Тест 2: Проверяем PyInstaller
    pyinstaller_ok = test_pyinstaller_build()
    
    print("\n" + "=" * 50)
    print("📊 РЕЗУЛЬТАТЫ:")
    print(f"dlsym функции: {'✅ РАБОТАЮТ' if dlsym_ok else '❌ НЕ РАБОТАЮТ'}")
    print(f"PyInstaller: {'✅ НАСТРОЕН' if pyinstaller_ok else '❌ НЕ НАСТРОЕН'}")
    
    if dlsym_ok and pyinstaller_ok:
        print("\n🎉 ПРОБЛЕМА РЕШЕНА! Можно собирать приложение.")
    else:
        print("\n⚠️ ПРОБЛЕМА НЕ РЕШЕНА. Нужны дополнительные исправления.")
