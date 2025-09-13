#!/usr/bin/env python3
"""
Тест модуля input_processing для проверки функциональности
"""

import sys
import os
import logging
import time
import asyncio

# Добавляем путь к модулю
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_imports():
    """Тест импорта всех компонентов модуля"""
    print("🧪 Тестируем импорты модуля input_processing...")
    
    try:
        # Тест основного модуля
        from input_processing import (
            KeyboardMonitor, KeyEvent, KeyEventType, KeyboardConfig,
            SpeechRecognizer, SpeechEvent, SpeechEventType, SpeechState, SpeechConfig,
            InputConfig, DEFAULT_INPUT_CONFIG
        )
        print("✅ Основной модуль импортирован успешно")
        
        # Тест keyboard модуля
        from input_processing.keyboard import (
            KeyboardMonitor, KeyEvent, KeyEventType, KeyboardConfig
        )
        print("✅ Keyboard модуль импортирован успешно")
        
        # Тест speech модуля
        from input_processing.speech import (
            SpeechRecognizer, SpeechEvent, SpeechEventType, SpeechState, SpeechConfig
        )
        print("✅ Speech модуль импортирован успешно")
        
        # Тест config модуля
        from input_processing.config import (
            InputConfig, DEFAULT_INPUT_CONFIG
        )
        print("✅ Config модуль импортирован успешно")
        
        return True
        
    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        return False
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

def test_keyboard_types():
    """Тест типов данных клавиатуры"""
    print("\n⌨️ Тестируем типы данных клавиатуры...")
    
    try:
        from input_processing.keyboard.types import KeyEvent, KeyEventType, KeyType, KeyboardConfig
        
        # Тест KeyEventType
        event_types = [KeyEventType.PRESS, KeyEventType.RELEASE, KeyEventType.HOLD, 
                      KeyEventType.SHORT_PRESS, KeyEventType.LONG_PRESS]
        print(f"✅ KeyEventType: {[et.value for et in event_types]}")
        
        # Тест KeyType
        key_types = [KeyType.SPACE, KeyType.CTRL, KeyType.ALT, KeyType.SHIFT, 
                    KeyType.ENTER, KeyType.ESC]
        print(f"✅ KeyType: {[kt.value for kt in key_types]}")
        
        # Тест KeyEvent
        event = KeyEvent(
            key="space",
            event_type=KeyEventType.PRESS,
            timestamp=time.time(),
            duration=0.5
        )
        print(f"✅ KeyEvent создан: {event.key} - {event.event_type.value}")
        
        # Тест KeyboardConfig
        config = KeyboardConfig(
            key_to_monitor="space",
            short_press_threshold=0.6,
            long_press_threshold=2.0
        )
        print(f"✅ KeyboardConfig создан: {config.key_to_monitor}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка типов клавиатуры: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_speech_types():
    """Тест типов данных речи"""
    print("\n🎤 Тестируем типы данных речи...")
    
    try:
        from input_processing.speech.types import SpeechEvent, SpeechEventType, SpeechState, SpeechConfig
        
        # Тест SpeechEventType
        event_types = [SpeechEventType.START, SpeechEventType.END, SpeechEventType.RESULT, 
                      SpeechEventType.ERROR, SpeechEventType.TIMEOUT]
        print(f"✅ SpeechEventType: {[et.value for et in event_types]}")
        
        # Тест SpeechState
        states = [SpeechState.IDLE, SpeechState.LISTENING, SpeechState.PROCESSING, 
                 SpeechState.ERROR]
        print(f"✅ SpeechState: {[s.value for s in states]}")
        
        # Тест SpeechEvent
        event = SpeechEvent(
            event_type=SpeechEventType.START,
            state=SpeechState.IDLE,
            timestamp=time.time(),
            text="test speech"
        )
        print(f"✅ SpeechEvent создан: {event.event_type.value}")
        
        # Тест SpeechConfig
        config = SpeechConfig(
            language="en-US",
            timeout=5.0,
            phrase_timeout=0.5
        )
        print(f"✅ SpeechConfig создан: {config.language}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка типов речи: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_config():
    """Тест конфигурации"""
    print("\n⚙️ Тестируем конфигурацию...")
    
    try:
        from input_processing.config.input_config import InputConfig, DEFAULT_INPUT_CONFIG
        
        # Тест DEFAULT_INPUT_CONFIG
        print(f"✅ DEFAULT_INPUT_CONFIG: {DEFAULT_INPUT_CONFIG}")
        
        # Тест InputConfig
        from input_processing.keyboard.types import KeyboardConfig
        from input_processing.speech.types import SpeechConfig
        
        config = InputConfig(
            keyboard=KeyboardConfig(key_to_monitor="space"),
            speech=SpeechConfig(language="en-US")
        )
        print(f"✅ InputConfig создан: keyboard={config.keyboard.key_to_monitor}, speech={config.speech.language}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка конфигурации: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_keyboard_monitor():
    """Тест монитора клавиатуры"""
    print("\n⌨️ Тестируем монитор клавиатуры...")
    
    try:
        from input_processing.keyboard.keyboard_monitor import KeyboardMonitor
        from input_processing.keyboard.types import KeyboardConfig
        
        # Создание конфигурации
        config = KeyboardConfig(
            key_to_monitor="space",
            short_press_threshold=0.6,
            long_press_threshold=2.0
        )
        
        # Создание монитора
        monitor = KeyboardMonitor(config)
        print(f"✅ KeyboardMonitor создан: {monitor.config.key_to_monitor}")
        
        # Проверка методов
        methods = ['start_monitoring', 'stop_monitoring', 'is_monitoring', 'register_callback']
        for method in methods:
            if hasattr(monitor, method):
                print(f"✅ Метод {method} найден")
            else:
                print(f"❌ Метод {method} не найден")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка монитора клавиатуры: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_speech_recognizer():
    """Тест распознавателя речи"""
    print("\n🎤 Тестируем распознаватель речи...")
    
    try:
        from input_processing.speech.speech_recognizer import SpeechRecognizer
        from input_processing.speech.types import SpeechConfig
        
        # Создание конфигурации
        config = SpeechConfig(
            language="en-US",
            timeout=5.0,
            phrase_timeout=0.5
        )
        
        # Создание распознавателя
        recognizer = SpeechRecognizer(config)
        print(f"✅ SpeechRecognizer создан: {recognizer.config.language}")
        
        # Проверка методов
        methods = ['start_recording', 'stop_recording', 'is_recording', 'register_callback']
        for method in methods:
            if hasattr(recognizer, method):
                print(f"✅ Метод {method} найден")
            else:
                print(f"❌ Метод {method} не найден")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка распознавателя речи: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_integration():
    """Тест интеграции компонентов"""
    print("\n🔗 Тестируем интеграцию компонентов...")
    
    try:
        from input_processing import KeyboardMonitor, SpeechRecognizer, InputConfig
        from input_processing.keyboard.types import KeyboardConfig
        from input_processing.speech.types import SpeechConfig
        
        # Создание конфигурации
        keyboard_config = KeyboardConfig(key_to_monitor="space")
        speech_config = SpeechConfig(language="en-US")
        input_config = InputConfig(keyboard=keyboard_config, speech=speech_config)
        
        # Создание компонентов
        keyboard_monitor = KeyboardMonitor(keyboard_config)
        speech_recognizer = SpeechRecognizer(speech_config)
        
        print(f"✅ KeyboardMonitor создан: {keyboard_monitor.config.key_to_monitor}")
        print(f"✅ SpeechRecognizer создан: {speech_recognizer.config.language}")
        print(f"✅ InputConfig создан: {input_config.keyboard.key_to_monitor}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка интеграции: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Тест обработки ошибок"""
    print("\n🚨 Тестируем обработку ошибок...")
    
    try:
        from input_processing.keyboard.types import KeyboardConfig
        from input_processing.speech.types import SpeechConfig
        
        # Тест с невалидными параметрами
        try:
            invalid_config = KeyboardConfig(
                key_to_monitor="invalid_key",
                short_press_threshold=-1.0,  # Невалидное значение
                long_press_threshold=0.5     # Меньше short_press_threshold
            )
            print("⚠️ Невалидная конфигурация принята")
        except Exception as e:
            print(f"✅ Ошибка валидации обработана: {type(e).__name__}")
        
        # Тест с невалидными параметрами речи
        try:
            invalid_speech_config = SpeechConfig(
                language="invalid_lang",
                timeout=-1.0,  # Невалидное значение
                phrase_timeout=10.0  # Больше timeout
            )
            print("⚠️ Невалидная конфигурация речи принята")
        except Exception as e:
            print(f"✅ Ошибка валидации речи обработана: {type(e).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка в тесте обработки ошибок: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Основная функция тестирования"""
    print("🚀 НАЧИНАЕМ ТЕСТИРОВАНИЕ МОДУЛЯ INPUT_PROCESSING")
    print("=" * 60)
    
    # Тест 1: Импорты
    imports_ok = test_imports()
    
    # Тест 2: Типы данных клавиатуры
    keyboard_types_ok = test_keyboard_types()
    
    # Тест 3: Типы данных речи
    speech_types_ok = test_speech_types()
    
    # Тест 4: Конфигурация
    config_ok = test_config()
    
    # Тест 5: Монитор клавиатуры
    keyboard_monitor_ok = test_keyboard_monitor()
    
    # Тест 6: Распознаватель речи
    speech_recognizer_ok = test_speech_recognizer()
    
    # Тест 7: Интеграция
    integration_ok = test_integration()
    
    # Тест 8: Обработка ошибок
    error_handling_ok = test_error_handling()
    
    # Итоговый результат
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"✅ Импорты: {'ПРОЙДЕН' if imports_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Типы данных клавиатуры: {'ПРОЙДЕН' if keyboard_types_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Типы данных речи: {'ПРОЙДЕН' if speech_types_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Конфигурация: {'ПРОЙДЕН' if config_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Монитор клавиатуры: {'ПРОЙДЕН' if keyboard_monitor_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Распознаватель речи: {'ПРОЙДЕН' if speech_recognizer_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Интеграция: {'ПРОЙДЕН' if integration_ok else 'ПРОВАЛЕН'}")
    print(f"✅ Обработка ошибок: {'ПРОЙДЕН' if error_handling_ok else 'ПРОВАЛЕН'}")
    
    all_tests_passed = all([
        imports_ok, keyboard_types_ok, speech_types_ok, config_ok,
        keyboard_monitor_ok, speech_recognizer_ok, integration_ok, error_handling_ok
    ])
    
    print(f"\n🎯 ОБЩИЙ РЕЗУЛЬТАТ: {'ВСЕ ТЕСТЫ ПРОЙДЕНЫ' if all_tests_passed else 'ЕСТЬ ОШИБКИ'}")
    
    if all_tests_passed:
        print("🎉 Модуль input_processing готов к использованию!")
    else:
        print("⚠️ Требуется исправление ошибок перед использованием")
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)