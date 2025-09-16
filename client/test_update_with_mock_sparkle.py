#!/usr/bin/env python3
"""
Тест модуля обновлений с имитацией Sparkle Framework
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
        self.published_events = []
    
    async def publish(self, event_type, data):
        print(f"📢 EventBus: {event_type} - {data}")
        self.published_events.append((event_type, data))
    
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

# Создаем мок Sparkle Handler
class MockSparkleHandler:
    """Заглушка для SparkleHandler с имитацией обновлений"""
    
    def __init__(self, appcast_url):
        self.appcast_url = appcast_url
        self.is_available = True  # Имитируем доступность
        self.mock_update_available = True  # Имитируем наличие обновления
    
    def is_framework_available(self):
        return self.is_available
    
    async def check_for_updates(self):
        """Имитация проверки обновлений"""
        print("🔍 Имитация проверки обновлений через Sparkle...")
        await asyncio.sleep(0.5)  # Имитация сетевого запроса
        
        if self.mock_update_available:
            from modules.update_manager.core.types import UpdateInfo
            return UpdateInfo(
                version="1.71.0",
                build_number=171,
                release_notes="Исправления и улучшения для слепых пользователей",
                download_url="https://your-server.com/Nexy_1.71.0.dmg",
                file_size=50000000,
                signature="mock_signature_12345",
                pub_date="2025-09-15T02:00:00Z",
                is_mandatory=False
            )
        return None
    
    async def download_update(self, update_info):
        """Имитация скачивания обновления"""
        print(f"📥 Имитация скачивания обновления {update_info.version}...")
        await asyncio.sleep(1)  # Имитация скачивания
        
        from modules.update_manager.core.types import UpdateResult, UpdateStatus
        return UpdateResult(
            success=True,
            status=UpdateStatus.DOWNLOADING,
            message="Обновление скачано успешно",
            update_info=update_info
        )
    
    async def install_update(self, update_info):
        """Имитация установки обновления"""
        print(f"🔧 Имитация установки обновления {update_info.version}...")
        await asyncio.sleep(2)  # Имитация установки
        
        from modules.update_manager.core.types import UpdateResult, UpdateStatus
        return UpdateResult(
            success=True,
            status=UpdateStatus.INSTALLING,
            message="Обновление установлено успешно",
            update_info=update_info
        )
    
    async def restart_application(self):
        """Имитация перезапуска приложения"""
        print("🔄 Имитация перезапуска приложения...")
        await asyncio.sleep(1)  # Имитация перезапуска
        
        from modules.update_manager.core.types import UpdateResult, UpdateStatus
        return UpdateResult(
            success=True,
            status=UpdateStatus.RESTARTING,
            message="Приложение перезапущено успешно"
        )

# Патчим модуль обновлений для использования мока
import modules.update_manager.core.update_manager as update_manager_module
original_sparkle_handler = update_manager_module.SparkleHandler
update_manager_module.SparkleHandler = MockSparkleHandler

# Импортируем модуль обновлений
from modules.update_manager import UpdateManager, UpdateConfig, UpdateStatus

async def test_update_with_mock_sparkle():
    """Тест модуля обновлений с имитацией Sparkle"""
    print("🧪 ТЕСТ МОДУЛЯ ОБНОВЛЕНИЙ С ИМИТАЦИЕЙ SPARKLE")
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
    print(f"   - Автоустановка: {config.auto_install}")
    print(f"   - Тихий режим: {config.silent_mode}")
    
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
        
        # Тестируем процесс обновления
        print(f"\n🔄 Тестирую процесс обновления...")
        await update_manager._start_update_process()
        
    else:
        print("❌ Обновления не найдены")
    
    print(f"📊 Статус после проверки: {update_manager.get_current_status().value}")
    
    # Проверяем опубликованные события
    print(f"\n📢 Опубликованные события:")
    for event_type, data in event_bus.published_events:
        print(f"   - {event_type}: {data}")
    
    # Тестируем остановку
    print(f"\n⏹️ Тестирую остановку...")
    await update_manager.stop()
    print(f"✅ Менеджер обновлений остановлен")
    
    print(f"\n✅ ТЕСТ С ИМИТАЦИЕЙ SPARKLE ЗАВЕРШЕН")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_update_with_mock_sparkle())
