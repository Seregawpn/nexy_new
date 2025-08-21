#!/usr/bin/env python3
"""
Тест Sounddevice Buffering - проверяем системную буферизацию sounddevice
"""

import asyncio
import time
import numpy as np
import sys
import os
import sounddevice as sd

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_player import AudioPlayer

async def test_sounddevice_buffering():
    """Тестируем системную буферизацию sounddevice"""
    
    print("🔊 ТЕСТ SOUNDDEVICE BUFFERING")
    print("=" * 60)
    
    # 1. Проверка sounddevice
    print("1️⃣ ПРОВЕРКА SOUNDDEVICE:")
    try:
        devices = sd.query_devices()
        print(f"   ✅ Доступно устройств: {len(devices)}")
        
        default_device = sd.default.device
        print(f"   🎵 Устройство по умолчанию: {default_device}")
        
        # Получаем информацию о текущем устройстве
        if default_device[1] is not None:
            device_info = sd.query_devices(default_device[1])
            print(f"   📊 Каналы: {device_info['max_input_channels']} вход, {device_info['max_output_channels']} выход")
            print(f"   🎯 Частота: {device_info['default_samplerate']} Hz")
    except Exception as e:
        print(f"   ❌ Ошибка sounddevice: {e}")
        return
    
    # 2. Тест прямого воспроизведения
    print("\n2️⃣ ТЕСТ ПРЯМОГО ВОСПРОИЗВЕДЕНИЯ:")
    
    # Создаем тестовое аудио (1 секунда)
    sample_rate = 44100
    duration = 1
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    
    print(f"   📦 Создано аудио: {len(test_audio)} сэмплов ({duration}s)")
    
    # Воспроизводим напрямую через sounddevice
    print("   🎵 Воспроизвожу через sounddevice...")
    start_time = time.time()
    
    try:
        # Воспроизводим с блокировкой
        sd.play(test_audio, sample_rate, blocking=True)
        play_time = (time.time() - start_time) * 1000
        print(f"   ⏱️ Время воспроизведения: {play_time:.1f}ms")
        
        # Тестируем остановку
        print("   🚨 Останавливаю sounddevice...")
        stop_start = time.time()
        sd.stop()
        stop_time = (time.time() - stop_start) * 1000
        print(f"   ⏱️ Время остановки: {stop_time:.1f}ms")
        
    except Exception as e:
        print(f"   ❌ Ошибка воспроизведения: {e}")
    
    # 3. Тест буферизации
    print("\n3️⃣ ТЕСТ БУФЕРИЗАЦИИ:")
    
    # Создаем длинное аудио (5 секунд)
    long_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 5, sample_rate * 5))
    long_audio = (long_audio * 0.3).astype(np.float32)
    
    print(f"   📦 Создано длинное аудио: {len(long_audio)} сэмплов (5s)")
    
    # Воспроизводим без блокировки
    print("   🎵 Воспроизвожу длинное аудио...")
    start_time = time.time()
    
    try:
        # Воспроизводим без блокировки
        stream = sd.OutputStream(
            samplerate=sample_rate,
            channels=1,
            dtype=np.float32,
            blocksize=1024
        )
        
        with stream:
            # Запускаем воспроизведение
            stream.start()
            
            # Отправляем данные по частям
            chunk_size = 4410  # 100ms
            for i in range(0, len(long_audio), chunk_size):
                chunk = long_audio[i:i+chunk_size]
                stream.write(chunk)
                
                # Прерываем через 1 секунду
                if i >= sample_rate:
                    print("   🚨 ПРЕРЫВАНИЕ ЧЕРЕЗ 1 СЕКУНДУ!")
                    break
                
                time.sleep(0.1)  # 100ms задержка
            
            # Останавливаем
            stream.stop()
            
        play_time = (time.time() - start_time) * 1000
        print(f"   ⏱️ Время воспроизведения: {play_time:.1f}ms")
        
    except Exception as e:
        print(f"   ❌ Ошибка буферизации: {e}")
    
    # 4. Тест AudioPlayer vs Sounddevice
    print("\n4️⃣ ТЕСТ AUDIOPLAYER VS SOUNDDEVICE:")
    
    audio_player = AudioPlayer()
    
    # Создаем короткое аудио
    short_audio = np.sin(2 * np.pi * 440 * np.linspace(0, 0.5, int(sample_rate * 0.5)))
    short_audio = (short_audio * 0.3).astype(np.float32)
    
    print(f"   📦 Создано короткое аудио: {len(short_audio)} сэмплов (0.5s)")
    
    # Тестируем AudioPlayer
    print("   🎵 Тестирую AudioPlayer...")
    audio_start = time.time()
    
    audio_player.add_chunk(short_audio)
    await asyncio.sleep(0.1)  # 100ms
    
    # Прерываем AudioPlayer
    print("   🚨 ПРЕРЫВАНИЕ AUDIOPLAYER!")
    interrupt_start = time.time()
    audio_player.clear_all_audio_data()
    interrupt_time = (time.time() - interrupt_start) * 1000
    
    print(f"   ⏱️ Время прерывания AudioPlayer: {interrupt_time:.1f}ms")
    
    # Тестируем прямую остановку sounddevice
    print("   🎵 Тестирую прямую остановку sounddevice...")
    sd_start = time.time()
    sd.stop()
    sd_time = (time.time() - sd_start) * 1000
    
    print(f"   ⏱️ Время остановки sounddevice: {sd_time:.1f}ms")
    
    # 5. Сравнение
    print("\n5️⃣ СРАВНЕНИЕ:")
    print(f"   🎯 AudioPlayer прерывание: {interrupt_time:.1f}ms")
    print(f"   🎯 Sounddevice остановка: {sd_time:.1f}ms")
    
    if interrupt_time < sd_time:
        print("   ✅ AudioPlayer быстрее sounddevice!")
    else:
        print("   ⚠️ Sounddevice быстрее AudioPlayer!")
    
    # 6. Очистка
    print("\n6️⃣ ОЧИСТКА:")
    audio_player.force_stop_immediately()
    sd.stop()
    
    print("   ✅ Ресурсы очищены")

async def test_os_level_buffering():
    """Тестируем OS-уровневую буферизацию"""
    
    print("\n💻 ТЕСТ OS-УРОВНЕВОЙ БУФЕРИЗАЦИИ:")
    print("=" * 60)
    
    # Создаем AudioPlayer
    audio_player = AudioPlayer()
    
    # Создаем тестовое аудио
    sample_rate = 44100
    duration = 2
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    
    print(f"   📦 Создано аудио: {len(test_audio)} сэмплов ({duration}s)")
    
    # Добавляем аудио в очередь
    print("   📥 Добавляю аудио в очередь...")
    audio_player.add_chunk(test_audio)
    
    # Ждем начала воспроизведения
    print("   ⏰ Жду начала воспроизведения...")
    await asyncio.sleep(0.5)  # 500ms
    
    # Проверяем размер очереди
    queue_size = audio_player.audio_queue.qsize()
    print(f"   📊 Размер очереди: {queue_size}")
    
    # Прерываем
    print("   🚨 ПРЕРЫВАНИЕ!")
    interrupt_start = time.time()
    audio_player.clear_all_audio_data()
    interrupt_time = (time.time() - interrupt_start) * 1000
    
    print(f"   ⏱️ Время прерывания: {interrupt_time:.1f}ms")
    
    # Ждем дополнительно для проверки OS буферизации
    print("   ⏰ Жду 1 секунду для проверки OS буферизации...")
    await asyncio.sleep(1.0)
    
    # Финальная проверка
    final_queue_size = audio_player.audio_queue.qsize()
    print(f"   📊 Финальный размер очереди: {final_queue_size}")
    
    if final_queue_size == 0:
        print("   ✅ OS-уровневая буферизация не мешает!")
    else:
        print("   ❌ OS-уровневая буферизация мешает!")
    
    # Очистка
    audio_player.force_stop_immediately()

if __name__ == "__main__":
    print("🚀 Запуск тестов Sounddevice Buffering...")
    
    # Тест 1: Sounddevice Buffering
    asyncio.run(test_sounddevice_buffering())
    
    # Тест 2: OS Level Buffering
    asyncio.run(test_os_level_buffering())
