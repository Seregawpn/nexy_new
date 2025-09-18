#!/usr/bin/env python3
"""
Автоматический тест аудио генерации - без интерактивного ввода
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к серверу
server_path = Path(__file__).parent / "server"
sys.path.insert(0, str(server_path))

async def test_edge_tts_auto():
    """Автоматический тест Edge TTS"""
    print("🗣️ ТЕСТ EDGE TTS")
    print("=" * 30)
    
    test_text = "Hello, this is a test of Edge text to speech."
    
    try:
        import edge_tts
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        import io
        
        print("✅ Edge TTS библиотека доступна")
        print(f"🗣️ Генерирую: '{test_text}'")
        
        # Генерируем аудио
        communicate = edge_tts.Communicate(test_text, "en-US-JennyNeural")
        audio_bytes = b""
        
        print("🔄 Генерация...")
        
        timeout_seconds = 10
        try:
            async with asyncio.timeout(timeout_seconds):
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
        except asyncio.TimeoutError:
            print(f"⏰ Таймаут {timeout_seconds}s")
            return False
        except Exception as e:
            print(f"❌ WebSocket ошибка: {e}")
            return False
        
        if not audio_bytes:
            print("❌ Пустые аудио данные")
            return False
        
        print(f"✅ Получено: {len(audio_bytes)} байт")
        
        # Конвертируем в numpy
        try:
            seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
            print(f"📊 Исходный формат: {seg.frame_rate}Hz, {seg.channels}ch, {len(seg)}ms")
            
            # Приводим к стандартному формату
            if seg.frame_rate != 48000:
                seg = seg.set_frame_rate(48000)
            if seg.channels != 1:
                seg = seg.set_channels(1)
            
            samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
            print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
            
            # Проверяем качество данных
            max_val = np.max(np.abs(samples))
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            print(f"📈 Качество: max={max_val}, rms={rms:.1f}")
            
            # Воспроизводим
            print("🔊 Воспроизведение через sounddevice...")
            play_data = samples.astype(np.float32) / 32767.0
            sd.play(play_data, samplerate=48000)
            
            # Ждем завершения
            duration = len(samples) / 48000
            await asyncio.sleep(duration + 1.0)
            
            print("✅ Edge TTS работает отлично!")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка конвертации: {e}")
            return False
        
    except ImportError as e:
        print(f"❌ Edge TTS не установлен: {e}")
        return False
    except Exception as e:
        print(f"❌ Общая ошибка Edge TTS: {e}")
        return False

async def test_azure_tts_auto():
    """Автоматический тест Azure TTS"""
    print("\n🇺🇸 ТЕСТ AZURE TTS")
    print("=" * 30)
    
    test_text = "Hello, this is a test of Azure text to speech."
    
    try:
        import azure.cognitiveservices.speech as speechsdk
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        import io
        
        print("✅ Azure SDK доступен")
        
        # Загружаем конфигурацию
        try:
            from config import Config
            if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
                print("❌ Azure ключи не настроены в server/config.env")
                print("💡 Раскомментируйте строки:")
                print("   SPEECH_KEY=ваш_ключ")
                print("   SPEECH_REGION=ваш_регион")
                return False
                
            print(f"🔑 Ключ: {Config.SPEECH_KEY[:10]}...")
            print(f"📍 Регион: {Config.SPEECH_REGION}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            return False
        
        print(f"🗣️ Генерирую: '{test_text}'")
        
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
        
        print("🔄 Генерация через Azure...")
        result = synthesizer.speak_text_async(test_text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            print(f"✅ Получено: {len(audio_data)} байт")
            
            # Конвертируем в numpy
            audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
            samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
            
            print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
            
            # Проверяем качество
            max_val = np.max(np.abs(samples))
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            print(f"📈 Качество: max={max_val}, rms={rms:.1f}")
            
            # Воспроизводим
            print("🔊 Воспроизведение через sounddevice...")
            play_data = samples.astype(np.float32) / 32767.0
            sd.play(play_data, samplerate=48000)
            
            duration = len(samples) / 48000
            await asyncio.sleep(duration + 1.0)
            
            print("✅ Azure TTS работает отлично!")
            return True
        else:
            print(f"❌ Azure TTS ошибка: {result.reason}")
            if result.error_details:
                print(f"   Детали: {result.error_details}")
            return False
            
    except ImportError as e:
        print(f"❌ Azure SDK не установлен: {e}")
        print("💡 Установите: pip install azure-cognitiveservices-speech")
        return False
    except Exception as e:
        print(f"❌ Azure TTS ошибка: {e}")
        return False

async def test_macos_say_auto():
    """Автоматический тест macOS say"""
    print("\n🍎 ТЕСТ MACOS SAY")
    print("=" * 30)
    
    test_text = "Hello, this is a test of macOS text to speech."
    
    try:
        import subprocess
        import tempfile
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        
        print("✅ macOS say доступен")
        print(f"🗣️ Генерирую: '{test_text}'")
        
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
                test_text
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and os.path.exists(temp_path):
                print(f"✅ macOS say успешно")
                
                # Конвертируем
                seg = AudioSegment.from_file(temp_path)
                print(f"📊 Исходный формат: {seg.frame_rate}Hz, {seg.channels}ch, {len(seg)}ms")
                
                seg = seg.set_frame_rate(48000).set_channels(1)
                samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                
                print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
                
                # Проверяем качество
                max_val = np.max(np.abs(samples))
                rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
                print(f"📈 Качество: max={max_val}, rms={rms:.1f}")
                
                # Воспроизводим
                print("🔊 Воспроизведение...")
                play_data = samples.astype(np.float32) / 32767.0
                sd.play(play_data, samplerate=48000)
                
                duration = len(samples) / 48000
                await asyncio.sleep(duration + 1.0)
                
                print("✅ macOS say работает отлично!")
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

async def test_current_fallback():
    """Тест текущего проблемного fallback"""
    print("\n🎛️ ТЕСТ ТЕКУЩЕГО FALLBACK (ПРОБЛЕМНЫЙ)")
    print("=" * 30)
    
    test_text = "This should be speech but will be a tone."
    
    try:
        import sounddevice as sd
        import numpy as np
        
        print(f"🗣️ Генерирую sine-wave для: '{test_text}'")
        
        # Текущий проблемный метод
        sr = 48000
        duration_sec = min(3.5, max(0.6, 0.05 * len(test_text.strip())))
        t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False, dtype=np.float32)
        freq = 440.0
        envelope = np.minimum(1.0, np.linspace(0, 1.0, int(0.1 * sr)))
        envelope = np.pad(envelope, (0, len(t) - len(envelope)), constant_values=(0, 1.0))
        wave = 0.2 * np.sin(2 * np.pi * freq * t) * envelope
        audio = np.asarray(wave * 32767, dtype=np.int16)
        
        print(f"🎵 Sine-wave: {len(audio)} сэмплов, {duration_sec:.1f}s")
        print("⚠️ ВНИМАНИЕ: Это НЕ речь, а музыкальный тон 440Hz!")
        print("⚠️ Именно это слышат пользователи когда TTS не работает!")
        
        # Воспроизводим для демонстрации проблемы
        print("🔊 Воспроизведение проблемного fallback...")
        play_data = audio.astype(np.float32) / 32767.0
        sd.play(play_data, samplerate=48000)
        
        await asyncio.sleep(duration_sec + 1.0)
        
        print("❌ Вот почему в наушниках шум вместо речи!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка fallback теста: {e}")
        return False

async def main():
    """Автоматическое тестирование всех методов"""
    print("🧪 АВТОМАТИЧЕСКИЙ ТЕСТ ВСЕХ TTS МЕТОДОВ")
    print("=" * 60)
    print("Тестируем фразу: 'Hello, this is a test of text to speech.'")
    print("=" * 60)
    
    results = {}
    
    # Тест 1: Edge TTS
    try:
        success = await test_edge_tts_auto()
        results['Edge TTS'] = success
    except Exception as e:
        print(f"❌ Edge TTS критическая ошибка: {e}")
        results['Edge TTS'] = False
    
    # Тест 2: Azure TTS
    try:
        success = await test_azure_tts_auto()
        results['Azure TTS'] = success
    except Exception as e:
        print(f"❌ Azure TTS критическая ошибка: {e}")
        results['Azure TTS'] = False
    
    # Тест 3: macOS say
    try:
        success = await test_macos_say_auto()
        results['macOS say'] = success
    except Exception as e:
        print(f"❌ macOS say критическая ошибка: {e}")
        results['macOS say'] = False
    
    # Тест 4: Проблемный fallback
    try:
        await test_current_fallback()
        results['Sine Fallback'] = True
    except Exception as e:
        print(f"❌ Fallback ошибка: {e}")
        results['Sine Fallback'] = False
    
    # Итоговый отчет
    print(f"\n📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")
    print("=" * 40)
    
    working_methods = []
    for method, success in results.items():
        status = "✅ РАБОТАЕТ" if success else "❌ НЕ РАБОТАЕТ"
        print(f"🎤 {method:<15} {status}")
        if success and method != 'Sine Fallback':
            working_methods.append(method)
    
    print(f"\n💡 РЕКОМЕНДАЦИИ:")
    if working_methods:
        print(f"✅ Работающие TTS: {', '.join(working_methods)}")
        print(f"🎯 Используйте: {working_methods[0]}")
        
        # Показываем как настроить
        if 'Azure TTS' in working_methods:
            print(f"\n🔧 Для использования Azure TTS:")
            print(f"   1. Раскомментируйте SPEECH_KEY и SPEECH_REGION в server/config.env")
            print(f"   2. Перезапустите сервер")
        elif 'Edge TTS' in working_methods:
            print(f"\n🔧 Для использования Edge TTS:")
            print(f"   1. Установите: USE_EDGE_TTS=true в server/config.env")
            print(f"   2. Перезапустите сервер")
        elif 'macOS say' in working_methods:
            print(f"\n🔧 Для использования macOS say:")
            print(f"   1. Нужно интегрировать в audio_generator.py")
            print(f"   2. Добавить как новый метод генерации")
    else:
        print(f"❌ Ни один TTS метод не работает!")
        print(f"🔧 Требуется настройка API ключей")
    
    if results.get('Sine Fallback'):
        print(f"\n⚠️ ПРОБЛЕМА С ШУМОМ:")
        print(f"   Sine-wave fallback создает музыкальный тон вместо речи")
        print(f"   Именно поэтому в наушниках слышен шум!")

async def test_edge_tts_auto():
    """Автоматический тест Edge TTS"""
    print("🗣️ ТЕСТ EDGE TTS")
    print("=" * 30)
    
    test_text = "Hello, this is a test of Edge text to speech."
    
    try:
        import edge_tts
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        import io
        
        print("✅ Edge TTS библиотека доступна")
        print(f"🗣️ Генерирую: '{test_text}'")
        
        # Генерируем аудио
        communicate = edge_tts.Communicate(test_text, "en-US-JennyNeural")
        audio_bytes = b""
        
        print("🔄 Генерация...")
        
        timeout_seconds = 10
        try:
            async with asyncio.timeout(timeout_seconds):
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
        except asyncio.TimeoutError:
            print(f"⏰ Таймаут {timeout_seconds}s")
            return False
        except Exception as e:
            print(f"❌ WebSocket ошибка: {e}")
            return False
        
        if not audio_bytes:
            print("❌ Пустые аудио данные")
            return False
        
        print(f"✅ Получено: {len(audio_bytes)} байт")
        
        # Конвертируем в numpy
        try:
            seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
            print(f"📊 Исходный формат: {seg.frame_rate}Hz, {seg.channels}ch, {len(seg)}ms")
            
            # Приводим к стандартному формату
            if seg.frame_rate != 48000:
                seg = seg.set_frame_rate(48000)
            if seg.channels != 1:
                seg = seg.set_channels(1)
            
            samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
            print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
            
            # Проверяем качество данных
            max_val = np.max(np.abs(samples))
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            print(f"📈 Качество: max={max_val}, rms={rms:.1f}")
            
            # Воспроизводим
            print("🔊 Воспроизведение через sounddevice...")
            play_data = samples.astype(np.float32) / 32767.0
            sd.play(play_data, samplerate=48000)
            
            # Ждем завершения
            duration = len(samples) / 48000
            await asyncio.sleep(duration + 1.0)
            
            print("✅ Edge TTS работает отлично!")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка конвертации: {e}")
            return False
        
    except ImportError as e:
        print(f"❌ Edge TTS не установлен: {e}")
        return False
    except Exception as e:
        print(f"❌ Общая ошибка Edge TTS: {e}")
        return False

async def test_azure_tts_auto():
    """Автоматический тест Azure TTS"""
    print("\n🇺🇸 ТЕСТ AZURE TTS")
    print("=" * 30)
    
    test_text = "Hello, this is a test of Azure text to speech."
    
    try:
        import azure.cognitiveservices.speech as speechsdk
        from pydub import AudioSegment
        import sounddevice as sd
        import numpy as np
        import io
        
        print("✅ Azure SDK доступен")
        
        # Загружаем конфигурацию
        try:
            from config import Config
            if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
                print("❌ Azure ключи не настроены в server/config.env")
                print("💡 Раскомментируйте строки:")
                print("   SPEECH_KEY=ваш_ключ")
                print("   SPEECH_REGION=ваш_регион")
                return False
                
            print(f"🔑 Ключ: {Config.SPEECH_KEY[:10]}...")
            print(f"📍 Регион: {Config.SPEECH_REGION}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки конфигурации: {e}")
            return False
        
        print(f"🗣️ Генерирую: '{test_text}'")
        
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
        
        print("🔄 Генерация через Azure...")
        result = synthesizer.speak_text_async(test_text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio_data = result.audio_data
            print(f"✅ Получено: {len(audio_data)} байт")
            
            # Конвертируем в numpy
            audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
            samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
            
            print(f"🎵 Конвертировано: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
            
            # Проверяем качество
            max_val = np.max(np.abs(samples))
            rms = np.sqrt(np.mean(samples.astype(np.float32) ** 2))
            print(f"📈 Качество: max={max_val}, rms={rms:.1f}")
            
            # Воспроизводим
            print("🔊 Воспроизведение через sounddevice...")
            play_data = samples.astype(np.float32) / 32767.0
            sd.play(play_data, samplerate=48000)
            
            duration = len(samples) / 48000
            await asyncio.sleep(duration + 1.0)
            
            print("✅ Azure TTS работает отлично!")
            return True
        else:
            print(f"❌ Azure TTS ошибка: {result.reason}")
            if result.error_details:
                print(f"   Детали: {result.error_details}")
            return False
            
    except ImportError as e:
        print(f"❌ Azure SDK не установлен: {e}")
        print("💡 Установите: pip install azure-cognitiveservices-speech")
        return False
    except Exception as e:
        print(f"❌ Azure TTS ошибка: {e}")
        return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
