#!/usr/bin/env python3
"""
Чистый тест Edge TTS без зависимостей от проекта
Проверяем работает ли Edge TTS сам по себе
"""

import asyncio
import os

async def test_pure_edge_tts():
    """Чистый тест Edge TTS"""
    print("🗣️ ЧИСТЫЙ ТЕСТ EDGE TTS")
    print("=" * 40)
    print("Тестируем Edge TTS без использования проектного кода")
    print()
    
    try:
        import edge_tts
        print("✅ Edge TTS импортирован")
        
        # Очищаем переменные окружения связанные с Azure
        azure_vars = ['SPEECH_KEY', 'SPEECH_REGION', 'AZURE_SPEECH_KEY', 'AZURE_SPEECH_REGION']
        for var in azure_vars:
            if var in os.environ:
                print(f"🧹 Удаляю переменную окружения: {var}")
                del os.environ[var]
        
        text = "Hello, this is a clean test of Edge text to speech without any Azure keys."
        voice = "en-US-JennyNeural"
        
        print(f"🗣️ Текст: '{text}'")
        print(f"🎤 Голос: {voice}")
        print("🔄 Генерация...")
        
        # Создаем communicate объект
        communicate = edge_tts.Communicate(text, voice)
        audio_bytes = b""
        
        # Собираем аудио данные
        timeout_seconds = 10
        try:
            async with asyncio.timeout(timeout_seconds):
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes += chunk["data"]
                    elif chunk["type"] == "WordBoundary":
                        # Можем логировать прогресс
                        pass
        except asyncio.TimeoutError:
            print(f"⏰ Таймаут {timeout_seconds}s")
            return False
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            print(f"❌ Тип ошибки: {type(e)}")
            return False
        
        if audio_bytes:
            print(f"✅ Получено аудио: {len(audio_bytes)} байт")
            
            # Сохраняем для проверки
            output_file = "test_edge_output.mp3"
            with open(output_file, 'wb') as f:
                f.write(audio_bytes)
            print(f"💾 Сохранено в: {output_file}")
            
            # Пробуем воспроизвести через system
            try:
                import subprocess
                print("🔊 Воспроизведение через afplay...")
                subprocess.run(['afplay', output_file], timeout=10)
                print("✅ Воспроизведение завершено")
            except Exception as e:
                print(f"⚠️ Не удалось воспроизвести: {e}")
            
            # Очищаем файл
            try:
                os.unlink(output_file)
            except:
                pass
            
            return True
        else:
            print("❌ Пустые аудио данные")
            return False
            
    except ImportError:
        print("❌ Edge TTS не установлен")
        print("💡 Установите: pip install edge-tts")
        return False
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_edge_voices():
    """Тест доступных голосов Edge TTS"""
    print("\n🎤 ТЕСТ ДОСТУПНЫХ ГОЛОСОВ")
    print("=" * 40)
    
    try:
        import edge_tts
        
        print("🔄 Получение списка голосов...")
        voices = await edge_tts.list_voices()
        
        # Фильтруем английские голоса
        en_voices = [v for v in voices if v['Locale'].startswith('en-US')][:10]
        
        print(f"✅ Найдено {len(en_voices)} английских голосов:")
        for i, voice in enumerate(en_voices, 1):
            name = voice['ShortName']
            gender = voice['Gender']
            print(f"   {i}. {name} ({gender})")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка получения голосов: {e}")
        return False

if __name__ == "__main__":
    try:
        # Запускаем тесты
        asyncio.run(test_pure_edge_tts())
        asyncio.run(test_edge_voices())
        
    except KeyboardInterrupt:
        print("\n⏹️ Тест прерван")
    except Exception as e:
        print(f"\n💥 Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
