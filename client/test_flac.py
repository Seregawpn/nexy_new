#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Тестовый скрипт для проверки работы FLAC
"""

import sys
import os
import subprocess
from pathlib import Path

def test_system_flac():
    """Тестирует системный FLAC"""
    print("🔍 Тестирую системный FLAC...")
    
    try:
        # Проверяем наличие FLAC в системе
        result = subprocess.run(['flac', '--version'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ Системный FLAC найден: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ FLAC вернул ошибку: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ FLAC не найден в системе")
        print("💡 Установите через: brew install flac")
        return False
    except subprocess.TimeoutExpired:
        print("❌ Таймаут при запуске FLAC")
        return False
    except Exception as e:
        print(f"❌ Ошибка при проверке FLAC: {e}")
        return False

def test_python_flac():
    """Тестирует Python библиотеки для работы с FLAC"""
    print("\n🐍 Тестирую Python FLAC библиотеки...")
    
    try:
        import pydub
        print(f"✅ pydub импортирован успешно")
        
        # Проверяем поддержку FLAC
        from pydub import AudioSegment
        
        # Создаем тестовый аудио сегмент
        test_audio = AudioSegment.silent(duration=1000)  # 1 секунда тишины
        
        # Пробуем экспорт в FLAC
        temp_flac = "test_output.flac"
        test_audio.export(temp_flac, format="flac")
        
        if os.path.exists(temp_flac):
            print("✅ FLAC экспорт работает")
            # Удаляем тестовый файл
            os.remove(temp_flac)
            return True
        else:
            print("❌ FLAC экспорт не работает")
            return False
            
    except ImportError as e:
        print(f"❌ Ошибка импорта pydub: {e}")
        print("💡 Установите через: pip install pydub")
        return False
    except Exception as e:
        print(f"❌ Ошибка при тестировании pydub: {e}")
        return False

def test_audio_formats():
    """Тестирует поддержку различных аудио форматов"""
    print("\n🎵 Тестирую поддержку аудио форматов...")
    
    try:
        from pydub import AudioSegment
        
        # Список форматов для тестирования
        formats = ["wav", "mp3", "flac", "ogg", "m4a"]
        supported_formats = []
        
        for fmt in formats:
            try:
                # Создаем тестовый аудио
                test_audio = AudioSegment.silent(duration=1000)
                temp_file = f"test_output.{fmt}"
                
                # Пробуем экспорт
                test_audio.export(temp_file, format=fmt)
                
                if os.path.exists(temp_file):
                    supported_formats.append(fmt)
                    os.remove(temp_file)  # Удаляем тестовый файл
                    print(f"✅ {fmt.upper()} поддерживается")
                else:
                    print(f"❌ {fmt.upper()} не поддерживается")
                    
            except Exception as e:
                print(f"❌ {fmt.upper()} ошибка: {e}")
        
        print(f"\n📊 Поддерживаемые форматы: {', '.join(supported_formats)}")
        return len(supported_formats) > 0
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании форматов: {e}")
        return False

def test_flac_conversion():
    """Тестирует конвертацию в FLAC"""
    print("\n🔄 Тестирую конвертацию в FLAC...")
    
    try:
        from pydub import AudioSegment
        
        # Создаем тестовый WAV файл
        test_audio = AudioSegment.silent(duration=2000)  # 2 секунды тишины
        test_wav = "test_input.wav"
        test_flac = "test_output.flac"
        
        # Экспортируем в WAV
        test_audio.export(test_wav, format="wav")
        
        if not os.path.exists(test_wav):
            print("❌ Не удалось создать тестовый WAV файл")
            return False
        
        # Конвертируем WAV в FLAC
        audio = AudioSegment.from_wav(test_wav)
        audio.export(test_flac, format="flac")
        
        if os.path.exists(test_flac):
            # Проверяем размер файлов
            wav_size = os.path.getsize(test_wav)
            flac_size = os.path.getsize(test_flac)
            
            print(f"✅ Конвертация WAV → FLAC успешна")
            print(f"   WAV размер: {wav_size} байт")
            print(f"   FLAC размер: {flac_size} байт")
            print(f"   Сжатие: {((wav_size - flac_size) / wav_size * 100):.1f}%")
            
            # Очищаем тестовые файлы
            os.remove(test_wav)
            os.remove(test_flac)
            
            return True
        else:
            print("❌ Конвертация в FLAC не удалась")
            if os.path.exists(test_wav):
                os.remove(test_wav)
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при тестировании конвертации: {e}")
        # Очищаем тестовые файлы при ошибке
        for file in ["test_input.wav", "test_output.flac"]:
            if os.path.exists(file):
                os.remove(file)
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 Начинаю тестирование FLAC поддержки...\n")
    
    tests = [
        ("Системный FLAC", test_system_flac),
        ("Python FLAC библиотеки", test_python_flac),
        ("Аудио форматы", test_audio_formats),
        ("FLAC конвертация", test_flac_conversion),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
            results.append((test_name, False))
    
    # Выводим итоги
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ FLAC")
    print("="*50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ ПРОЙДЕН" if result else "❌ ПРОВАЛЕН"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n📈 Итого: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("🎉 Все тесты пройдены! FLAC готов к работе.")
        print("💡 Теперь можно собирать приложение с поддержкой FLAC.")
        return True
    else:
        print("⚠️ Некоторые тесты не пройдены. Требуется доработка.")
        print("💡 Проверьте установку FLAC: brew install flac")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
