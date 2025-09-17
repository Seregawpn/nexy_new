#!/usr/bin/env python3
"""
Тест клавиатуры через InputProcessingIntegration
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent / "integration" / "core"))

from integration.core.event_bus import EventBus, EventPriority
from integration.core.state_manager import ApplicationStateManager, AppMode
from integration.core.error_handler import ErrorHandler
from integration.integrations.input_processing_integration import InputProcessingIntegration, InputProcessingConfig
from modules.input_processing.keyboard.types import KeyboardConfig

async def main():
    print("🎹 Тест InputProcessingIntegration...")
    
    # Создаем core компоненты
    event_bus = EventBus()
    state_manager = ApplicationStateManager()
    error_handler = ErrorHandler(event_bus)
    
    # Создаем конфигурацию
    keyboard_config = KeyboardConfig(
        key_to_monitor="space",
        short_press_threshold=0.6,
        long_press_threshold=1.0,
        event_cooldown=0.1,
        hold_check_interval=0.05,
        debounce_time=0.1
    )
    
    input_config = InputProcessingConfig(
        keyboard_config=keyboard_config,
        enable_keyboard_monitoring=True,
        auto_start=True
    )
    
    # Создаем интеграцию
    integration = InputProcessingIntegration(
        event_bus=event_bus,
        state_manager=state_manager,
        error_handler=error_handler,
        config=input_config
    )
    
    # Подписываемся на события для отладки
    async def on_voice_start(event):
        print(f"🎤 VOICE START: {event}")
    
    async def on_voice_stop(event):
        print(f"🎤 VOICE STOP: {event}")
    
    async def on_mode_change(event):
        print(f"🔄 MODE CHANGE: {event}")
    
    await event_bus.subscribe("voice.recording_start", on_voice_start)
    await event_bus.subscribe("voice.recording_stop", on_voice_stop)
    await event_bus.subscribe("app.mode_changed", on_mode_change)
    
    # Инициализируем и запускаем
    success = await integration.initialize()
    if not success:
        print("❌ Ошибка инициализации")
        return
    
    success = await integration.start()
    if not success:
        print("❌ Ошибка запуска")
        return
    
    print("✅ InputProcessingIntegration запущен")
    print("⌨️ Нажмите пробел несколько раз... (Ctrl+C для выхода)")
    
    try:
        # Ждем события
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван")
    finally:
        await integration.stop()

if __name__ == "__main__":
    asyncio.run(main())

