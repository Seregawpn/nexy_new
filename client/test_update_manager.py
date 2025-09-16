#!/usr/bin/env python3
"""
Тест модуля обновлений
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

from modules.update_manager import UpdateManager, UpdateConfig, UpdateStatus
from integration.core.event_bus import EventBus
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler

async def test_update_manager():
    """Тест модуля обновлений"""
    print("🧪 ТЕСТ МОДУЛЯ ОБНОВЛЕНИЙ")
    print("=" * 50)
    
    # Создаем компоненты
    event_bus = EventBus()
    state_manager = ApplicationStateManager()
    error_handler = ErrorHandler(event_bus)
    
    # Создаем конфигурацию
    config = UpdateConfig(
        enabled=True,
        check_interval=1,  # 1 час для тестирования
        check_time="02:00",
        auto_install=True,
        announce_updates=False,  # Тихий режим
        check_on_startup=True,
        appcast_url="https://api.nexy.ai/updates/appcast.xml",
        retry_attempts=3,
        retry_delay=300,
        silent_mode=True,
        log_updates=True
    )
    
    # Создаем менеджер обновлений
    update_manager = UpdateManager(
        config=config,
        event_bus=event_bus,
        state_manager=state_manager
    )
    
    print(f"✅ Менеджер обновлений создан")
    print(f"📊 Статус: {update_manager.get_current_status().value}")
    print(f"🔧 Включен: {update_manager.is_enabled()}")
    
    # Тестируем проверку обновлений
    print("\n🔍 Тестирую проверку обновлений...")
    update_info = await update_manager.check_for_updates()
    
    if update_info:
        print(f"📦 Доступно обновление: {update_info.version}")
        print(f"📝 Описание: {update_info.release_notes}")
        print(f"📏 Размер: {update_info.file_size} байт")
    else:
        print("❌ Обновления не найдены")
    
    print(f"📊 Статус после проверки: {update_manager.get_current_status().value}")
    
    # Тестируем получение информации
    available_update = update_manager.get_available_update()
    if available_update:
        print(f"📦 Доступное обновление: {available_update.version}")
    else:
        print("❌ Нет доступных обновлений")
    
    print("\n✅ Тест завершен")

if __name__ == "__main__":
    asyncio.run(test_update_manager())
