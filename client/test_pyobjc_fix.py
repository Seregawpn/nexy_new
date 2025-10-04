"""
Тест PyObjC Fix для NSMakeRect проблемы
"""

import sys
from pathlib import Path

# Добавляем пути
CLIENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(CLIENT_ROOT))
sys.path.insert(0, str(CLIENT_ROOT / "integration"))

print("=" * 80)
print("🧪 ТЕСТ PyObjC FIX ДЛЯ NSMakeRect")
print("=" * 80)

# 1. Проверка ДО фикса
print("\n1️⃣ Состояние ДО применения фикса:")
print("-" * 80)

try:
    import Foundation
    print("✓ Foundation импортирован")
    
    has_nsmake_rect_before = hasattr(Foundation, "NSMakeRect")
    print(f"  NSMakeRect в Foundation: {has_nsmake_rect_before}")
    
    if has_nsmake_rect_before:
        print("  ℹ️  NSMakeRect уже доступен (возможно, AppKit загружен раньше)")
    
except ImportError as e:
    print(f"✗ Ошибка импорта Foundation: {e}")
    sys.exit(1)

try:
    import AppKit
    print("✓ AppKit импортирован")
    
    has_in_appkit = hasattr(AppKit, "NSMakeRect")
    print(f"  NSMakeRect в AppKit: {has_in_appkit}")
    
except ImportError as e:
    print(f"✗ Ошибка импорта AppKit: {e}")
    sys.exit(1)

# 2. Применение фикса
print("\n2️⃣ Применение фикса:")
print("-" * 80)

try:
    from integration.utils.macos_pyobjc_fix import fix_pyobjc_foundation
    fix_pyobjc_foundation()
    print("✓ fix_pyobjc_foundation() выполнен")
except Exception as e:
    print(f"✗ Ошибка при применении фикса: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Проверка ПОСЛЕ фикса
print("\n3️⃣ Состояние ПОСЛЕ применения фикса:")
print("-" * 80)

has_nsmake_rect_after = hasattr(Foundation, "NSMakeRect")
print(f"  NSMakeRect в Foundation: {has_nsmake_rect_after}")

if has_nsmake_rect_after:
    print("  ✅ NSMakeRect теперь доступен в Foundation!")
else:
    print("  ❌ NSMakeRect всё ещё недоступен в Foundation!")

# Проверяем другие символы
other_symbols = ["NSMakePoint", "NSMakeSize", "NSMakeRange"]
print("\n  Дополнительные символы:")
all_symbols_ok = True
for symbol in other_symbols:
    has_it = hasattr(Foundation, symbol)
    status = "✓" if has_it else "✗"
    print(f"    {status} {symbol}: {has_it}")
    if not has_it:
        all_symbols_ok = False

# 4. Тест импорта rumps
print("\n4️⃣ Проверка импорта rumps:")
print("-" * 80)

try:
    import rumps
    print("✓ rumps успешно импортирован")
    
    # Пытаемся создать простое приложение (без запуска)
    class TestApp(rumps.App):
        def __init__(self):
            super(TestApp, self).__init__("Test", quit_button=None)
    
    test_app = TestApp()
    print("✓ Тестовое rumps.App создано успешно")
    
except ImportError as e:
    print(f"⚠️  rumps не установлен: {e}")
    print("  (Это нормально, если rumps не используется в development)")
    
except Exception as e:
    print(f"✗ Ошибка при работе с rumps: {e}")
    import traceback
    traceback.print_exc()

# 5. Итоговая сводка
print("\n" + "=" * 80)
print("📊 ИТОГОВАЯ СВОДКА")
print("=" * 80)

if has_nsmake_rect_after and all_symbols_ok:
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
    print("\n💡 Фикс работает корректно. Можно пересобрать приложение:")
    print("   cd /Users/sergiyzasorin/Development/Nexy/client")
    print("   ./packaging/build_final.sh")
    exit_code = 0
else:
    print("⚠️  ЕСТЬ ПРЕДУПРЕЖДЕНИЯ")
    print("\n💡 Проверьте логи выше для деталей")
    exit_code = 1

print("=" * 80)

sys.exit(exit_code)





