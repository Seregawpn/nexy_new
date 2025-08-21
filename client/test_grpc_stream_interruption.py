#!/usr/bin/env python3
"""
Тест gRPC Stream Interruption - проверяем прерывание gRPC стрима на сервере
"""

import asyncio
import time
import sys
import os

# Добавляем путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from grpc_client import GrpcClient
from utils.hardware_id import get_hardware_id

async def test_grpc_stream_interruption():
    """Тестируем прерывание gRPC стрима на сервере"""
    
    print("🌐 ТЕСТ GPRC STREAM INTERRUPTION")
    print("=" * 60)
    
    # 1. Проверка сервера
    print("1️⃣ ПРОВЕРКА СЕРВЕРА:")
    print("   🔍 Убедитесь, что сервер запущен: python grpc_server.py")
    print("   🔍 Сервер должен быть доступен на localhost:50051")
    
    # 2. Инициализация компонентов
    print("\n2️⃣ ИНИЦИАЛИЗАЦИЯ КОМПОНЕНТОВ:")
    grpc_client = GrpcClient()
    hardware_id = get_hardware_id()
    print("   ✅ GrpcClient создан")
    print(f"   🆔 Hardware ID: {hardware_id[:20]}...")
    
    # 3. Подключение к серверу
    print("\n3️⃣ ПОДКЛЮЧЕНИЕ К СЕРВЕРУ:")
    try:
        await grpc_client.connect()
        print("   ✅ Подключение к серверу установлено")
    except Exception as e:
        print(f"   ❌ Ошибка подключения: {e}")
        print("   🔧 Запустите сервер: cd ../server && python grpc_server.py")
        return
    
    # 4. Устанавливаем hardware_id
    grpc_client.hardware_id = hardware_id
    print("   ✅ Hardware ID установлен в GrpcClient")
    
    # 5. Тестируем прерывание БЕЗ активного стрима
    print("\n4️⃣ ТЕСТ ПРЕРЫВАНИЯ БЕЗ АКТИВНОГО СТРИМА:")
    print("   🔇 Вызываю force_interrupt_server()...")
    
    interrupt_start = time.time()
    grpc_client.force_interrupt_server()
    
    # Ждем завершения асинхронной задачи
    await asyncio.sleep(0.1)
    
    interrupt_time = (time.time() - interrupt_start) * 1000
    print(f"   ⏱️ Время прерывания: {interrupt_time:.1f}ms")
    
    # 6. Тестируем прерывание С АКТИВНЫМ СТРИМОМ
    print("\n5️⃣ ТЕСТ ПРЕРЫВАНИЯ С АКТИВНЫМ СТРИМОМ:")
    
    # Создаем простую команду для короткого ответа
    test_command = "Скажи только 'Привет'"
    print(f"   📝 Команда: {test_command}")
    
    # Запускаем gRPC стрим
    print("   🚀 Запускаю gRPC стрим...")
    streaming_task = asyncio.create_task(
        grpc_client.stream_audio(test_command, hardware_id=hardware_id).__anext__()
    )
    
    # Ждем немного для начала стрима
    await asyncio.sleep(1.0)
    
    # Прерываем стрим
    print("   🚨 ПРЕРЫВАНИЕ АКТИВНОГО СТРИМА!")
    interrupt_start = time.time()
    
    # Отменяем задачу
    streaming_task.cancel()
    
    # Отправляем команду прерывания на сервер
    grpc_client.force_interrupt_server()
    
    interrupt_time = (time.time() - interrupt_start) * 1000
    print(f"   ⏱️ Время прерывания активного стрима: {interrupt_time:.1f}ms")
    
    # 7. Ждем завершения
    print("\n6️⃣ ОЖИДАНИЕ ЗАВЕРШЕНИЯ:")
    print("   ⏰ Ждем 2 секунды для проверки...")
    await asyncio.sleep(2.0)
    
    # 8. Проверяем результат
    print("\n7️⃣ ПРОВЕРКА РЕЗУЛЬТАТА:")
    
    # Проверяем, что задача была отменена
    if streaming_task.cancelled():
        print("   ✅ streaming_task отменен")
    else:
        print("   ❌ streaming_task НЕ отменен")
    
    # 9. Тестируем повторное прерывание
    print("\n8️⃣ ТЕСТ ПОВТОРНОГО ПРЕРЫВАНИЯ:")
    print("   🔇 Вызываю force_interrupt_server() повторно...")
    
    repeat_interrupt_start = time.time()
    grpc_client.force_interrupt_server()
    
    # Ждем завершения
    await asyncio.sleep(0.1)
    
    repeat_interrupt_time = (time.time() - repeat_interrupt_start) * 1000
    print(f"   ⏱️ Время повторного прерывания: {repeat_interrupt_time:.1f}ms")
    
    # 10. Завершение
    print("\n9️⃣ ЗАВЕРШЕНИЕ:")
    print("   🧹 Очистка ресурсов...")
    
    try:
        await grpc_client.disconnect()
        print("   ✅ gRPC соединение закрыто")
    except:
        pass
    
    print("\n" + "=" * 60)
    print("🎯 ТЕСТ GPRC STREAM INTERRUPTION ЗАВЕРШЕН!")
    
    # Анализ результатов
    if interrupt_time < 100:  # Меньше 100ms
        print("✅ ПРЕРЫВАНИЕ GPRC СТРИМА РАБОТАЕТ БЫСТРО!")
    else:
        print("⚠️ ПРЕРЫВАНИЕ GPRC СТРИМА МЕДЛЕННОЕ!")
        
    if streaming_task.cancelled():
        print("✅ GPRC СТРИМ КОРРЕКТНО ОТМЕНЕН!")
    else:
        print("❌ GPRC СТРИМ НЕ ОТМЕНЕН!")

async def test_server_interrupt_response():
    """Тестируем ответ сервера на прерывание"""
    
    print("\n🔄 ТЕСТ ОТВЕТА СЕРВЕРА НА ПРЕРЫВАНИЕ:")
    print("=" * 60)
    
    # Создаем новый клиент для тестирования
    grpc_client = GrpcClient()
    hardware_id = get_hardware_id()
    
    try:
        # Подключаемся
        await grpc_client.connect()
        grpc_client.hardware_id = hardware_id
        print("   ✅ Подключение установлено")
        
        # Тестируем прерывание
        print("   🚨 Тестирую прерывание...")
        grpc_client.force_interrupt_server()
        
        # Ждем ответа
        await asyncio.sleep(0.2)
        
        print("   ✅ Тест завершен")
        
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    finally:
        await grpc_client.disconnect()

if __name__ == "__main__":
    print("🚀 Запуск тестов gRPC Stream Interruption...")
    
    # Тест 1: gRPC Stream Interruption
    asyncio.run(test_grpc_stream_interruption())
    
    # Тест 2: Server Interrupt Response
    asyncio.run(test_server_interrupt_response())
