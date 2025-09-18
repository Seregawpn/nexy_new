#!/usr/bin/env python3
"""
Прямой тест TTS через gRPC - обходим проблему с клавиатурой
"""

import asyncio
import grpc
import sys
import os
from pathlib import Path
import sounddevice as sd
import numpy as np

# Добавляем путь к клиенту для импорта protobuf
client_path = Path(__file__).parent / "client"
sys.path.insert(0, str(client_path))

try:
    import streaming_pb2
    import streaming_pb2_grpc
except ImportError:
    print("❌ Не удалось импортировать protobuf файлы")
    print("Убедитесь, что файлы streaming_pb2.py и streaming_pb2_grpc.py существуют в client/")
    sys.exit(1)

async def test_edge_tts_via_grpc():
    """Тест Edge TTS через gRPC сервер"""
    print("🗣️ ТЕСТ EDGE TTS ЧЕРЕЗ GRPC")
    print("=" * 50)
    
    # Подключаемся к gRPC серверу
    channel = grpc.aio.insecure_channel('localhost:50051')
    stub = streaming_pb2_grpc.StreamingServiceStub(channel)
    
    try:
        # Создаем запрос
        request = streaming_pb2.StreamRequest(
            hardware_id="test-hardware-id-12345",
            text_input="Hello, this is a test of Edge text to speech through gRPC server.",
            screenshot_data=b"",  # Пустой скриншот для теста
            session_id="test-session-001"
        )
        
        print(f"📤 Отправляем запрос: '{request.text_input}'")
        print("🔄 Ожидаем ответ от сервера...")
        
        # Отправляем запрос и получаем стрим ответов
        response_stream = stub.ProcessVoiceStream(request)
        
        audio_chunks = []
        text_response = ""
        
        async for response in response_stream:
            if response.audio_chunk:
                print(f"🎵 Получен аудио чанк: {len(response.audio_chunk)} байт")
                audio_chunks.append(response.audio_chunk)
            
            if response.text_response:
                text_response = response.text_response
                print(f"💬 Текстовый ответ: {text_response}")
        
        if audio_chunks:
            print(f"✅ Получено {len(audio_chunks)} аудио чанков")
            
            # Объединяем все чанки
            full_audio = b''.join(audio_chunks)
            print(f"📊 Общий размер аудио: {len(full_audio)} байт")
            
            # Конвертируем в numpy array для воспроизведения
            # Предполагаем int16, 48kHz, mono (согласно конфигурации)
            audio_array = np.frombuffer(full_audio, dtype=np.int16)
            
            if len(audio_array) > 0:
                print(f"🎵 Аудио массив: {len(audio_array)} сэмплов")
                print(f"📈 Диапазон значений: {audio_array.min()} - {audio_array.max()}")
                
                # Воспроизводим через sounddevice
                print("🔊 Воспроизведение...")
                sd.play(audio_array, samplerate=48000)
                sd.wait()
                
                print("✅ Edge TTS через gRPC работает!")
            else:
                print("❌ Пустой аудио массив")
        else:
            print("❌ Не получено аудио данных")
            
    except grpc.RpcError as e:
        print(f"❌ gRPC ошибка: {e}")
        print(f"   Код: {e.code()}")
        print(f"   Детали: {e.details()}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await channel.close()

async def test_azure_tts_via_grpc():
    """Тест Azure TTS через gRPC сервер"""
    print("\n🇺🇸 ТЕСТ AZURE TTS ЧЕРЕЗ GRPC")
    print("=" * 50)
    print("⚠️ Для работы Azure TTS нужно:")
    print("   1. Раскомментировать SPEECH_KEY и SPEECH_REGION в server/config.env")
    print("   2. Установить USE_EDGE_TTS=false")
    print("   3. Перезапустить сервер")
    print("🔄 Пропускаем Azure TTS тест (требует настройки)")

async def main():
    """Главная функция тестирования"""
    print("🧪 ПРЯМОЕ ТЕСТИРОВАНИЕ TTS ЧЕРЕЗ GRPC")
    print("=" * 60)
    print("🎯 Обходим проблему с клавиатурой - тестируем TTS напрямую")
    print("=" * 60)
    
    # Проверяем доступность gRPC сервера
    try:
        channel = grpc.aio.insecure_channel('localhost:50051')
        await asyncio.wait_for(channel.channel_ready(), timeout=5.0)
        print("✅ gRPC сервер доступен")
        await channel.close()
    except asyncio.TimeoutError:
        print("❌ gRPC сервер недоступен на localhost:50051")
        print("💡 Запустите сервер: cd server && python main.py")
        return
    except Exception as e:
        print(f"❌ Ошибка подключения к gRPC серверу: {e}")
        return
    
    # Тестируем Edge TTS
    await test_edge_tts_via_grpc()
    
    # Информация об Azure TTS
    await test_azure_tts_via_grpc()
    
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print("=" * 40)
    print("🎤 Edge TTS (gRPC)     - протестирован")
    print("🎤 Azure TTS (gRPC)    - требует настройки ключей")
    print("\n💡 Если Edge TTS работает, проблема НЕ в генерации речи,")
    print("   а в системе обработки клавиатурного ввода!")

if __name__ == "__main__":
    asyncio.run(main())
