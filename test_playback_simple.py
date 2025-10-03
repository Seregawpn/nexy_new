#!/usr/bin/env python3
"""
Простой тест воспроизведения аудио
"""

import sys
from pathlib import Path

# Добавляем пути для импорта
sys.path.append(str(Path(__file__).parent / "client"))

def test_audio_file():
    """Тест аудио файла"""
    try:
        print("🚀 Запуск теста воспроизведения аудио")
        print("=" * 60)
        
        # Проверяем файл
        audio_file = Path("test_audio_simple.wav")
        if not audio_file.exists():
            print("❌ Аудио файл не найден")
            return False
        
        file_size = audio_file.stat().st_size
        print(f"📁 Аудио файл найден: {file_size} байт")
        
        if file_size < 1000:
            print("❌ Аудио файл слишком маленький")
            return False
        
        print("✅ Аудио файл корректен")
        
        # Пробуем воспроизвести через macOS say
        print("🔊 Пробуем воспроизвести через macOS say...")
        import subprocess
        
        try:
            # Сначала пробуем воспроизвести тестовый текст
            result = subprocess.run(['say', 'Hello! This is a test.'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print("✅ macOS say работает")
            else:
                print(f"❌ macOS say не работает: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Ошибка macOS say: {e}")
            return False
        
        # Пробуем воспроизвести наш файл через afplay
        print("🔊 Пробуем воспроизвести файл через afplay...")
        try:
            result = subprocess.run(['afplay', str(audio_file)], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ afplay воспроизвел файл успешно")
                return True
            else:
                print(f"❌ afplay не сработал: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Ошибка afplay: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def main():
    """Основная функция тестирования"""
    success = test_audio_file()
    
    print()
    print("=" * 60)
    if success:
        print("🎉 ТЕСТ ВОСПРОИЗВЕДЕНИЯ ПРОШЕЛ УСПЕШНО!")
        print("🔊 Аудио должно было воспроизвестись")
    else:
        print("❌ ТЕСТ ВОСПРОИЗВЕДЕНИЯ НЕ ПРОШЕЛ")
        print("🔍 Возможные проблемы:")
        print("   - Аудио устройство не настроено")
        print("   - Разрешения на аудио")
        print("   - Проблемы с macOS аудио системой")
    
    return success

if __name__ == "__main__":
    result = main()
    sys.exit(0 if result else 1)
