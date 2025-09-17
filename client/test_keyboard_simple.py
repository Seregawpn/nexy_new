#!/usr/bin/env python3
"""
Простой тест клавиатуры для диагностики проблемы
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

from modules.input_processing.keyboard.keyboard_monitor import KeyboardMonitor
from modules.input_processing.keyboard.types import KeyboardConfig, KeyEvent, KeyEventType

class TestKeyboardHandler:
    def __init__(self):
        self.event_count = 0
        
    async def handle_press(self, event: KeyEvent):
        self.event_count += 1
        print(f"🔑 ASYNC PRESS {self.event_count}: {event.timestamp}")
        
    async def handle_release(self, event: KeyEvent):
        self.event_count += 1
        print(f"🔑 ASYNC RELEASE {self.event_count}: {event.duration:.3f}с")

async def main():
    print("🎹 Тест async клавиатуры...")
    
    # Создаем конфигурацию
    config = KeyboardConfig(
        key_to_monitor="space",
        short_press_threshold=0.6,
        long_press_threshold=1.0,
        event_cooldown=0.1,
        hold_check_interval=0.05,
        debounce_time=0.1
    )
    
    # Создаем обработчик
    handler = TestKeyboardHandler()
    
    # Создаем монитор
    monitor = KeyboardMonitor(config)
    
    # Регистрируем async callback'и
    monitor.register_callback(KeyEventType.PRESS, handler.handle_press)
    monitor.register_callback(KeyEventType.RELEASE, handler.handle_release)
    
    # Передаем event loop
    monitor.set_loop(asyncio.get_running_loop())
    
    # Запускаем мониторинг
    monitor.start_monitoring()
    
    print("⌨️ Нажмите пробел несколько раз... (Ctrl+C для выхода)")
    
    try:
        # Ждем события
        await asyncio.sleep(30)
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван")
    finally:
        monitor.stop_monitoring()
        print(f"📊 Всего событий: {handler.event_count}")

if __name__ == "__main__":
    asyncio.run(main())

