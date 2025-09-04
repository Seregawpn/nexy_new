#!/usr/bin/env python3
"""
Простой тестовый клиент для проверки gRPC сервера
"""
import grpc
import sys
import os

# Добавляем путь к protobuf файлам
sys.path.append('client')
sys.path.append('server')

try:
    import streaming_pb2
    import streaming_pb2_grpc
except ImportError:
    print("❌ Не удалось импортировать protobuf файлы")
    print("🔧 Попробуем найти правильные файлы...")
    
    # Ищем protobuf файлы
    import os
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('_pb2_grpc.py'):
                print(f"📁 Найден: {os.path.join(root, file)}")
                sys.path.append(root)
    
    try:
        import streaming_pb2
        import streaming_pb2_grpc
        print("✅ Protobuf файлы найдены и импортированы")
    except ImportError as e:
        print(f"❌ Все еще не удается импортировать: {e}")
        sys.exit(1)

def test_server():
    """Тестирует подключение к серверу"""
    try:
        # Подключение к серверу (пробуем production сервер)
        channel = grpc.insecure_channel('20.151.51.172:50051')
        stub = streaming_pb2_grpc.StreamingServiceStub(channel)
        
        print("🔌 Подключение к серверу...")
        
        # Создаем тестовый запрос
        request = streaming_pb2.StreamRequest(
            prompt="Привет! Как дела?",
            screenshot="",  # Пустой скриншот для теста
            screen_width=1920,
            screen_height=1080,
            hardware_id="test_client_123"
        )
        
        print("📤 Отправка запроса...")
        
        # Отправляем запрос
        response_stream = stub.StreamAudio(request)
        
        print("📥 Получение ответа...")
        
        # Обрабатываем ответ
        for response in response_stream:
            if response.text_chunk:
                print(f"💬 Текст: {response.text_chunk}")
            
            if response.audio_chunk and response.audio_chunk.audio_data:
                print(f"🎵 Аудио: {len(response.audio_chunk.audio_data)} байт")
            
            if response.end_message:
                print(f"✅ Завершение: {response.end_message}")
                break
            
            if response.error_message:
                print(f"❌ Ошибка: {response.error_message}")
                break
        
        print("✅ Тест завершен успешно!")
        
    except grpc.RpcError as e:
        print(f"❌ gRPC ошибка: {e}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    test_server()
