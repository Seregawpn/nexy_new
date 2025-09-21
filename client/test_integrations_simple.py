#!/usr/bin/env python3
"""
Простой тест новых интеграций
"""

import sys
import os
import asyncio

# Добавляем путь к модулям
sys.path.append(os.path.dirname(__file__))

def test_module_imports():
    """Тест импорта модулей."""
    print("🔍 Тестирование импорта модулей...")
    
    try:
        from modules.instance_manager import InstanceManager, InstanceStatus, InstanceManagerConfig
        print("✅ InstanceManager модуль импортируется корректно")
    except ImportError as e:
        print(f"❌ Ошибка импорта InstanceManager: {e}")
        return False
    
    try:
        from modules.autostart_manager import AutostartManager, AutostartStatus, AutostartConfig
        print("✅ AutostartManager модуль импортируется корректно")
    except ImportError as e:
        print(f"❌ Ошибка импорта AutostartManager: {e}")
        return False
    
    return True

def test_integration_imports():
    """Тест импорта интеграций."""
    print("🔍 Тестирование импорта интеграций...")
    
    try:
        from integration.integrations.instance_manager_integration import InstanceManagerIntegration
        print("✅ InstanceManagerIntegration импортируется корректно")
    except ImportError as e:
        print(f"❌ Ошибка импорта InstanceManagerIntegration: {e}")
        return False
    
    try:
        from integration.integrations.autostart_manager_integration import AutostartManagerIntegration
        print("✅ AutostartManagerIntegration импортируется корректно")
    except ImportError as e:
        print(f"❌ Ошибка импорта AutostartManagerIntegration: {e}")
        return False
    
    return True

def test_configuration():
    """Тест конфигурации."""
    print("🔍 Тестирование конфигурации...")
    
    try:
        from config.unified_config_loader import UnifiedConfigLoader
        config_loader = UnifiedConfigLoader()
        config = config_loader._load_config()
        
        # Проверяем что новые секции есть в конфигурации
        if 'instance_manager' in config:
            print("✅ Секция instance_manager найдена в конфигурации")
        else:
            print("❌ Секция instance_manager НЕ найдена в конфигурации")
            return False
        
        if 'autostart' in config:
            print("✅ Секция autostart найдена в конфигурации")
        else:
            print("❌ Секция autostart НЕ найдена в конфигурации")
            return False
        
        if 'installation' in config:
            print("✅ Секция installation найдена в конфигурации")
        else:
            print("❌ Секция installation НЕ найдена в конфигурации")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка загрузки конфигурации: {e}")
        return False

def test_instance_manager_basic():
    """Базовый тест InstanceManager."""
    print("🔍 Тестирование InstanceManager...")
    
    try:
        from modules.instance_manager import InstanceManager, InstanceManagerConfig
        
        config = InstanceManagerConfig(
            enabled=True,
            lock_file="/tmp/test_nexy.lock",
            timeout_seconds=30,
            pid_check=True
        )
        
        manager = InstanceManager(config)
        print("✅ InstanceManager создан успешно")
        
        # Проверяем что методы существуют
        assert hasattr(manager, 'check_single_instance'), "Метод check_single_instance не найден"
        assert hasattr(manager, 'acquire_lock'), "Метод acquire_lock не найден"
        assert hasattr(manager, 'release_lock'), "Метод release_lock не найден"
        
        print("✅ Все методы InstanceManager доступны")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования InstanceManager: {e}")
        return False

def test_autostart_manager_basic():
    """Базовый тест AutostartManager."""
    print("🔍 Тестирование AutostartManager...")
    
    try:
        from modules.autostart_manager import AutostartManager, AutostartConfig
        
        config = AutostartConfig(
            enabled=True,
            method="launch_agent",
            bundle_id="com.nexy.assistant"
        )
        
        manager = AutostartManager(config)
        print("✅ AutostartManager создан успешно")
        
        # Проверяем что методы существуют
        assert hasattr(manager, 'enable_autostart'), "Метод enable_autostart не найден"
        assert hasattr(manager, 'disable_autostart'), "Метод disable_autostart не найден"
        assert hasattr(manager, 'get_autostart_status'), "Метод get_autostart_status не найден"
        
        print("✅ Все методы AutostartManager доступны")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования AutostartManager: {e}")
        return False

def test_pyinstaller_spec():
    """Тест PyInstaller spec."""
    print("🔍 Тестирование PyInstaller spec...")
    
    try:
        spec_file = "tools/packaging/Nexy.spec"
        if not os.path.exists(spec_file):
            print(f"❌ Файл {spec_file} не найден")
            return False
        
        with open(spec_file, 'r') as f:
            content = f.read()
        
        # Проверяем что новые модули добавлены в hiddenimports
        required_imports = [
            'modules.instance_manager.core.instance_manager',
            'modules.autostart_manager.core.autostart_manager',
            'integration.integrations.instance_manager_integration',
            'integration.integrations.autostart_manager_integration'
        ]
        
        for import_name in required_imports:
            if import_name in content:
                print(f"✅ {import_name} найден в PyInstaller spec")
            else:
                print(f"❌ {import_name} НЕ найден в PyInstaller spec")
                return False
        
        print("✅ PyInstaller spec содержит все необходимые импорты")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования PyInstaller spec: {e}")
        return False

def main():
    """Основная функция тестирования."""
    print("🧪 ЗАПУСК ТЕСТОВ НОВЫХ ИНТЕГРАЦИЙ")
    print("=" * 50)
    
    tests = [
        test_module_imports,
        test_integration_imports,
        test_configuration,
        test_instance_manager_basic,
        test_autostart_manager_basic,
        test_pyinstaller_spec
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте {test.__name__}: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        return True
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
