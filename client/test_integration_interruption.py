#!/usr/bin/env python3
"""
Интеграционный тест прерывания: StateManager + AudioPlayer + gRPC
"""

import asyncio
import time
import numpy as np
import threading
from unittest.mock import Mock, AsyncMock
import sys
import os

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audio_player import AudioPlayer

class MockGrpcClient:
    """Мок gRPC клиента для тестирования"""
    
    def __init__(self):
        self.interrupt_called = False
        self.interrupt_time = 0
        
    async def force_interrupt_server(self):
        """Мок метода прерывания сервера"""
        start_time = time.time()
        self.interrupt_called = True
        # Имитируем задержку сети
        await asyncio.sleep(0.01)  # 10ms задержка
        self.interrupt_time = (time.time() - start_time) * 1000
        print(f"   🌐 gRPC прерывание отправлено: {self.interrupt_time:.1f}ms")

class MockStateManager:
    """Мок StateManager для тестирования логики прерывания"""
    
    def __init__(self):
        self.audio_player = AudioPlayer()
        self.grpc_client = MockGrpcClient()
        self._cancelled = False
        self.streaming_task = None
        self.active_call = None
        
    def _force_interrupt_all(self):
        """Тестируем метод полного прерывания"""
        print("   🚨 _force_interrupt_all() вызван")
        start_time = time.time()
        
        # 1. Устанавливаем флаг отмены
        self._cancelled = True
        print(f"   ✅ Флаг отмены установлен: {(time.time() - start_time)*1000:.1f}ms")
        
        # 2. Прерываем аудио
        audio_start = time.time()
        self._interrupt_audio()
        audio_time = (time.time() - audio_start) * 1000
        print(f"   ✅ Аудио прервано: {audio_time:.1f}ms")
        
        # 3. Отменяем задачи
        tasks_start = time.time()
        self._cancel_tasks()
        tasks_time = (time.time() - tasks_start) * 1000
        print(f"   ✅ Задачи отменены: {tasks_time:.1f}ms")
        
        total_time = (time.time() - start_time) * 1000
        print(f"   ⏱️ Общее время прерывания: {total_time:.1f}ms")
        
    def _interrupt_audio(self):
        """Тестируем прерывание аудио"""
        print("   🔇 _interrupt_audio() вызван")
        start_time = time.time()
        
        # Устанавливаем флаг прерывания
        self.audio_player.interrupt_flag.set()
        
        # Очищаем все аудио данные
        self.audio_player.clear_all_audio_data()
        
        time_taken = (time.time() - start_time) * 1000
        print(f"   ✅ Аудио прервано за: {time_taken:.1f}ms")
        
    def _cancel_tasks(self):
        """Тестируем отмену задач"""
        print("   🚫 _cancel_tasks() вызван")
        start_time = time.time()
        
        # Отменяем streaming_task
        if self.streaming_task:
            self.streaming_task.cancel()
            print("   ✅ streaming_task отменен")
            
        # Отменяем active_call
        if self.active_call:
            self.active_call.cancel()
            print("   ✅ active_call отменен")
            
        # Отправляем команду прерывания на сервер
        asyncio.create_task(self.grpc_client.force_interrupt_server())
        
        time_taken = (time.time() - start_time) * 1000
        print(f"   ✅ Задачи отменены за: {time_taken:.1f}ms")

async def test_integration_interruption():
    """Тестируем интеграционное прерывание"""
    
    print("🔗 ТЕСТ ИНТЕГРАЦИОННОГО ПРЕРЫВАНИЯ")
    print("=" * 60)
    
    # 1. Создание компонентов
    print("\n1️⃣ СОЗДАНИЕ КОМПОНЕНТОВ:")
    state_manager = MockStateManager()
    print("   ✅ MockStateManager создан")
    print("   ✅ AudioPlayer создан")
    print("   ✅ MockGrpcClient создан")
    
    # 2. Создание тестового аудио
    print("\n2️⃣ СОЗДАНИЕ ТЕСТОВОГО АУДИО:")
    sample_rate = 44100
    duration = 3  # 3 секунды
    test_audio = np.sin(2 * np.pi * 440 * np.linspace(0, duration, sample_rate * duration))
    test_audio = (test_audio * 0.3).astype(np.float32)
    print(f"   ✅ Тестовое аудио создано: {len(test_audio)} сэмплов")
    
    # 3. Добавление аудио в очередь
    print("\n3️⃣ ДОБАВЛЕНИЕ АУДИО В ОЧЕРЕДЬ:")
    chunk_size = 44100  # 1 секунда
    for i in range(0, len(test_audio), chunk_size):
        chunk = test_audio[i:i+chunk_size]
        state_manager.audio_player.add_chunk(chunk)
        print(f"   📦 Чанк {i//chunk_size + 1} добавлен: {len(chunk)} сэмплов")
    
    # Проверяем размер очереди
    queue_size = state_manager.audio_player.audio_queue.qsize()
    print(f"   📊 Размер очереди: {queue_size}")
    
    # 4. Создание мок-задач
    print("\n4️⃣ СОЗДАНИЕ МОК-ЗАДАЧ:")
    state_manager.streaming_task = Mock()
    state_manager.streaming_task.cancel = Mock()
    state_manager.active_call = Mock()
    state_manager.active_call.cancel = Mock()
    print("   ✅ streaming_task создан")
    print("   ✅ active_call создан")
    
    # 5. ТЕСТИРОВАНИЕ ПРЕРЫВАНИЯ
    print("\n5️⃣ 🚨 ТЕСТИРОВАНИЕ ПРЕРЫВАНИЯ:")
    print("   🔇 Вызываю _force_interrupt_all()...")
    
    interrupt_start = time.time()
    state_manager._force_interrupt_all()
    interrupt_time = (time.time() - interrupt_start) * 1000
    
    print(f"\n   ⏱️ Время выполнения прерывания: {interrupt_time:.1f}ms")
    
    # 6. ПРОВЕРКА РЕЗУЛЬТАТОВ
    print("\n6️⃣ ПРОВЕРКА РЕЗУЛЬТАТОВ:")
    
    # Проверяем флаг отмены
    cancelled_flag = state_manager._cancelled
    print(f"   🚨 Флаг отмены: {cancelled_flag}")
    
    # Проверяем размер очереди
    final_queue_size = state_manager.audio_player.audio_queue.qsize()
    print(f"   📊 Финальный размер очереди: {final_queue_size}")
    
    # Проверяем флаг прерывания аудио
    audio_interrupt_flag = state_manager.audio_player.interrupt_flag.is_set()
    print(f"   🔇 Флаг прерывания аудио: {audio_interrupt_flag}")
    
    # Проверяем gRPC прерывание
    grpc_interrupt_called = state_manager.grpc_client.interrupt_called
    print(f"   🌐 gRPC прерывание вызвано: {grpc_interrupt_called}")
    
    # 7. ДОПОЛНИТЕЛЬНОЕ ОЖИДАНИЕ
    print("\n7️⃣ ДОПОЛНИТЕЛЬНОЕ ОЖИДАНИЕ:")
    await asyncio.sleep(0.1)  # Ждем 100ms для завершения gRPC
    
    # 8. ФИНАЛЬНАЯ ПРОВЕРКА
    print("\n8️⃣ ФИНАЛЬНАЯ ПРОВЕРКА:")
    
    # Проверяем, что задачи были отменены
    streaming_cancelled = state_manager.streaming_task.cancel.called
    active_call_cancelled = state_manager.active_call.cancel.called
    
    print(f"   ✅ streaming_task.cancel() вызван: {streaming_cancelled}")
    print(f"   ✅ active_call.cancel() вызван: {active_call_cancelled}")
    
    # 9. ЗАВЕРШЕНИЕ
    print("\n9️⃣ ЗАВЕРШЕНИЕ:")
    print("   🧹 Очистка ресурсов...")
    state_manager.audio_player.force_stop_immediately()
    
    print("\n" + "=" * 60)
    print("🎯 ИНТЕГРАЦИОННЫЙ ТЕСТ ЗАВЕРШЕН!")
    
    # Анализ результатов
    if interrupt_time < 50:  # Меньше 50ms
        print("✅ ПРЕРЫВАНИЕ РАБОТАЕТ БЫСТРО!")
    else:
        print("⚠️ ПРЕРЫВАНИЕ МЕДЛЕННОЕ!")
        
    if final_queue_size == 0:
        print("✅ ОЧЕРЕДЬ ПОЛНОСТЬЮ ОЧИЩЕНА!")
    else:
        print("❌ ОЧЕРЕДЬ НЕ ОЧИЩЕНА ПОЛНОСТЬЮ!")
        
    if cancelled_flag and audio_interrupt_flag and grpc_interrupt_called:
        print("✅ ВСЕ КОМПОНЕНТЫ ПРЕРЫВАНИЯ РАБОТАЮТ!")
    else:
        print("❌ НЕ ВСЕ КОМПОНЕНТЫ ПРЕРЫВАНИЯ РАБОТАЮТ!")

if __name__ == "__main__":
    print("🚀 Запуск интеграционного теста прерывания...")
    asyncio.run(test_integration_interruption())
