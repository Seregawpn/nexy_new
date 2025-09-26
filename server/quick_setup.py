#!/usr/bin/env python3
"""
Быстрая настройка API ключей для тестирования
Создает минимальную рабочую конфигурацию
"""

import os
from pathlib import Path

def create_minimal_config():
    """Создание минимальной конфигурации для тестирования"""
    
    print("🚀 БЫСТРАЯ НАСТРОЙКА NEXY SERVER")
    print("=" * 50)
    
    # Запрашиваем только критически важные ключи
    gemini_key = input("🔑 Введите Gemini API ключ (или Enter для пропуска): ").strip()
    azure_key = input("🔑 Введите Azure Speech ключ (или Enter для пропуска): ").strip()
    azure_region = input("🌍 Введите Azure регион (например: eastus) (или Enter для пропуска): ").strip()
    
    # Создаем конфигурацию
    config_content = f"""# =====================================================
# БЫСТРАЯ КОНФИГУРАЦИЯ NEXY SERVER
# =====================================================
# Создано скриптом quick_setup.py

# =====================================================
# API КЛЮЧИ
# =====================================================
GEMINI_API_KEY={gemini_key or 'YOUR_GEMINI_API_KEY_HERE'}
AZURE_SPEECH_KEY={azure_key or 'YOUR_AZURE_SPEECH_KEY_HERE'}
AZURE_SPEECH_REGION={azure_region or 'YOUR_AZURE_SPEECH_REGION_HERE'}

# =====================================================
# НАСТРОЙКИ ПО УМОЛЧАНИЮ
# =====================================================
GEMINI_MODEL=gemini-2.0-flash-exp
GEMINI_TEMPERATURE=0.7
GEMINI_MAX_TOKENS=2048

AZURE_VOICE_NAME=en-US-AriaNeural
AZURE_VOICE_STYLE=friendly
AZURE_SPEECH_RATE=1.0
AZURE_SPEECH_PITCH=1.0
AZURE_SPEECH_VOLUME=1.0
AZURE_AUDIO_FORMAT=riff-48khz-16bit-mono-pcm

SAMPLE_RATE=48000
CHUNK_SIZE=1024
AUDIO_FORMAT=int16
AUDIO_CHANNELS=1
AUDIO_BITS_PER_SAMPLE=16

STREAMING_CHUNK_SIZE=4096
STREAMING_ENABLED=true

GRPC_HOST=0.0.0.0
GRPC_PORT=50051
MAX_WORKERS=10

DB_HOST=localhost
DB_PORT=5432
DB_NAME=voice_assistant_db
DB_USER=postgres
DB_PASSWORD=your_password_here

MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=60
FALLBACK_TIMEOUT=30

LOG_LEVEL=INFO
LOG_REQUESTS=true
LOG_RESPONSES=false

MAX_SESSIONS=100
SESSION_TIMEOUT=3600
HARDWARE_ID_LENGTH=32

GLOBAL_INTERRUPT_TIMEOUT=300
SESSION_INTERRUPT_TIMEOUT=60
MAX_ACTIVE_SESSIONS=50
"""
    
    # Сохраняем конфигурацию
    config_file = "config.env"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"\n✅ Минимальная конфигурация сохранена в {config_file}")
    
    # Проверяем наличие ключей
    if gemini_key and azure_key and azure_region:
        print("\n🎉 Все ключи настроены! Система готова к работе.")
        return True
    else:
        print("\n⚠️ Некоторые ключи не настроены. Система будет работать в ограниченном режиме.")
        print("\n📋 Для полной настройки запустите:")
        print("   python3 setup_api_keys.py")
        return False

def test_server():
    """Тестирование сервера"""
    print("\n🧪 ТЕСТИРОВАНИЕ СЕРВЕРА")
    print("-" * 30)
    
    try:
        import sys
        sys.path.append('.')
        
        from config.unified_config import get_config
        config = get_config()
        
        print("✅ Централизованная конфигурация загружена")
        
        # Проверяем ключи
        if config.text_processing.gemini_api_key and config.text_processing.gemini_api_key != 'YOUR_GEMINI_API_KEY_HERE':
            print("✅ Gemini API ключ настроен")
        else:
            print("⚠️ Gemini API ключ не настроен")
        
        if config.audio.azure_speech_key and config.audio.azure_speech_key != 'YOUR_AZURE_SPEECH_KEY_HERE':
            print("✅ Azure Speech ключ настроен")
        else:
            print("⚠️ Azure Speech ключ не настроен")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    success = create_minimal_config()
    test_server()
    
    if success:
        print("\n🚀 Сервер готов к запуску!")
        print("Запустите: python3 grpc_server.py")
    else:
        print("\n📝 Для полной настройки запустите:")
        print("   python3 setup_api_keys.py")
