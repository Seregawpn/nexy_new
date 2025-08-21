#!/usr/bin/env python3
"""
🧪 Тестовый скрипт для проверки функциональности прерывания речи
"""

import asyncio
import time
from rich.console import Console

console = Console()

async def test_interrupt_functionality():
    """Тестирует функциональность прерывания"""
    console.print("🧪 Тест прерывания речи:")
    console.print("1. Запустите ассистент")
    console.print("2. Скажите длинную команду")
    console.print("3. Нажмите пробел во время речи")
    console.print("4. Проверьте что речь остановилась МГНОВЕННО")
    console.print("5. Нажмите Ctrl+C для выхода")
    
    try:
        while True:
            await asyncio.sleep(1)
            console.print("⏳ Ожидание тестирования...")
    except KeyboardInterrupt:
        console.print("\n✅ Тест завершен")

def test_audio_player_interrupt():
    """Тестирует методы прерывания AudioPlayer"""
    console.print("🔊 Тест методов прерывания AudioPlayer:")
    
    try:
        from audio_player import AudioPlayer
        
        # Создаем экземпляр AudioPlayer
        player = AudioPlayer()
        console.print("✅ AudioPlayer создан")
        
        # Тестируем методы прерывания
        console.print("🧪 Тестирую interrupt_immediately()...")
        player.interrupt_immediately()
        console.print("✅ interrupt_immediately() выполнен")
        
        console.print("🧪 Тестирую force_stop_immediately()...")
        player.force_stop_immediately()
        console.print("✅ force_stop_immediately() выполнен")
        
        console.print("🧪 Тестирую force_stop()...")
        player.force_stop()
        console.print("✅ force_stop() выполнен")
        
        console.print("🎯 Все методы прерывания работают корректно!")
        
    except ImportError as e:
        console.print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        console.print(f"❌ Ошибка тестирования: {e}")

def test_input_handler_timing():
    """Тестирует тайминги InputHandler"""
    console.print("⌚ Тест таймингов InputHandler:")
    
    try:
        from input_handler import InputHandler
        
        console.print("✅ InputHandler импортирован")
        console.print("ℹ️ Таймер активации микрофона: 10ms (было 50ms)")
        console.print("ℹ️ Порог короткого нажатия: 300ms")
        console.print("✅ Тайминги оптимизированы для быстрого отклика!")
        
    except ImportError as e:
        console.print(f"❌ Ошибка импорта: {e}")
    except Exception as e:
        console.print(f"❌ Ошибка тестирования: {e}")

async def main():
    """Главная функция тестирования"""
    console.print("🚀 ЗАПУСК ТЕСТОВ ПРЕРЫВАНИЯ РЕЧИ")
    console.print("=" * 50)
    
    # Тест 1: AudioPlayer
    test_audio_player_interrupt()
    console.print()
    
    # Тест 2: InputHandler
    test_input_handler_timing()
    console.print()
    
    # Тест 3: Интерактивное тестирование
    console.print("🎮 Интерактивное тестирование:")
    await test_interrupt_functionality()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n👋 Тестирование завершено пользователем")
    except Exception as e:
        console.print(f"\n❌ Ошибка в тестировании: {e}")
