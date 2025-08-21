#!/usr/bin/env python3
"""
Тест Thread Safety - проверяем безопасность потоков и асинхронности
"""

import asyncio
import time
import numpy as np
import threading
import sys
import os

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_player import AudioPlayer

async def test_thread_safety():
    """Тестируем безопасность потоков"""
    
    print("🧵 ТЕСТ THREAD SAFETY")
    print("=" * 60)
    
    # 1. Создаем AudioPlayer
    audio_player = AudioPlayer()
    
    # 2. Создаем тестовое аудио
    sample_rate = 44100
    duration = 3  # 3 секунды
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    
    print(f"   📦 Создано аудио: {len(test_audio)} сэмплов ({duration}s)")
    
    # 3. Функция для добавления аудио в отдельном потоке
    def add_audio_in_thread():
        """Добавляет аудио в отдельном потоке"""
        try:
            chunk_size = 44100  # 1 секунда
            for i in range(0, len(test_audio), chunk_size):
                chunk = test_audio[i:i+chunk_size]
                audio_player.add_chunk(chunk)
                time.sleep(0.1)  # 100ms задержка между чанками
                print(f"      📦 Чанк {i//chunk_size + 1} добавлен в потоке")
        except Exception as e:
            print(f"      ❌ Ошибка в потоке: {e}")
    
    # 4. Функция для прерывания в отдельном потоке
    def interrupt_in_thread():
        """Прерывает аудио в отдельном потоке"""
        try:
            time.sleep(0.5)  # Ждем 500ms
            print("      🚨 ПРЕРЫВАНИЕ В ОТДЕЛЬНОМ ПОТОКЕ!")
            audio_player.clear_all_audio_data()
            print("      ✅ Прерывание выполнено в потоке")
        except Exception as e:
            print(f"      ❌ Ошибка прерывания в потоке: {e}")
    
    # 5. Запускаем поток добавления аудио
    print("   🧵 Запускаю поток добавления аудио...")
    audio_thread = threading.Thread(target=add_audio_in_thread)
    audio_thread.start()
    
    # 6. Запускаем поток прерывания
    print("   🧵 Запускаю поток прерывания...")
    interrupt_thread = threading.Thread(target=interrupt_in_thread)
    interrupt_thread.start()
    
    # 7. Ждем завершения потоков
    print("   ⏰ Жду завершения потоков...")
    audio_thread.join()
    interrupt_thread.join()
    
    # 8. Проверяем результат
    print("   🔍 Проверяю результат...")
    await asyncio.sleep(1.0)  # Ждем 1 секунду
    
    final_queue_size = audio_player.audio_queue.qsize()
    print(f"   📊 Финальный размер очереди: {final_queue_size}")
    
    if final_queue_size == 0:
        print("   ✅ THREAD SAFETY РАБОТАЕТ!")
    else:
        print("   ❌ THREAD SAFETY НЕ РАБОТАЕТ!")
    
    # 9. Очистка
    audio_player.force_stop_immediately()

async def test_concurrent_access():
    """Тестируем одновременный доступ к AudioPlayer"""
    
    print("\n🔄 ТЕСТ CONCURRENT ACCESS")
    print("=" * 60)
    
    audio_player = AudioPlayer()
    
    # Создаем тестовое аудио
    sample_rate = 44100
    duration = 2
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    
    # Функция для одновременного добавления и прерывания
    def concurrent_operations():
        """Выполняет одновременные операции"""
        try:
            # Добавляем аудио
            audio_player.add_chunk(test_audio)
            print("      📦 Аудио добавлено")
            
            # Сразу прерываем
            audio_player.clear_all_audio_data()
            print("      🚨 Аудио прервано")
            
        except Exception as e:
            print(f"      ❌ Ошибка: {e}")
    
    # Запускаем несколько потоков одновременно
    threads = []
    for i in range(5):
        thread = threading.Thread(target=concurrent_operations)
        threads.append(thread)
        thread.start()
        print(f"   🧵 Поток {i+1} запущен")
    
    # Ждем завершения
    for thread in threads:
        thread.join()
    
    # Проверяем результат
    await asyncio.sleep(0.5)
    final_queue_size = audio_player.audio_queue.qsize()
    print(f"   📊 Финальный размер очереди: {final_queue_size}")
    
    if final_queue_size == 0:
        print("   ✅ CONCURRENT ACCESS РАБОТАЕТ!")
    else:
        print("   ❌ CONCURRENT ACCESS НЕ РАБОТАЕТ!")
    
    # Очистка
    audio_player.force_stop_immediately()

async def test_interrupt_flag_safety():
    """Тестируем безопасность флага прерывания"""
    
    print("\n🚨 ТЕСТ INTERRUPT FLAG SAFETY")
    print("=" * 60)
    
    audio_player = AudioPlayer()
    
    # Создаем тестовое аудио
    sample_rate = 44100
    duration = 2
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    
    # Функция для проверки флага прерывания
    def check_interrupt_flag():
        """Проверяет флаг прерывания"""
        try:
            flag_set = audio_player.interrupt_flag.is_set()
            print(f"      🚨 Флаг прерывания: {flag_set}")
            return flag_set
        except Exception as e:
            print(f"      ❌ Ошибка проверки флага: {e}")
            return False
    
    # Функция для установки флага прерывания
    def set_interrupt_flag():
        """Устанавливает флаг прерывания"""
        try:
            audio_player.interrupt_flag.set()
            print("      ✅ Флаг прерывания установлен")
        except Exception as e:
            print(f"      ❌ Ошибка установки флага: {e}")
    
    # Функция для сброса флага прерывания
    def clear_interrupt_flag():
        """Сбрасывает флаг прерывания"""
        try:
            audio_player.interrupt_flag.clear()
            print("      🔄 Флаг прерывания сброшен")
        except Exception as e:
            print(f"      ❌ Ошибка сброса флага: {e}")
    
    # Тестируем в разных потоках
    print("   🧵 Тестирую флаг прерывания в разных потоках...")
    
    # Поток 1: проверяет флаг
    thread1 = threading.Thread(target=check_interrupt_flag)
    thread1.start()
    
    # Поток 2: устанавливает флаг
    thread2 = threading.Thread(target=set_interrupt_flag)
    thread2.start()
    
    # Поток 3: снова проверяет флаг
    thread3 = threading.Thread(target=check_interrupt_flag)
    thread3.start()
    
    # Ждем завершения
    thread1.join()
    thread2.join()
    thread3.join()
    
    # Финальная проверка
    final_flag = check_interrupt_flag()
    print(f"   📊 Финальное состояние флага: {final_flag}")
    
    if final_flag:
        print("   ✅ INTERRUPT FLAG SAFETY РАБОТАЕТ!")
    else:
        print("   ❌ INTERRUPT FLAG SAFETY НЕ РАБОТАЕТ!")
    
    # Очистка
    audio_player.force_stop_immediately()

if __name__ == "__main__":
    print("🚀 Запуск тестов Thread Safety...")
    
    # Тест 1: Thread Safety
    asyncio.run(test_thread_safety())
    
    # Тест 2: Concurrent Access
    asyncio.run(test_concurrent_access())
    
    # Тест 3: Interrupt Flag Safety
    asyncio.run(test_interrupt_flag_safety())
