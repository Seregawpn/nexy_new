"""
macOS PyObjC Fix для упакованных приложений

ПРОБЛЕМА:
В PyInstaller упакованных приложениях библиотека rumps пытается импортировать
NSMakeRect из Foundation, но этот символ находится в AppKit.
Это вызывает ошибку: "dlsym cannot find symbol NSMakeRect in CFBundle ... Foundation.framework"

РЕШЕНИЕ:
Загружаем AppKit первым и присваиваем NSMakeRect в Foundation перед импортом rumps.
Это должно быть выполнено ДО любых импортов rumps.

ИСПОЛЬЗОВАНИЕ:
    from integration.utils.macos_pyobjc_fix import fix_pyobjc_foundation
    
    # В самом начале main.py, до импорта rumps
    fix_pyobjc_foundation()
"""

import logging
import sys

logger = logging.getLogger(__name__)


def fix_pyobjc_foundation():
    """
    Исправляет проблему с NSMakeRect в Foundation для PyInstaller.
    
    Должно вызываться в самом начале приложения, до импорта rumps.
    """
    try:
        # Проверяем, что мы на macOS
        if sys.platform != "darwin":
            return
        
        logger.info("🔧 Применяю PyObjC Foundation fix для NSMakeRect...")
        
        # Импортируем AppKit первым (здесь находится настоящий NSMakeRect)
        import AppKit
        
        # Импортируем Foundation
        import Foundation
        
        # Проверяем, нужен ли фикс
        if not hasattr(Foundation, "NSMakeRect"):
            # Копируем NSMakeRect из AppKit в Foundation
            Foundation.NSMakeRect = getattr(AppKit, "NSMakeRect")
            logger.info("✅ NSMakeRect скопирован из AppKit в Foundation")
        else:
            logger.info("✅ NSMakeRect уже доступен в Foundation")
        
        # Проверяем другие потенциально проблемные символы
        problematic_symbols = [
            "NSMakePoint",
            "NSMakeSize",
            "NSMakeRange",
        ]
        
        fixed_symbols = []
        for symbol in problematic_symbols:
            if not hasattr(Foundation, symbol) and hasattr(AppKit, symbol):
                setattr(Foundation, symbol, getattr(AppKit, symbol))
                fixed_symbols.append(symbol)
        
        if fixed_symbols:
            logger.info(f"✅ Дополнительно исправлены символы: {', '.join(fixed_symbols)}")
        
        logger.info("✅ PyObjC Foundation fix применен успешно")
        
    except ImportError as e:
        # PyObjC не установлен или недоступен
        logger.warning(f"⚠️ PyObjC не доступен, пропускаю fix: {e}")
        
    except Exception as e:
        # Любая другая ошибка - логируем, но не падаем
        logger.error(f"❌ Ошибка при применении PyObjC Foundation fix: {e}")
        # Не пробрасываем исключение - лучше попытаться запуститься


def check_pyobjc_status():
    """
    Проверяет статус PyObjC и наличие проблемных символов.
    
    Полезно для диагностики.
    
    Returns:
        dict: Статус PyObjC и доступных символов
    """
    status = {
        "platform": sys.platform,
        "pyobjc_available": False,
        "appkit_available": False,
        "foundation_available": False,
        "symbols": {}
    }
    
    try:
        import Foundation
        status["foundation_available"] = True
        status["pyobjc_available"] = True
        
        import AppKit
        status["appkit_available"] = True
        
        # Проверяем ключевые символы
        symbols_to_check = [
            "NSMakeRect",
            "NSMakePoint",
            "NSMakeSize",
            "NSMakeRange",
        ]
        
        for symbol in symbols_to_check:
            status["symbols"][symbol] = {
                "in_foundation": hasattr(Foundation, symbol),
                "in_appkit": hasattr(AppKit, symbol),
            }
        
    except ImportError:
        pass
    
    return status


def print_pyobjc_diagnostics():
    """
    Выводит диагностическую информацию о PyObjC.
    
    Полезно для отладки проблем с символами.
    """
    status = check_pyobjc_status()
    
    print("\n" + "=" * 80)
    print("🔍 PyObjC Diagnostics")
    print("=" * 80)
    print(f"Platform: {status['platform']}")
    print(f"PyObjC available: {status['pyobjc_available']}")
    print(f"AppKit available: {status['appkit_available']}")
    print(f"Foundation available: {status['foundation_available']}")
    
    if status["symbols"]:
        print("\n📊 Symbol availability:")
        for symbol, availability in status["symbols"].items():
            foundation_status = "✓" if availability["in_foundation"] else "✗"
            appkit_status = "✓" if availability["in_appkit"] else "✗"
            print(f"  {symbol}:")
            print(f"    Foundation: {foundation_status}")
            print(f"    AppKit:     {appkit_status}")
    
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Запуск диагностики
    print_pyobjc_diagnostics()
    
    # Применение фикса
    fix_pyobjc_foundation()
    
    # Проверка после фикса
    print("\nПосле применения фикса:")
    print_pyobjc_diagnostics()





