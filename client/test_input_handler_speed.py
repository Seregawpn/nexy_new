#!/usr/bin/env python3
"""
Тест скорости InputHandler - как быстро отправляются события прерывания
"""

import asyncio
import time
import threading
from input_handler import InputHandler

async def test_input_handler_speed():
    """Тестирует скорость InputHandler при отправке событий прерывания"""
    print("🚀 Тест скорости InputHandler (ИСПРАВЛЕННАЯ ВЕРСИЯ)")
    print("📌 Тестируем: каждое нажатие пробела должно мгновенно отправлять interrupt_or_cancel")
    
    # Создаем очередь и цикл событий
    queue = asyncio.Queue()
    loop = asyncio.get_event_loop()
    
    # Создаем InputHandler
    input_handler = InputHandler(loop, queue)
    
    # Счетчики
    interrupt_events = []
    start_time = time.time()
    
    async def event_consumer():
        """Потребитель событий"""
        event_count = 0
        while event_count < 5:  # Ждем 5 событий прерывания
            try:
                event = await asyncio.wait_for(queue.get(), timeout=10.0)  # Увеличиваем таймаут
                current_time = time.time()
                
                if event == "interrupt_or_cancel":
                    event_count += 1
                    time_from_start = (current_time - start_time) * 1000
                    interrupt_events.append(time_from_start)
                    print(f"📨 Прерывание {event_count}: время {time_from_start:.1f}ms от начала теста")
                    
                    if event_count >= 5:
                        break
                else:
                    print(f"📡 Другое событие: {event}")
                    
            except asyncio.TimeoutError:
                print("⏰ Таймаут ожидания события")
                break
    
    # Запускаем потребитель
    consumer_task = asyncio.create_task(event_consumer())
    
    print("\n🎯 ИНСТРУКЦИЯ:")
    print("   1. Быстро нажмите пробел 5 раз подряд")
    print("   2. НЕ УДЕРЖИВАЙТЕ - просто быстрые нажатия")
    print("   3. Каждое нажатие должно мгновенно создать событие прерывания")
    print("\n⏱️ Начинаем измерение...")
    
    # Ждем завершения теста
    await consumer_task
    
    # Анализ результатов
    print(f"\n📊 РЕЗУЛЬТАТЫ АНАЛИЗА:")
    if len(interrupt_events) >= 2:
        print(f"   Получено событий прерывания: {len(interrupt_events)}")
        
        # Вычисляем интервалы между событиями
        intervals = []
        for i in range(1, len(interrupt_events)):
            interval = interrupt_events[i] - interrupt_events[i-1]
            intervals.append(interval)
            print(f"   Интервал {i}: {interval:.1f}ms")
        
        if intervals:
            avg_interval = sum(intervals) / len(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            
            print(f"\n   🔢 СТАТИСТИКА:")
            print(f"      Средний интервал: {avg_interval:.1f}ms")
            print(f"      Минимальный: {min_interval:.1f}ms")
            print(f"      Максимальный: {max_interval:.1f}ms")
            
            print(f"\n   📈 ОЦЕНКА:")
            if avg_interval < 200:
                print("      ✅ ОТЛИЧНО - InputHandler реагирует быстро!")
            elif avg_interval < 500:
                print("      ⚠️ ХОРОШО - InputHandler реагирует нормально")
            elif avg_interval < 1000:
                print("      ⚠️ МЕДЛЕННО - есть задержки")
            else:
                print("      ❌ ОЧЕНЬ МЕДЛЕННО - большие задержки!")
    else:
        print("   ❌ Недостаточно событий для анализа")
    
    print("\n🔍 Тест завершен!")

if __name__ == "__main__":
    asyncio.run(test_input_handler_speed())
