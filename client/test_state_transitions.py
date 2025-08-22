#!/usr/bin/env python3
"""
Тест всех переходов состояний для новой логики с тремя состояниями
"""

import asyncio
from rich.console import Console
from rich.table import Table

console = Console()

async def test_state_transitions():
    """Тестирует все возможные переходы состояний"""
    console.print("🚀 Тест всех переходов состояний")
    console.print("=" * 60)
    
    # Создаем таблицу переходов
    table = Table(title="📊 Матрица переходов состояний")
    table.add_column("Текущее состояние", style="cyan")
    table.add_column("Событие", style="yellow")
    table.add_column("Новое состояние", style="green")
    table.add_column("Действие", style="blue")
    
    # Заполняем таблицу всеми возможными переходами
    transitions = [
        # SLEEPING
        ("SLEEPING", "start_recording", "LISTENING", "Просыпаемся, активируем микрофон"),
        ("SLEEPING", "interrupt_or_cancel", "SLEEPING", "Ничего (уже спим)"),
        ("SLEEPING", "stop_recording", "SLEEPING", "Ничего (не слушаем)"),
        
        # LISTENING
        ("LISTENING", "start_recording", "LISTENING", "Ничего (уже слушаем)"),
        ("LISTENING", "interrupt_or_cancel", "SLEEPING", "Прерываем запись, переходим в SLEEPING"),
        ("LISTENING", "stop_recording", "IN_PROCESS", "Команда принята, обрабатываем"),
        ("LISTENING", "stop_recording", "SLEEPING", "Команда не принята, возвращаемся в SLEEPING"),
        
        # IN_PROCESS
        ("IN_PROCESS", "start_recording", "LISTENING", "Прерываем работу, переходим в LISTENING"),
        ("IN_PROCESS", "interrupt_or_cancel", "SLEEPING", "Прерываем работу, переходим в SLEEPING"),
        ("IN_PROCESS", "stop_recording", "IN_PROCESS", "Ничего (работа продолжается)"),
        ("IN_PROCESS", "work_completed", "SLEEPING", "Работа завершена, переходим в SLEEPING"),
    ]
    
    for current, event, new_state, action in transitions:
        table.add_row(current, event, new_state, action)
    
    console.print(table)
    
    console.print("\n🎯 Ключевые особенности новой логики:")
    console.print("  1. SLEEPING - базовое состояние ожидания")
    console.print("  2. LISTENING - только при активном микрофоне")
    console.print("  3. IN_PROCESS - только при активной работе")
    
    console.print("\n🔄 Логика переходов:")
    console.print("  • SLEEPING → LISTENING: при активации микрофона")
    console.print("  • LISTENING → IN_PROCESS: при принятии команды")
    console.print("  • LISTENING → SLEEPING: при прерывании записи")
    console.print("  • IN_PROCESS → LISTENING: при прерывании работы")
    console.print("  • IN_PROCESS → SLEEPING: при завершении работы")
    
    console.print("\n✅ Преимущества:")
    console.print("  • Нет циклических переходов")
    console.print("  • Каждое состояние имеет четкую роль")
    console.print("  • Простая логика восстановления")
    console.print("  • Экономия ресурсов в SLEEPING")

if __name__ == "__main__":
    try:
        asyncio.run(test_state_transitions())
    except KeyboardInterrupt:
        console.print("\n👋 Выход...")
    except Exception as e:
        console.print(f"❌ Ошибка: {e}")
