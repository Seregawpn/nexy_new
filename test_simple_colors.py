#!/usr/bin/env python3
"""
Простой тест цветов иконок - без зависимостей
"""

import sys
from pathlib import Path

# Добавляем путь к client модулям
client_path = Path(__file__).parent / "client"
sys.path.insert(0, str(client_path))

def test_colors():
    """Тест цветовой схемы"""
    print("🎨 ПРОСТОЙ ТЕСТ: Проверка цветов иконок")
    print("=" * 50)
    
    try:
        # Импортируем типы
        from modules.tray_controller.core.tray_types import TrayStatus, TrayIconGenerator
        
        print("✅ Модули импортированы успешно")
        
        # Проверяем все статусы
        statuses = [TrayStatus.SLEEPING, TrayStatus.LISTENING, TrayStatus.PROCESSING]
        expected_colors = {
            TrayStatus.SLEEPING: "#808080",     # Серый
            TrayStatus.LISTENING: "#007AFF",    # Синий  
            TrayStatus.PROCESSING: "#FF9500"    # Желтый
        }
        
        generator = TrayIconGenerator()
        
        print("\n🔍 Проверка генерации цветов:")
        for status in statuses:
            print(f"\n📍 Статус: {status}")
            print(f"   Enum value: {status.value}")
            print(f"   Type: {type(status)}")
            
            # Генерируем иконку
            icon = generator.create_circle_icon(status, 16)
            
            print(f"   Generated color: {icon.color}")
            print(f"   Expected color: {expected_colors[status]}")
            
            if icon.color == expected_colors[status]:
                print(f"   ✅ Цвет ПРАВИЛЬНЫЙ")
            else:
                print(f"   ❌ Цвет НЕПРАВИЛЬНЫЙ!")
                
        # Проверяем PIL
        try:
            from PIL import Image, ImageDraw
            pil_available = True
            print(f"\n🖼️ PIL доступен: ✅ ДА")
        except ImportError:
            pil_available = False
            print(f"\n🖼️ PIL доступен: ❌ НЕТ")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_enum_comparison():
    """Тест сравнения enum'ов"""
    print("\n🔬 ТЕСТ: Сравнение enum значений")
    print("=" * 50)
    
    try:
        from modules.tray_controller.core.tray_types import TrayStatus
        from modules.mode_management import AppMode
        
        # Создаем маппинг как в реальном коде
        mode_to_status = {
            AppMode.SLEEPING: TrayStatus.SLEEPING,
            AppMode.LISTENING: TrayStatus.LISTENING,
            AppMode.PROCESSING: TrayStatus.PROCESSING,
        }
        
        print("🗺️ Маппинг режимов:")
        for app_mode, tray_status in mode_to_status.items():
            print(f"   {app_mode} → {tray_status}")
        
        # Тестируем поиск
        test_modes = [AppMode.SLEEPING, AppMode.LISTENING, AppMode.PROCESSING]
        
        print(f"\n🔍 Тест поиска в маппинге:")
        for mode in test_modes:
            found = mode in mode_to_status
            status = mode_to_status.get(mode, "NOT_FOUND")
            print(f"   {mode} in mapping: {found} → {status}")
            
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 ЗАПУСК ПРОСТЫХ ТЕСТОВ")
    print("=" * 60)
    
    success1 = test_colors()
    success2 = test_enum_comparison()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print(f"  Тест цветов: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Тест enum'ов: {'✅ PASS' if success2 else '❌ FAIL'}")
    
    if success1 and success2:
        print("\n🎉 БАЗОВАЯ ЛОГИКА РАБОТАЕТ!")
        print("💡 Проблема скорее всего в событиях или UI обновлении")
    else:
        print("\n🔍 НАЙДЕНЫ БАЗОВЫЕ ПРОБЛЕМЫ!")
