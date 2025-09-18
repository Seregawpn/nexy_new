#!/usr/bin/env python3
"""
Тестовый модуль для проверки всех методов TTS генерации
Позволяет протестировать Azure TTS, Edge TTS и fallback методы отдельно
"""

import asyncio
import logging
import sys
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any
import numpy as np

# Добавляем путь к серверным модулям
server_path = Path(__file__).parent / "server"
sys.path.insert(0, str(server_path))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TTSTestSuite:
    """Тестовый набор для всех TTS методов"""
    
    def __init__(self):
        self.test_phrases = [
            "Hello, this is a test of text to speech.",
            "How are you doing today?", 
            "The weather is nice outside.",
            "Testing audio quality and clarity.",
            "This is a longer sentence to test the quality of speech synthesis with multiple words and phrases."
        ]
        
        # Результаты тестов
        self.results = {}
        
    async def test_all_methods(self):
        """Тестирует все доступные методы TTS"""
        print("🚀 ЗАПУСК ПОЛНОГО ТЕСТИРОВАНИЯ TTS МЕТОДОВ")
        print("=" * 60)
        
        methods = [
            ("Azure TTS", self.test_azure_tts),
            ("Edge TTS", self.test_edge_tts),
            ("macOS Say", self.test_macos_say),
            ("Sine Fallback", self.test_sine_fallback)
        ]
        
        for method_name, test_func in methods:
            print(f"\n🧪 ТЕСТИРОВАНИЕ: {method_name}")
            print("-" * 40)
            
            try:
                success = await test_func()
                self.results[method_name] = {
                    'success': success,
                    'status': '✅ РАБОТАЕТ' if success else '❌ НЕ РАБОТАЕТ'
                }
            except Exception as e:
                logger.error(f"❌ Ошибка тестирования {method_name}: {e}")
                self.results[method_name] = {
                    'success': False,
                    'status': f'❌ ОШИБКА: {e}',
                    'error': str(e)
                }
        
        # Выводим итоговый отчет
        self._print_final_report()
    
    async def test_azure_tts(self) -> bool:
        """Тест Azure Speech Services"""
        try:
            # Проверяем доступность Azure SDK
            try:
                import azure.cognitiveservices.speech as speechsdk
                from config import Config
                
                if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
                    print("⚠️ Azure ключи не настроены в config.env")
                    return False
                    
                print(f"✅ Azure SDK доступен")
                print(f"📍 Регион: {Config.SPEECH_REGION}")
                print(f"🔑 Ключ: {Config.SPEECH_KEY[:10]}...")
                
            except ImportError:
                print("❌ Azure SDK не установлен")
                return False
            
            # Тестируем генерацию
            speech_config = speechsdk.SpeechConfig(
                subscription=Config.SPEECH_KEY,
                region=Config.SPEECH_REGION
            )
            speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
            )
            
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
            
            test_text = self.test_phrases[0]
            print(f"🗣️ Генерирую: '{test_text}'")
            
            result = synthesizer.speak_text_async(test_text).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                print(f"✅ Azure TTS успешно: {len(audio_data)} байт")
                
                # Конвертируем в numpy для тестирования
                audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
                samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                
                print(f"🎵 Аудио: {len(samples)} сэмплов, {audio_segment.frame_rate}Hz, {audio_segment.channels}ch")
                
                # Воспроизводим для тестирования
                await self._play_audio_samples(samples, "Azure TTS")
                return True
                
            else:
                print(f"❌ Azure TTS ошибка: {result.reason}")
                if result.error_details:
                    print(f"   Детали: {result.error_details}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка Azure TTS: {e}")
            return False
    
    async def test_edge_tts(self) -> bool:
        """Тест Edge TTS"""
        try:
            import edge_tts
            from pydub import AudioSegment
            import io
            
            print(f"✅ Edge TTS доступен")
            
            test_text = self.test_phrases[0]
            print(f"🗣️ Генерирую: '{test_text}'")
            
            # Тестируем разные голоса
            voices_to_test = [
                "en-US-JennyNeural",
                "en-US-AriaNeural", 
                "en-US-GuyNeural"
            ]
            
            for voice in voices_to_test:
                print(f"🎤 Тестирую голос: {voice}")
                
                try:
                    communicate = edge_tts.Communicate(test_text, voice)
                    audio_bytes = b""
                    
                    # Собираем аудио данные с таймаутом
                    timeout_seconds = 10
                    
                    async with asyncio.timeout(timeout_seconds):
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                audio_bytes += chunk["data"]
                    
                    if audio_bytes:
                        print(f"✅ Edge TTS ({voice}): {len(audio_bytes)} байт")
                        
                        # Конвертируем в numpy
                        try:
                            seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
                            if seg.frame_rate != 48000:
                                seg = seg.set_frame_rate(48000)
                            if seg.channels != 1:
                                seg = seg.set_channels(1)
                            
                            samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                            print(f"🎵 Аудио: {len(samples)} сэмплов, {seg.frame_rate}Hz, {seg.channels}ch")
                            
                            # Воспроизводим для тестирования
                            await self._play_audio_samples(samples, f"Edge TTS ({voice})")
                            return True
                            
                        except Exception as e:
                            print(f"❌ Ошибка конвертации Edge TTS: {e}")
                            continue
                    else:
                        print(f"❌ Edge TTS ({voice}): пустые данные")
                        
                except asyncio.TimeoutError:
                    print(f"⏰ Edge TTS ({voice}): таймаут {timeout_seconds}s")
                    continue
                except Exception as e:
                    print(f"❌ Edge TTS ({voice}) ошибка: {e}")
                    continue
            
            return False
            
        except ImportError:
            print("❌ Edge TTS не установлен")
            return False
        except Exception as e:
            print(f"❌ Ошибка Edge TTS: {e}")
            return False
    
    async def test_macos_say(self) -> bool:
        """Тест встроенного macOS say command"""
        try:
            import subprocess
            
            test_text = self.test_phrases[0]
            print(f"🗣️ Генерирую через macOS say: '{test_text}'")
            
            # Создаем временный файл
            with tempfile.NamedTemporaryFile(suffix='.aiff', delete=False) as temp_file:
                temp_path = temp_file.name
            
            try:
                # Генерируем аудио через say
                cmd = [
                    'say', 
                    '-v', 'Samantha',  # Голос
                    '-r', '200',       # Скорость (слов в минуту)
                    '-o', temp_path,   # Выходной файл
                    test_text
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0 and os.path.exists(temp_path):
                    # Конвертируем в нужный формат
                    from pydub import AudioSegment
                    
                    seg = AudioSegment.from_file(temp_path)
                    print(f"✅ macOS say: {len(seg)}ms, {seg.frame_rate}Hz, {seg.channels}ch")
                    
                    # Приводим к стандартному формату
                    if seg.frame_rate != 48000:
                        seg = seg.set_frame_rate(48000)
                    if seg.channels != 1:
                        seg = seg.set_channels(1)
                    
                    samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                    print(f"🎵 Конвертировано: {len(samples)} сэмплов")
                    
                    # Воспроизводим для тестирования
                    await self._play_audio_samples(samples, "macOS say")
                    
                    return True
                else:
                    print(f"❌ macOS say ошибка: {result.stderr}")
                    return False
                    
            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_path)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            print("⏰ macOS say: таймаут")
            return False
        except Exception as e:
            print(f"❌ Ошибка macOS say: {e}")
            return False
    
    async def test_sine_fallback(self) -> bool:
        """Тест текущего sine-wave fallback"""
        try:
            test_text = self.test_phrases[0]
            print(f"🎛️ Генерирую sine-wave для: '{test_text}'")
            
            # Текущий метод (проблемный)
            sr = 48000
            duration_sec = min(3.5, max(0.6, 0.05 * len(test_text.strip())))
            t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False, dtype=np.float32)
            freq = 440.0
            envelope = np.minimum(1.0, np.linspace(0, 1.0, int(0.1 * sr)))
            envelope = np.pad(envelope, (0, len(t) - len(envelope)), constant_values=(0, 1.0))
            wave = 0.2 * np.sin(2 * np.pi * freq * t) * envelope
            audio = np.asarray(wave * 32767, dtype=np.int16)
            
            print(f"🎵 Sine-wave: {len(audio)} сэмплов, {duration_sec:.1f}s")
            print("⚠️ ВНИМАНИЕ: Это НЕ речь, а музыкальный тон!")
            
            # Воспроизводим для демонстрации проблемы
            await self._play_audio_samples(audio, "Sine Fallback (ПРОБЛЕМНЫЙ)")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка sine fallback: {e}")
            return False
    
    async def _play_audio_samples(self, samples: np.ndarray, method_name: str):
        """Воспроизводит аудио сэмплы для тестирования"""
        try:
            import sounddevice as sd
            
            print(f"🔊 Воспроизведение {method_name}...")
            print(f"   Длительность: {len(samples) / 48000:.1f}s")
            print(f"   Сэмплов: {len(samples)}")
            print(f"   Формат: {samples.dtype}")
            
            # Нормализуем для безопасности
            if samples.dtype == np.int16:
                play_data = samples.astype(np.float32) / 32767.0
            else:
                play_data = samples
            
            # Воспроизводим
            sd.play(play_data, samplerate=48000, channels=1)
            
            # Ждем завершения воспроизведения
            duration = len(samples) / 48000
            await asyncio.sleep(duration + 0.5)
            
            # Спрашиваем у пользователя
            print(f"❓ Качество {method_name}: [1-5] или Enter для пропуска")
            
        except Exception as e:
            print(f"❌ Ошибка воспроизведения {method_name}: {e}")
    
    def _print_final_report(self):
        """Выводит итоговый отчет тестирования"""
        print("\n" + "=" * 60)
        print("📊 ИТОГОВЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ TTS")
        print("=" * 60)
        
        for method, result in self.results.items():
            status = result['status']
            print(f"🎤 {method:<20} {status}")
            if 'error' in result:
                print(f"   Ошибка: {result['error']}")
        
        # Рекомендации
        print(f"\n💡 РЕКОМЕНДАЦИИ:")
        working_methods = [name for name, result in self.results.items() if result['success']]
        
        if working_methods:
            print(f"✅ Работающие методы: {', '.join(working_methods)}")
            print(f"🎯 Рекомендуется использовать: {working_methods[0]}")
        else:
            print(f"❌ Ни один метод не работает!")
            print(f"🔧 Требуется настройка API ключей или установка зависимостей")

class AzureTTSTester:
    """Специальный тестер для Azure TTS"""
    
    def __init__(self):
        self.voices = [
            "en-US-JennyNeural",
            "en-US-AriaNeural", 
            "en-US-GuyNeural",
            "en-US-DavisNeural",
            "en-US-AmberNeural"
        ]
    
    async def test_azure_comprehensive(self):
        """Комплексное тестирование Azure TTS"""
        print("🇺🇸 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ AZURE TTS")
        print("=" * 50)
        
        try:
            import azure.cognitiveservices.speech as speechsdk
            from config import Config
            
            if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
                print("❌ Azure ключи не настроены!")
                print("💡 Добавьте в server/config.env:")
                print("   SPEECH_KEY=ваш_ключ")
                print("   SPEECH_REGION=ваш_регион")
                return False
            
            print(f"🔑 Ключ: {Config.SPEECH_KEY[:10]}...")
            print(f"📍 Регион: {Config.SPEECH_REGION}")
            
            # Тестируем каждый голос
            for voice in self.voices:
                print(f"\n🎤 Тестирую голос: {voice}")
                
                try:
                    speech_config = speechsdk.SpeechConfig(
                        subscription=Config.SPEECH_KEY,
                        region=Config.SPEECH_REGION
                    )
                    speech_config.speech_synthesis_voice_name = voice
                    speech_config.set_speech_synthesis_output_format(
                        speechsdk.SpeechSynthesisOutputFormat.Riff48Khz16BitMonoPcm
                    )
                    
                    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)
                    
                    test_text = "Hello, this is a test of Azure text to speech."
                    result = synthesizer.speak_text_async(test_text).get()
                    
                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        audio_data = result.audio_data
                        print(f"   ✅ Успешно: {len(audio_data)} байт")
                        
                        # Конвертируем и воспроизводим
                        from pydub import AudioSegment
                        audio_segment = AudioSegment.from_wav(io.BytesIO(audio_data))
                        samples = np.array(audio_segment.get_array_of_samples()).astype(np.int16)
                        
                        import sounddevice as sd
                        play_data = samples.astype(np.float32) / 32767.0
                        sd.play(play_data, samplerate=48000)
                        await asyncio.sleep(len(samples) / 48000 + 0.5)
                        
                        print(f"   🎵 Воспроизведено: {len(samples)} сэмплов")
                        
                    else:
                        print(f"   ❌ Ошибка: {result.reason}")
                        if result.error_details:
                            print(f"   Детали: {result.error_details}")
                        
                except Exception as e:
                    print(f"   ❌ Ошибка голоса {voice}: {e}")
                    continue
            
            return True
            
        except ImportError as e:
            print(f"❌ Импорт ошибка: {e}")
            return False
        except Exception as e:
            print(f"❌ Общая ошибка Azure: {e}")
            return False

class EdgeTTSTester:
    """Специальный тестер для Edge TTS"""
    
    async def test_edge_comprehensive(self):
        """Комплексное тестирование Edge TTS"""
        print("🗣️ КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ EDGE TTS")
        print("=" * 50)
        
        try:
            import edge_tts
            
            print("✅ Edge TTS импортирован")
            
            # Получаем список доступных голосов
            try:
                voices = await edge_tts.list_voices()
                en_voices = [v for v in voices if v['Locale'].startswith('en-US')][:5]
                print(f"🎤 Найдено {len(en_voices)} английских голосов")
                
                for voice in en_voices:
                    name = voice['ShortName']
                    gender = voice['Gender']
                    print(f"   {name} ({gender})")
                    
            except Exception as e:
                print(f"⚠️ Не удалось получить список голосов: {e}")
                en_voices = [{'ShortName': 'en-US-JennyNeural'}]
            
            # Тестируем генерацию
            test_text = "Hello, this is a comprehensive test of Edge text to speech."
            
            for voice_info in en_voices[:3]:  # Тестируем первые 3 голоса
                voice_name = voice_info['ShortName']
                print(f"\n🎤 Тестирую: {voice_name}")
                
                try:
                    communicate = edge_tts.Communicate(test_text, voice_name)
                    audio_bytes = b""
                    
                    timeout_seconds = 15
                    start_time = time.time()
                    
                    async with asyncio.timeout(timeout_seconds):
                        async for chunk in communicate.stream():
                            if chunk["type"] == "audio":
                                audio_bytes += chunk["data"]
                    
                    generation_time = time.time() - start_time
                    
                    if audio_bytes:
                        print(f"   ✅ Успешно: {len(audio_bytes)} байт за {generation_time:.1f}s")
                        
                        # Конвертируем и тестируем
                        from pydub import AudioSegment
                        import io
                        
                        seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
                        if seg.frame_rate != 48000:
                            seg = seg.set_frame_rate(48000)
                        if seg.channels != 1:
                            seg = seg.set_channels(1)
                        
                        samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
                        print(f"   🎵 Аудио: {len(samples)} сэмплов, {len(samples)/48000:.1f}s")
                        
                        # Воспроизводим
                        import sounddevice as sd
                        play_data = samples.astype(np.float32) / 32767.0
                        sd.play(play_data, samplerate=48000)
                        await asyncio.sleep(len(samples) / 48000 + 0.5)
                        
                        print(f"   🔊 Воспроизведено")
                        return True
                        
                    else:
                        print(f"   ❌ Пустые аудио данные")
                        
                except asyncio.TimeoutError:
                    print(f"   ⏰ Таймаут {timeout_seconds}s")
                except Exception as e:
                    print(f"   ❌ Ошибка: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ Общая ошибка Edge TTS: {e}")
            return False

async def main():
    """Главная функция тестирования"""
    print("🚀 TTS ТЕСТОВЫЙ МОДУЛЬ")
    print("=" * 60)
    print("Этот модуль тестирует все доступные методы генерации речи")
    print("и поможет выбрать лучший вариант для вашей системы.")
    print("=" * 60)
    
    # Меню выбора
    print("\nВыберите тип тестирования:")
    print("1. Полное тестирование всех методов")
    print("2. Только Azure TTS")
    print("3. Только Edge TTS") 
    print("4. Быстрый тест")
    print("5. Выход")
    
    choice = input("\nВаш выбор (1-5): ").strip()
    
    if choice == "1":
        tester = TTSTestSuite()
        await tester.test_all_methods()
    elif choice == "2":
        tester = AzureTTSTester()
        await tester.test_azure_comprehensive()
    elif choice == "3":
        tester = EdgeTTSTester()
        await tester.test_edge_comprehensive()
    elif choice == "4":
        await quick_test()
    elif choice == "5":
        print("👋 До свидания!")
        return
    else:
        print("❌ Неверный выбор")
        return

async def quick_test():
    """Быстрый тест одного предложения"""
    print("\n⚡ БЫСТРЫЙ ТЕСТ")
    print("-" * 30)
    
    text = input("Введите текст для генерации: ").strip()
    if not text:
        text = "Hello, this is a quick test."
    
    print(f"🗣️ Тестирую: '{text}'")
    
    # Пробуем Edge TTS
    try:
        import edge_tts
        from pydub import AudioSegment
        import sounddevice as sd
        import io
        
        communicate = edge_tts.Communicate(text, "en-US-JennyNeural")
        audio_bytes = b""
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_bytes += chunk["data"]
        
        if audio_bytes:
            seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
            seg = seg.set_frame_rate(48000).set_channels(1)
            samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
            
            print(f"✅ Генерировано: {len(samples)} сэмплов")
            print("🔊 Воспроизведение...")
            
            play_data = samples.astype(np.float32) / 32767.0
            sd.play(play_data, samplerate=48000)
            await asyncio.sleep(len(samples) / 48000 + 0.5)
            
            print("✅ Воспроизведение завершено")
        else:
            print("❌ Не удалось сгенерировать аудио")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
