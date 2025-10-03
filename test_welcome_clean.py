#!/usr/bin/env python3
"""
Чистый тест welcome message функциональности
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent / "client"))
sys.path.append(str(Path(__file__).parent / "server" / "modules" / "grpc_service"))

import grpc.aio

# Импорты protobuf
try:
    import streaming_pb2
    import streaming_pb2_grpc
    print("✅ Protobuf модули импортированы успешно")
except ImportError as e:
    print(f"❌ Ошибка импорта protobuf: {e}")
    sys.exit(1)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_welcome_message():
    """Тест welcome message с английским текстом"""
    try:
        print("🚀 Запуск чистого теста welcome message")
        print("=" * 60)
        
        # Подключение к серверу
        server_address = "localhost:50051"
        print(f"🔗 Подключаемся к серверу: {server_address}")
        
        async with grpc.aio.insecure_channel(server_address) as channel:
            stub = streaming_pb2_grpc.StreamingServiceStub(channel)
            
            # Создаем welcome запрос с английским текстом
            request = streaming_pb2.WelcomeRequest(
                text="Hi! This is a clean test of the welcome message.",
                session_id="clean_test_session"
            )
            
            print("📤 Отправляем welcome запрос...")
            
            # Отправляем запрос и получаем ответы
            audio_chunks = []
            metadata = {}
            
            async for response in stub.GenerateWelcomeAudio(request, timeout=30):
                content = response.WhichOneof('content')
                
                if content == 'audio_chunk':
                    chunk = response.audio_chunk
                    if chunk.audio_data:
                        audio_bytes = bytes(chunk.audio_data)
                        if audio_bytes:
                            audio_chunks.append(audio_bytes)
                            print(f"🎵 Получен аудио чанк: {len(audio_bytes)} байт")
                
                elif content == 'metadata':
                    metadata = {
                        'method': response.metadata.method,
                        'duration_sec': response.metadata.duration_sec,
                        'sample_rate': response.metadata.sample_rate,
                        'channels': response.metadata.channels,
                    }
                    print(f"📊 Метаданные: method={metadata['method']}, duration={metadata['duration_sec']:.1f}s, sample_rate={metadata['sample_rate']}")
                
                elif content == 'end_message':
                    print(f"✅ Завершение: {response.end_message}")
                    break
                
                elif content == 'error_message':
                    print(f"❌ Ошибка: {response.error_message}")
                    return False
            
            if audio_chunks:
                total_bytes = sum(len(chunk) for chunk in audio_chunks)
                print(f"🎉 Успех! Получено {len(audio_chunks)} чанков, всего {total_bytes} байт аудио")
                
                # Сохраняем тестовое аудио
                with open("test_welcome_clean.wav", "wb") as f:
                    f.write(b''.join(audio_chunks))
                print("💾 Тестовое аудио сохранено в test_welcome_clean.wav")
                
                return True
            else:
                print("❌ Не получено аудио данных")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    success = await test_welcome_message()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 ТЕСТ WELCOME MESSAGE ПРОШЕЛ УСПЕШНО!")
    else:
        print("❌ ТЕСТ WELCOME MESSAGE НЕ ПРОШЕЛ")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
