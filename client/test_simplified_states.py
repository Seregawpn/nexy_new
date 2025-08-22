#!/usr/bin/env python3
"""
Тест упрощенной логики с тремя состояниями
"""

import asyncio
from rich.console import Console

console = Console()

async def test_simplified_states():
    """Тестирует упрощенную логику с тремя состояниями"""
    console.print("🚀 Тест упрощенной логики с тремя состояниями")
    console.print("=" * 60)
    
    # Симулируем состояния
    states = ["SLEEPING", "LISTENING", "IN_PROCESS"]
    
    console.print("📋 Тестирую логику для каждого состояния:")
    
    for state in states:
        console.print(f"\n🎯 Тестирую состояние: {state}")
        
        if state == "SLEEPING":
            console.print("  📝 Логика для SLEEPING:")
            console.print("    • Пробел нажат → просыпаемся, переходим в LISTENING")
            console.print("    • Пробел отпущен → ничего (спим)")
            console.print("    • Результат: переход в LISTENING")
            
        elif state == "LISTENING":
            console.print("  📝 Логика для LISTENING:")
            console.print("    • Пробел нажат → ничего (уже слушаем)")
            console.print("    • Пробел отпущен → отправка команды")
            console.print("    • Результат: переход в IN_PROCESS")
            
        elif state == "IN_PROCESS":
            console.print("  📝 Логика для IN_PROCESS:")
            console.print("    • Пробел нажат → ПРЕРЫВАНИЕ работы + переход в LISTENING")
            console.print("    • Пробел отпущен → ничего (работа продолжается)")
            console.print("    • Результат: переход в LISTENING")
    
    console.print("\n✅ Преимущества упрощенной логики:")
    console.print("  1. Меньше состояний = меньше ошибок")
    console.print("  2. Простая логика = легче отлаживать")
    console.print("  3. Четкие переходы = меньше путаницы")
    console.print("  4. Легкое тестирование = быстрая отладка")
    
    console.print("\n🎯 Итоговая логика переходов:")
    console.print("  • SLEEPING → LISTENING (при нажатии пробела)")
    console.print("  • LISTENING → IN_PROCESS (после команды)")
    console.print("  • IN_PROCESS → SLEEPING (после завершения работы)")
    console.print("  • IN_PROCESS → LISTENING (при прерывании)")
    console.print("  • LISTENING → SLEEPING (при прерывании записи)")
    
    console.print("\n🌙 Режим SLEEPING:")
    console.print("  • Ассистент завершил работу")
    console.print("  • Ждет новых команд")
    console.print("  • Микрофон неактивен")
    console.print("  • Экономит ресурсы")

if __name__ == "__main__":
    try:
        asyncio.run(test_simplified_states())
    except KeyboardInterrupt:
        console.print("\n👋 Выход...")
    except Exception as e:
        console.print(f"❌ Ошибка: {e}")
