#!/usr/bin/env python3
"""
Простой тест аудио генерации - проверка конкретного предложения
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к серверу
server_path = Path(__file__).parent / "server"
sys.path.insert(0, str(server_path))

async def test_sentence(text: str):
    """Тестирует генерацию конкретного предложения"""
    print(f"🗣️ ТЕСТ ПРЕДЛОЖЕНИЯ: '{text}'")
    print("=" * 60)
    
    # Тест 1: Edge TTS
    print("\n1️⃣ ТЕСТИРОВАНИЕ EDGE TTS")
    print("-" * 30)
    success_edge = await test_edge_tts_direct(text)
    
    # Тест 2: Azure TTS
    print("\n2️⃣ ТЕСТИРОВАНИЕ AZURE TTS") 
    print("-" * 30)
    success_azure = await test_azure_tts_direct(text)
    
    # Тест 3: macOS say
    print("\n3️⃣ ТЕСТИРОВАНИЕ MACOS SAY")
    print("-" * 30)
    success_macos = await test_macos_say_direct(text)
    
    # Итоги
    print(f"\n📊 РЕЗУЛЬТАТЫ для '{text[:30]}...':")
    print(f"   Edge TTS: {'✅' if success_edge else '❌'}")
    print(f"   Azure TTS: {'✅' if success_azure else '❌'}")
    print(f"   macOS say: {'✅' if success_macos else '❌'}")
    
    return any([success_edge, success_azure, success_macos])

async def test_edge_tts_direct(text: str) -> bool:
    """Прямой тест Edge TTS"""
    try:
        import edge_tts
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        import io
        
        print("✅ Edge TTS библиотека доступна")
        
        # Генерируем аудио
        communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
        audio_bytes = b""
        
        print("🔄 Генерация аудио...")
        
        timeout_seconds = 10
        try:
            async with asyncio.timeout(timeout_seconds):
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
        except asyncio.TimeoutError:
            print(f"⏰ Таймаут {timeout_seconds}s")
            return False
        
        if not audio_bytes:
            print("❌ Пустые аудио данные")
            return False
        
        print(f"✅ Получено: {len(audio_bytes)} байт")
        
        # Конвертируем в numpy
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
        if seg.frame_rate != 48000:
            seg = seg.set_frame_rate(48000)
        if seg.channels != 1:
            seg = seg.set_channels(1)
        
        samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
        print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
        
        # Воспроизводим
        print("🔊 Воспроизведение...")
        play_data = samples.astype(np.float32) / 32767.0
        sd.play(play_data, samplerate=48000)
        
        # Ждем завершения
        duration = len(samples) / 48000
        await asyncio.sleep(duration + 0.5)
        
        print("✅ Edge TTS работает!")
        return True
        
    except ImportError as e:
        print(f"❌ Импорт ошибка: {e}")
        print("💡 Установите: pip install edge-tts")
        return False
    except Exception as e:
        print(f"❌ Edge TTS ошибка: {e}")
        return False

async def test_azure_tts_direct(text: str) -> bool:
    """Прямой тест Azure TTS"""
    try:
        import azure.cognitiveservices.speech as speechsdk
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        import io
        
        # Загружаем конфигурацию
        try:
            from config import Config
            if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
                print("❌ Azure ключи не настроены в config.env")
                return False
        except Exception:
            print("❌ Не удалось загрузить конфигурацию")
            return False
        
        print(f"✅ Azure SDK доступен")
        print(f"🔑 Ключ: {Config.SPEECH_KEY[:10]}...")
        print(f"📍 Регион: {Config.SPEECH_REGION}")
        
        # Настраиваем Azure
        speech_config = speechsdk.SpeechConfig(
            subscription=Config.SPEECH_KEY,
            region=Config.SPEECH_REGION
        )
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        speech_config.set_speech_synthesis_output_format(
            speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
        )
        
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
        
        print("🔄 Генерация аудио...")
        result = synthesizer.speak_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            print(f"✅ Получено: {len(audio_data)} байт")
            
            # Конвертируем в numpy
            audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
            samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
            
            print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
            
            # Воспроизводим
            print("🔊 Воспроизведение...")
            play_data = samples.astype(np.float32) / 32767.0
            sd.play(play_data, samplerate=48000)
            
            duration = len(samples) / 48000
            await asyncio.sleep(duration + 0.5)
            
            print("✅ Azure TTS работает!")
            return True
        else:
            print(f"❌ Azure TTS ошибка: {result.reason}")
            if result.error_details:
                print(f"   Детали: {result.error_details}")
            return False
            
    except ImportError as e:
        print(f"❌ Импорт ошибка: {e}")
        print("💡 Установите: pip install azure-cognitiveservices-speech")
        return False
    except Exception as e:
        print(f"❌ Azure TTS ошибка: {e}")
        return False

async def test_macos_say_direct(text: str) -> bool:
    """Прямой тест macOS say command"""
    try:
        import subprocess
        import tempfile
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        
        print("✅ macOS say доступен")
        
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
            temp_path = temp_file.name
        
        try:
            print("🔄 Генерация через macOS say...")
            
            cmd = [
                'say',
                '-v', 'Samantha',
                '-r', '180',  # Скорость
                '-o', temp_path,
                text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                # Конвертируем
                seg = AudioSegment.from_file(temp_path)
                seg = seg.set_frame_rate(48000).set_channels(1)
                
                samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                print(f"✅ Получено: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
                
                # Воспроизводим
                print("🔊 Воспроизведение...")
                play_data = samples.astype(np.float32) / 32767.0
                sd.play(play_data, samplerate=48000)
                
                duration = len(samples) / 48000
                await asyncio.sleep(duration + 0.5)
                
                print("✅ macOS say работает!")
                return True
            else:
                print(f"❌ macOS say ошибка: {result.stderr}")
                return False
                
        finally:
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        print("⏰ macOS say таймаут")
        return False
    except Exception as e:
        print(f"❌ macOS say ошибка: {e}")
        return False

async def main():
    """Главная функция"""
    print("🧪 ПРОСТОЙ ТЕСТ АУДИО ГЕНЕРАЦИИ")
    print("=" * 60)
    
    # Получаем текст для тестирования
    default_text = "Hello, this is a test of text to speech generation."
    text = input(f"Введите текст для тестирования (или Enter для '{default_text}'): ").strip()
    
    if not text:
        text = default_text
    
    print(f"\n🎯 Тестируем: '{text}'")
    
    # Запускаем тест
    success = await test_sentence(text)
    
    if success:
        print(f"\n🎉 Хотя бы один метод работает!")
        print(f"💡 Рекомендуется настроить рабочий метод в config.env")
    else:
        print(f"\n❌ Ни один метод не работает!")
        print(f"🔧 Требуется настройка TTS сервисов")
        
    print(f"\n📚 Для настройки запустите: python configure_tts.py")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        import traceback
        traceback.print_exc()
