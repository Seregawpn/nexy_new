#!/usr/bin/env python3
"""
Тест переключения иконки трея - диагностика проблемы
Запускает минимальную версию системы для проверки логики
"""

import asyncio
import sys
import os
import logging
from pathlib import Path

# Добавляем путь к client модулям
client_path = Path(__file__).parent / "client"
sys.path.insert(0, str(client_path))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_tray_icon_switching():
    """Тест переключения иконки трея"""
    print("🧪 ТЕСТ: Переключение иконки трея")
    print("=" * 50)
    
    try:
        # Импортируем необходимые модули
        from integration.core.event_bus import EventBus
        from integration.core.state_manager import ApplicationStateManager
        from integration.core.error_handler import ErrorHandler
        from integrations.tray_controller_integration import TrayControllerIntegration
        from modules.mode_management import AppMode
        from modules.tray_controller.core.tray_types import TrayStatus
        
        print("✅ Все модули импортированы успешно")
        
        # Создаем компоненты
        event_bus = EventBus()
        state_manager = ApplicationStateManager()
        error_handler = ErrorHandler()
        
        # Подключаем EventBus к StateManager
        state_manager.attach_event_bus(event_bus)
        print("✅ StateManager подключен к EventBus")
        
        # Создаем TrayControllerIntegration
        tray_integration = TrayControllerIntegration(
            event_bus=event_bus,
            state_manager=state_manager,
            error_handler=error_handler
        )
        print("✅ TrayControllerIntegration создан")
        
        # Инициализируем (но не запускаем полностью)
        print("\n🔧 Инициализация TrayControllerIntegration...")
        success = await tray_integration.initialize()
        if not success:
            print("❌ Ошибка инициализации TrayControllerIntegration")
            return False
        print("✅ TrayControllerIntegration инициализирован")
        
        # Проверяем маппинг режимов
        print(f"\n🗺️ Маппинг режимов: {tray_integration.mode_to_status}")
        
        # Тестируем переключение режимов
        print("\n🧪 ТЕСТ 1: Переключение SLEEPING → LISTENING")
        print("-" * 40)
        state_manager.set_mode(AppMode.LISTENING)
        
        # Ждем обработки событий
        await asyncio.sleep(0.1)
        
        print("\n🧪 ТЕСТ 2: Переключение LISTENING → PROCESSING")
        print("-" * 40)
        state_manager.set_mode(AppMode.PROCESSING)
        
        # Ждем обработки событий
        await asyncio.sleep(0.1)
        
        print("\n🧪 ТЕСТ 3: Переключение PROCESSING → SLEEPING")
        print("-" * 40)
        state_manager.set_mode(AppMode.SLEEPING)
        
        # Ждем обработки событий
        await asyncio.sleep(0.1)
        
        print("\n✅ Все тесты выполнены")
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("💡 Возможно нужно запустить из корневой папки проекта")
        return False
    except Exception as e:
        print(f"❌ Ошибка выполнения теста: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_icon_generation():
    """Тест генерации иконок"""
    print("\n🎨 ТЕСТ: Генерация цветных иконок")
    print("=" * 50)
    
    try:
        from modules.tray_controller.core.tray_types import TrayStatus, TrayIconGenerator
        from modules.tray_controller.macos.tray_icon import MacOSTrayIcon
        
        # Тестируем TrayIconGenerator
        generator = TrayIconGenerator()
        
        for status in [TrayStatus.SLEEPING, TrayStatus.LISTENING, TrayStatus.PROCESSING]:
            print(f"\n🔍 Тест генерации для {status.value}:")
            icon = generator.create_circle_icon(status, 16)
            print(f"  Status: {icon.status}")
            print(f"  Color: {icon.color}")
            print(f"  Type: {icon.icon_type}")
        
        # Тестируем MacOSTrayIcon
        print(f"\n🖼️ Тест создания файлов иконок:")
        mac_icon = MacOSTrayIcon()
        
        for status in [TrayStatus.SLEEPING, TrayStatus.LISTENING, TrayStatus.PROCESSING]:
            print(f"\n📁 Создание файла для {status.value}:")
            icon_path = mac_icon.create_icon_file(status)
            if icon_path:
                print(f"  ✅ Файл создан: {icon_path}")
                # Проверяем существование файла
                if os.path.exists(icon_path):
                    file_size = os.path.getsize(icon_path)
                    print(f"  📏 Размер файла: {file_size} байт")
                else:
                    print(f"  ❌ Файл не найден!")
            else:
                print(f"  ❌ Ошибка создания файла")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка теста генерации иконок: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_event_bus():
    """Тест EventBus"""
    print("\n📡 ТЕСТ: EventBus публикация/подписка")
    print("=" * 50)
    
    try:
        from integration.core.event_bus import EventBus, EventPriority
        
        event_bus = EventBus()
        received_events = []
        
        # Создаем обработчик событий
        async def test_handler(event):
            print(f"📨 Получено событие: {event}")
            received_events.append(event)
        
        # Подписываемся на событие
        await event_bus.subscribe("test.mode_changed", test_handler, EventPriority.HIGH)
        print("✅ Подписка на test.mode_changed создана")
        
        # Публикуем событие
        test_data = {"mode": "test_mode", "data": "test_data"}
        await event_bus.publish("test.mode_changed", test_data)
        print(f"📤 Событие опубликовано: {test_data}")
        
        # Ждем обработки
        await asyncio.sleep(0.1)
        
        # Проверяем результат
        if received_events:
            print(f"✅ Событие получено: {received_events[0]}")
            return True
        else:
            print("❌ Событие не получено")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка теста EventBus: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция теста"""
    print("🚀 ЗАПУСК ДИАГНОСТИЧЕСКИХ ТЕСТОВ ИКОНКИ ТРЕЯ")
    print("=" * 60)
    
    # Меняем рабочую директорию на client
    os.chdir(client_path)
    print(f"📁 Рабочая директория: {os.getcwd()}")
    
    # Тест 1: EventBus
    success1 = await test_event_bus()
    
    # Тест 2: Генерация иконок
    success2 = await test_icon_generation()
    
    # Тест 3: Переключение иконок (основной)
    success3 = await test_tray_icon_switching()
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"  EventBus: {'✅ PASS' if success1 else '❌ FAIL'}")
    print(f"  Генерация иконок: {'✅ PASS' if success2 else '❌ FAIL'}")
    print(f"  Переключение иконок: {'✅ PASS' if success3 else '❌ FAIL'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Проблема может быть в UI или macOS интеграции")
    else:
        print("\n🔍 НАЙДЕНЫ ПРОБЛЕМЫ! Смотрите логи выше для диагностики")
    
    return all([success1, success2, success3])

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
