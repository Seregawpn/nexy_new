#!/usr/bin/env python3
"""
Тест упрощенной логики прерывания без сложных флагов
"""

import asyncio
import time
import logging
from audio_player import AudioPlayer

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_simplified_interruption():
    """Тестирует упрощенную логику прерывания"""
    print("🚀 Тест упрощенной логики прерывания")
    
    # Создаем AudioPlayer
    audio_player = AudioPlayer()
    
    # Создаем тестовые аудио данные
    import numpy as np
    sample_rate = 48000
    duration = 2.0  # 2 секунды
    samples = int(sample_rate * duration)
    
    # Генерируем синусоиду
    t = np.linspace(0, duration, samples)
    audio_data = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    
    print(f"📊 Создан тестовый аудио: {len(audio_data)} сэмплов, {duration:.1f} секунд")
    
    # Запускаем воспроизведение
    print("🔊 Запускаем воспроизведение...")
    audio_player.start_playback()
    
    # Добавляем аудио чанки
    chunk_size = 1024
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i+chunk_size]
        audio_player.add_chunk(chunk)
        print(f"📦 Добавлен чанк {i//chunk_size + 1}: {len(chunk)} сэмплов")
        
        # Небольшая пауза между чанками
        await asyncio.sleep(0.01)
    
    print(f"📊 Всего добавлено чанков: {len(audio_data)//chunk_size + 1}")
    print(f"📊 Размер очереди: {audio_player.audio_queue.qsize()}")
    print(f"📊 Размер внутреннего буфера: {len(audio_player.internal_buffer)}")
    
    # Ждем немного воспроизведения
    print("⏳ Ждем воспроизведения...")
    await asyncio.sleep(0.5)
    
    # Тестируем прерывание
    print("🚨 ТЕСТИРУЕМ ПРЕРЫВАНИЕ...")
    start_time = time.time()
    
    audio_player.clear_all_audio_data()
    
    interrupt_time = (time.time() - start_time) * 1000
    print(f"⏱️ Время прерывания: {interrupt_time:.1f}ms")
    
    # Проверяем результат
    queue_size = audio_player.audio_queue.qsize()
    buffer_size = len(audio_player.internal_buffer)
    
    print(f"📊 Результат прерывания:")
    print(f"   - Размер очереди: {queue_size}")
    print(f"   - Размер буфера: {buffer_size}")
    print(f"   - Воспроизведение: {audio_player.is_playing}")
    
    if queue_size == 0 and buffer_size == 0:
        print("✅ ПРЕРЫВАНИЕ УСПЕШНО - все буферы очищены!")
    else:
        print("❌ ПРЕРЫВАНИЕ НЕПОЛНОЕ - буферы не полностью очищены!")
    
    # Тестируем временную блокировку
    print("\n🔒 Тестируем временную блокировку буфера...")
    
    # Пытаемся добавить чанк сразу после прерывания
    test_chunk = np.array([1000, 2000, 3000], dtype=np.int16)
    print(f"📦 Пытаемся добавить тестовый чанк: {len(test_chunk)} сэмплов")
    
    if audio_player.is_buffer_locked():
        print("🚨 Буфер заблокирован - чанк не будет добавлен")
    else:
        print("✅ Буфер не заблокирован - чанк будет добавлен")
    
    audio_player.add_chunk(test_chunk)
    
    print(f"📊 Размер очереди после попытки добавления: {audio_player.audio_queue.qsize()}")
    
    # Ждем истечения блокировки
    print("⏳ Ждем истечения блокировки буфера...")
    await asyncio.sleep(0.6)  # Больше чем buffer_block_duration (0.5s)
    
    # Пытаемся добавить чанк снова
    print("📦 Пытаемся добавить чанк после истечения блокировки...")
    audio_player.add_chunk(test_chunk)
    
    print(f"📊 Размер очереди после истечения блокировки: {audio_player.audio_queue.qsize()}")
    
    if audio_player.audio_queue.qsize() > 0:
        print("✅ Блокировка истекла - чанки снова принимаются!")
    else:
        print("❌ Блокировка не истекла - чанки все еще не принимаются!")
    
    # Очищаем
    audio_player.stop_playback()
    print("🧹 Очистка завершена")

if __name__ == "__main__":
    asyncio.run(test_simplified_interruption())
