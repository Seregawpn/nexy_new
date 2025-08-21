#!/usr/bin/env python3
"""
Тест Timing Window - проверяем время между получением аудио и прерыванием
"""

import asyncio
import time
import numpy as np
import sys
import os

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_player import AudioPlayer

async def test_timing_window():
    """Тестируем timing window между получением аудио и прерыванием"""
    
    print("🕐 ТЕСТ TIMING WINDOW")
    print("=" * 60)
    
    # Тестируем разные задержки
    delays = [0, 10, 25, 50, 100, 200]  # миллисекунды
    
    for delay_ms in delays:
        print(f"\n🔍 ТЕСТ ЗАДЕРЖКИ: {delay_ms}ms")
        print("-" * 40)
        
        # 1. Создаем AudioPlayer
        audio_player = AudioPlayer()
        
        # 2. Создаем тестовое аудио (5 секунд)
        sample_rate = 44100
        duration = 5
        test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
        test_audio = (test_audio * 0.3).astype(np.float32)
        
        # 3. Добавляем аудио в очередь
        chunk_size = 44100  # 1 секунда
        for i in range(0, len(test_audio), chunk_size):
            chunk = test_audio[i:i+chunk_size]
            audio_player.add_chunk(chunk)
        
        print(f"   📦 Добавлено {len(test_audio)//chunk_size} чанков")
        print(f"   📊 Размер очереди: {audio_player.audio_queue.qsize()}")
        
        # 4. Ждем начала воспроизведения
        print("   ⏰ Ждем начала воспроизведения...")
        await asyncio.sleep(0.5)  # 500ms для стабилизации
        
        # 5. Ждем указанную задержку
        if delay_ms > 0:
            print(f"   ⏳ Ждем {delay_ms}ms...")
            await asyncio.sleep(delay_ms / 1000.0)
        
        # 6. ПРЕРЫВАНИЕ
        print("   🚨 ПРЕРЫВАНИЕ!")
        interrupt_start = time.time()
        
        audio_player.clear_all_audio_data()
        
        interrupt_time = (time.time() - interrupt_start) * 1000
        print(f"   ⏱️ Время прерывания: {interrupt_time:.1f}ms")
        
        # 7. Проверяем состояние
        queue_size = audio_player.audio_queue.qsize()
        print(f"   📊 Размер очереди после прерывания: {queue_size}")
        
        # 8. Дополнительное ожидание для проверки
        print("   ⏰ Ждем 1 секунду для проверки...")
        await asyncio.sleep(1.0)
        
        # 9. Финальная проверка
        final_queue_size = audio_player.audio_queue.qsize()
        print(f"   📊 Финальный размер очереди: {final_queue_size}")
        
        # 10. Анализ результата
        if final_queue_size == 0:
            print("   ✅ ПРЕРЫВАНИЕ РАБОТАЕТ!")
        else:
            print("   ❌ ПРЕРЫВАНИЕ НЕ РАБОТАЕТ!")
            print(f"   🔍 Новые чанки продолжают поступать: {final_queue_size}")
        
        # 11. Очистка
        audio_player.force_stop_immediately()
        
        print(f"   {'✅' if final_queue_size == 0 else '❌'} Тест {delay_ms}ms завершен")
        
        # Пауза между тестами
        if delay_ms < delays[-1]:
            print("   ⏳ Пауза 2 секунды...")
            await asyncio.sleep(2.0)
    
    print("\n" + "=" * 60)
    print("🎯 ТЕСТ TIMING WINDOW ЗАВЕРШЕН!")
    
    # Анализ результатов
    print("\n📊 АНАЛИЗ РЕЗУЛЬТАТОВ:")
    print("   🔍 Если прерывание работает при 0ms, но не работает при больших задержках,")
    print("   🔍 то проблема в TIMING WINDOW - прерывание срабатывает слишком поздно!")

async def test_audio_flow_timing():
    """Тестируем timing аудио потока"""
    
    print("\n🎵 ТЕСТ TIMING АУДИО ПОТОКА")
    print("=" * 60)
    
    audio_player = AudioPlayer()
    
    # Создаем короткое аудио (1 секунда)
    sample_rate = 44100
    duration = 1
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    
    print(f"   📦 Создано аудио: {len(test_audio)} сэмплов ({duration}s)")
    
    # Добавляем аудио
    audio_player.add_chunk(test_audio)
    print(f"   📊 Размер очереди: {audio_player.audio_queue.qsize()}")
    
    # Запускаем воспроизведение
    print("   🎵 Запускаю воспроизведение...")
    await asyncio.sleep(0.1)  # 100ms
    
    # Тестируем прерывание в разные моменты
    for i in range(10):
        delay = i * 0.1  # 0ms, 100ms, 200ms, ...
        print(f"\n   🔍 Тест {i+1}: прерывание через {delay*1000:.0f}ms")
        
        # Ждем указанное время
        if delay > 0:
            await asyncio.sleep(delay)
        
        # Прерываем
        interrupt_start = time.time()
        audio_player.clear_all_audio_data()
        interrupt_time = (time.time() - interrupt_start) * 1000
        
        print(f"      ⏱️ Время прерывания: {interrupt_time:.1f}ms")
        
        # Проверяем состояние
        queue_size = audio_player.audio_queue.qsize()
        print(f"      📊 Размер очереди: {queue_size}")
        
        if queue_size == 0:
            print(f"      ✅ Прерывание работает при {delay*1000:.0f}ms")
        else:
            print(f"      ❌ Прерывание НЕ работает при {delay*1000:.0f}ms")
            break
        
        # Сброс для следующего теста
        if i < 9:
            audio_player.add_chunk(test_audio)
            await asyncio.sleep(0.1)
    
    # Очистка
    audio_player.force_stop_immediately()
    
    print("\n" + "=" * 60)
    print("🎯 ТЕСТ TIMING АУДИО ПОТОКА ЗАВЕРШЕН!")

if __name__ == "__main__":
    print("🚀 Запуск тестов Timing Window...")
    
    # Тест 1: Timing Window
    asyncio.run(test_timing_window())
    
    # Тест 2: Audio Flow Timing
    asyncio.run(test_audio_flow_timing())
