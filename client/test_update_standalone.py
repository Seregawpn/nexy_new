#!/usr/bin/env python3
"""
Автономный тест модуля обновлений
Тестируем модуль обновлений отдельно от основного приложения
"""

import asyncio
import sys
import logging
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Простые заглушки для тестирования
class MockEventBus:
    """Заглушка для EventBus"""
    
    def __init__(self):
        self.subscribers = {}
    
    async def publish(self, event_type, data):
        print(f"📢 EventBus: {event_type} - {data}")
    
    def subscribe(self, event_type, callback, priority=None):
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
        print(f"📝 Подписка на событие: {event_type}")

class MockStateManager:
    """Заглушка для ApplicationStateManager"""
    
    def __init__(self):
        self.current_mode = "SLEEPING"
    
    def get_current_mode(self):
        return self.current_mode
    
    def set_mode(self, mode):
        self.current_mode = mode

class MockErrorHandler:
    """Заглушка для ErrorHandler"""
    
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    def handle_error(self, error, severity, category, context):
        print(f"❌ Ошибка в {context}: {error}")

# Импортируем модуль обновлений
from modules.update_manager import UpdateManager, UpdateConfig, UpdateStatus

async def test_update_manager_standalone():
    """Автономный тест модуля обновлений"""
    print("🧪 АВТОНОМНЫЙ ТЕСТ МОДУЛЯ ОБНОВЛЕНИЙ")
    print("=" * 60)
    
    # Создаем заглушки
    event_bus = MockEventBus()
    state_manager = MockStateManager()
    error_handler = MockErrorHandler(event_bus)
    
    # Создаем конфигурацию для тестирования
    config = UpdateConfig(
        enabled=True,
        check_interval=1,  # 1 час для тестирования
        check_time="02:00",
        auto_install=True,
        announce_updates=False,  # Тихий режим
        check_on_startup=True,
        appcast_url="https://your-server.com/appcast.xml",
        retry_attempts=3,
        retry_delay=300,
        silent_mode=True,  # Полностью тихий режим
        log_updates=True
    )
    
    print(f"📋 Конфигурация:")
    print(f"   - Включен: {config.enabled}")
    print(f"   - Интервал проверки: {config.check_interval} часов")
    print(f"   - Время проверки: {config.check_time}")
    print(f"   - Автоустановка: {config.auto_install}")
    print(f"   - Тихий режим: {config.silent_mode}")
    print(f"   - URL обновлений: {config.appcast_url}")
    
    # Создаем менеджер обновлений
    update_manager = UpdateManager(
        config=config,
        event_bus=event_bus,
        state_manager=state_manager
    )
    
    print(f"\n✅ Менеджер обновлений создан")
    print(f"📊 Статус: {update_manager.get_current_status().value}")
    print(f"🔧 Включен: {update_manager.is_enabled()}")
    
    # Тестируем инициализацию
    print(f"\n🔧 Тестирую инициализацию...")
    await update_manager.start()
    print(f"✅ Менеджер обновлений запущен")
    
    # Тестируем проверку обновлений
    print(f"\n🔍 Тестирую проверку обновлений...")
    update_info = await update_manager.check_for_updates()
    
    if update_info:
        print(f"📦 Доступно обновление:")
        print(f"   - Версия: {update_info.version}")
        print(f"   - Build: {update_info.build_number}")
        print(f"   - Описание: {update_info.release_notes}")
        print(f"   - Размер: {update_info.file_size} байт")
        print(f"   - URL: {update_info.download_url}")
    else:
        print("❌ Обновления не найдены")
    
    print(f"📊 Статус после проверки: {update_manager.get_current_status().value}")
    
    # Тестируем получение информации
    available_update = update_manager.get_available_update()
    if available_update:
        print(f"📦 Доступное обновление: {available_update.version}")
    else:
        print("❌ Нет доступных обновлений")
    
    # Тестируем смену режима приложения
    print(f"\n🔄 Тестирую смену режима приложения...")
    print(f"Текущий режим: {state_manager.get_current_mode()}")
    
    # Симулируем активный режим
    state_manager.set_mode("LISTENING")
    print(f"Новый режим: {state_manager.get_current_mode()}")
    
    # Проверяем, можно ли обновляться в активном режиме
    can_check = await update_manager._can_check_updates()
    print(f"Можно ли проверять обновления в активном режиме: {can_check}")
    
    # Возвращаем в спящий режим
    state_manager.set_mode("SLEEPING")
    print(f"Режим после возврата: {state_manager.get_current_mode()}")
    
    can_check = await update_manager._can_check_updates()
    print(f"Можно ли проверять обновления в спящем режиме: {can_check}")
    
    # Тестируем остановку
    print(f"\n⏹️ Тестирую остановку...")
    await update_manager.stop()
    print(f"✅ Менеджер обновлений остановлен")
    
    print(f"\n✅ АВТОНОМНЫЙ ТЕСТ ЗАВЕРШЕН")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_update_manager_standalone())