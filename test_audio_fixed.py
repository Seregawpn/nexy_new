#!/usr/bin/env python3
"""
Исправленный тест аудио с правильным WAV форматом
"""

import asyncio
import logging
import sys
import wave
import struct
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

def save_audio_as_wav(audio_data, sample_rate=48000, channels=1, filename="test_audio_fixed.wav"):
    """Сохраняет аудио данные в правильном WAV формате"""
    try:
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_data)
        print(f"✅ WAV файл сохранен: {filename}")
        return True
    except Exception as e:
        print(f"❌ Ошибка сохранения WAV: {e}")
        return False

async def test_audio_generation_fixed():
    """Тест генерации аудио с правильным форматом"""
    try:
        print("🚀 Запуск исправленного теста генерации аудио")
        print("=" * 60)
        
        # Подключение к серверу
        server_address = "localhost:50051"
        print(f"🔗 Подключаемся к серверу: {server_address}")
        
        async with grpc.aio.insecure_channel(server_address) as channel:
            stub = streaming_pb2_grpc.StreamingServiceStub(channel)
            
            # Создаем welcome запрос с коротким английским текстом
            request = streaming_pb2.WelcomeRequest(
                text="Hello! Test audio.",
                session_id="audio_test_fixed_session"
            )
            
            print("📤 Отправляем запрос на генерацию аудио...")
            
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
                
                # Объединяем все чанки
                raw_audio = b''.join(audio_chunks)
                
                # Сохраняем в правильном WAV формате
                sample_rate = metadata.get('sample_rate', 48000)
                channels = metadata.get('channels', 1)
                
                if save_audio_as_wav(raw_audio, sample_rate, channels):
                    # Проверяем размер файла
                    file_size = Path("test_audio_fixed.wav").stat().st_size
                    print(f"📁 Размер WAV файла: {file_size} байт")
                    
                    if file_size > 1000:  # Если файл больше 1KB, значит есть аудио
                        print("✅ WAV файл создан успешно и содержит данные")
                        return True
                    else:
                        print("❌ WAV файл слишком маленький, возможно пустой")
                        return False
                else:
                    return False
            else:
                print("❌ Не получено аудио данных")
                return False
                
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

async def main():
    """Основная функция тестирования"""
    success = await test_audio_generation_fixed()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 ТЕСТ АУДИО ГЕНЕРАЦИИ (ИСПРАВЛЕННЫЙ) ПРОШЕЛ УСПЕШНО!")
        print("🔊 Проверьте файл test_audio_fixed.wav - он должен содержать правильный WAV аудио")
    else:
        print("❌ ТЕСТ АУДИО ГЕНЕРАЦИИ (ИСПРАВЛЕННЫЙ) НЕ ПРОШЕЛ")
    
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
