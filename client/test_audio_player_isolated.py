#!/usr/bin/env python3
"""
Изолированный тест AudioPlayer для диагностики прерывания
"""

import time
import numpy as np
import asyncio
from audio_player import AudioPlayer

async def test_audio_player_interruption():
    """Тестируем изолированное прерывание AudioPlayer"""
    
    print("🎵 ТЕСТ ИЗОЛИРОВАННОГО ПРЕРЫВАНИЯ AUDIOPLAYER")
    print("=" * 60)
    
    # 1. Инициализация
    print("\n1️⃣ ИНИЦИАЛИЗАЦИЯ:")
    audio_player = AudioPlayer()
    print(f"   ✅ AudioPlayer создан")
    
    # 2. Создание тестового аудио
    print("\n2️⃣ СОЗДАНИЕ ТЕСТОВОГО АУДИО:")
    sample_rate = 44100
    duration = 5  # 5 секунд
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    print(f"   ✅ Тестовое аудио создано: {len(test_audio)} сэмплов")
    
    # 3. Запуск воспроизведения
    print("\n3️⃣ ЗАПУСК ВОСПРОИЗВЕДЕНИЯ:")
    start_time = time.time()
    
    # Добавляем аудио чанки
    chunk_size = 44100  # 1 секунда
    for i in range(0, len(test_audio), chunk_size):
        chunk = test_audio[i:i+chunk_size]
        audio_player.add_chunk(chunk)
        print(f"   📦 Чанк {i//chunk_size + 1} добавлен: {len(chunk)} сэмплов")
    
    print(f"   ⏱️ Время добавления чанков: {(time.time() - start_time)*1000:.1f}ms")
    
    # 4. Ждем начала воспроизведения
    print("\n4️⃣ ОЖИДАНИЕ НАЧАЛА ВОСПРОИЗВЕДЕНИЯ:")
    await asyncio.sleep(1.0)  # Ждем 1 секунду
    
    # 5. ПРЕРЫВАНИЕ
    print("\n5️⃣ 🚨 ПРЕРЫВАНИЕ АУДИО:")
    interrupt_start = time.time()
    
    print("   🔇 Вызываю clear_all_audio_data()...")
    audio_player.clear_all_audio_data()
    
    interrupt_time = (time.time() - interrupt_start) * 1000
    print(f"   ⏱️ Время прерывания: {interrupt_time:.1f}ms")
    
    # 6. Проверка состояния
    print("\n6️⃣ ПРОВЕРКА СОСТОЯНИЯ ПОСЛЕ ПРЕРЫВАНИЯ:")
    
    # Проверяем размер очереди
    queue_size = audio_player.audio_queue.qsize() if hasattr(audio_player, 'audio_queue') else 'N/A'
    print(f"   📊 Размер очереди: {queue_size}")
    
    # Проверяем флаг прерывания
    interrupt_flag = audio_player.interrupt_flag.is_set() if hasattr(audio_player, 'interrupt_flag') else 'N/A'
    print(f"   🚨 Флаг прерывания: {interrupt_flag}")
    
    # Проверяем активный поток
    stream_active = audio_player.stream is not None if hasattr(audio_player, 'stream') else 'N/A'
    print(f"   🔌 Активный поток: {stream_active}")
    
    # 7. Дополнительное ожидание
    print("\n7️⃣ ДОПОЛНИТЕЛЬНОЕ ОЖИДАНИЕ:")
    await asyncio.sleep(2.0)  # Ждем еще 2 секунды
    
    print("\n8️⃣ ФИНАЛЬНАЯ ПРОВЕРКА:")
    final_queue_size = audio_player.audio_queue.qsize() if hasattr(audio_player, 'audio_queue') else 'N/A'
    print(f"   📊 Финальный размер очереди: {final_queue_size}")
    
    # 8. Завершение
    print("\n9️⃣ ЗАВЕРШЕНИЕ:")
    print("   🧹 Очистка ресурсов...")
    audio_player.force_stop_immediately()
    
    print("\n" + "=" * 60)
    print("🎯 ТЕСТ ЗАВЕРШЕН!")
    
    if interrupt_time < 100:  # Меньше 100ms
        print("✅ ПРЕРЫВАНИЕ РАБОТАЕТ БЫСТРО!")
    else:
        print("⚠️ ПРЕРЫВАНИЕ МЕДЛЕННОЕ!")
        
    if final_queue_size == 0:
        print("✅ ОЧЕРЕДЬ ПОЛНОСТЬЮ ОЧИЩЕНА!")
    else:
        print("❌ ОЧЕРЕДЬ НЕ ОЧИЩЕНА ПОЛНОСТЬЮ!")

if __name__ == "__main__":
    print("🚀 Запуск изолированного теста AudioPlayer...")
    asyncio.run(test_audio_player_interruption())
