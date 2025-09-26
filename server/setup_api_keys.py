#!/usr/bin/env python3
"""
Скрипт для настройки API ключей Nexy Server
Интерактивная настройка всех необходимых ключей и параметров
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any

def print_banner():
    """Печать баннера"""
    print("=" * 60)
    print("🚀 NEXY SERVER - НАСТРОЙКА API КЛЮЧЕЙ")
    print("=" * 60)
    print()

def get_user_input(prompt: str, default: str = "", required: bool = False) -> str:
    """
    Получение ввода от пользователя
    
    Args:
        prompt: Текст запроса
        default: Значение по умолчанию
        required: Обязательно ли поле
        
    Returns:
        Введенное значение
    """
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        value = input(full_prompt).strip()
        
        if not value and default:
            return default
        elif not value and required:
            print("❌ Это поле обязательно для заполнения!")
            continue
        elif not value:
            return ""
        else:
            return value

def setup_gemini_config() -> Dict[str, str]:
    """Настройка конфигурации Gemini"""
    print("🤖 НАСТРОЙКА GOOGLE GEMINI API")
    print("-" * 40)
    print("Получите ключ на: https://makersuite.google.com/app/apikey")
    print()
    
    config = {}
    config['GEMINI_API_KEY'] = get_user_input(
        "🔑 Введите ваш Gemini API ключ", 
        required=True
    )
    
    config['GEMINI_MODEL'] = get_user_input(
        "🧠 Модель Gemini", 
        default="gemini-2.0-flash-exp"
    )
    
    config['GEMINI_TEMPERATURE'] = get_user_input(
        "🌡️ Температура (0.0-2.0)", 
        default="0.7"
    )
    
    config['GEMINI_MAX_TOKENS'] = get_user_input(
        "📝 Максимум токенов", 
        default="2048"
    )
    
    print()
    return config

def setup_azure_config() -> Dict[str, str]:
    """Настройка конфигурации Azure Speech"""
    print("🎵 НАСТРОЙКА AZURE SPEECH SERVICES")
    print("-" * 40)
    print("Получите ключ в Azure Portal: https://portal.azure.com/")
    print()
    
    config = {}
    config['AZURE_SPEECH_KEY'] = get_user_input(
        "🔑 Введите ваш Azure Speech ключ", 
        required=True
    )
    
    config['AZURE_SPEECH_REGION'] = get_user_input(
        "🌍 Регион Azure (например: eastus)", 
        required=True
    )
    
    config['AZURE_VOICE_NAME'] = get_user_input(
        "🗣️ Имя голоса", 
        default="en-US-AriaNeural"
    )
    
    config['AZURE_VOICE_STYLE'] = get_user_input(
        "🎭 Стиль голоса (friendly, cheerful, sad, etc.)", 
        default="friendly"
    )
    
    config['AZURE_SPEECH_RATE'] = get_user_input(
        "⚡ Скорость речи (0.5-2.0)", 
        default="1.0"
    )
    
    config['AZURE_SPEECH_PITCH'] = get_user_input(
        "🎼 Высота голоса (0.5-2.0)", 
        default="1.0"
    )
    
    config['AZURE_SPEECH_VOLUME'] = get_user_input(
        "🔊 Громкость (0.0-1.0)", 
        default="1.0"
    )
    
    print()
    return config

def setup_database_config() -> Dict[str, str]:
    """Настройка конфигурации базы данных"""
    print("🗄️ НАСТРОЙКА БАЗЫ ДАННЫХ POSTGRESQL")
    print("-" * 40)
    print()
    
    config = {}
    config['DB_HOST'] = get_user_input(
        "🏠 Хост базы данных", 
        default="localhost"
    )
    
    config['DB_PORT'] = get_user_input(
        "🔌 Порт базы данных", 
        default="5432"
    )
    
    config['DB_NAME'] = get_user_input(
        "📚 Имя базы данных", 
        default="voice_assistant_db"
    )
    
    config['DB_USER'] = get_user_input(
        "👤 Пользователь базы данных", 
        default="postgres"
    )
    
    config['DB_PASSWORD'] = get_user_input(
        "🔒 Пароль базы данных", 
        required=True
    )
    
    print()
    return config

def setup_audio_config() -> Dict[str, str]:
    """Настройка конфигурации аудио"""
    print("🎧 НАСТРОЙКА АУДИО ПАРАМЕТРОВ")
    print("-" * 40)
    print("ВАЖНО: Эти настройки должны совпадать с клиентом!")
    print()
    
    config = {}
    config['SAMPLE_RATE'] = get_user_input(
        "📊 Частота дискретизации", 
        default="48000"
    )
    
    config['CHUNK_SIZE'] = get_user_input(
        "📦 Размер чанка", 
        default="1024"
    )
    
    config['AUDIO_FORMAT'] = get_user_input(
        "🎵 Формат аудио", 
        default="int16"
    )
    
    config['STREAMING_CHUNK_SIZE'] = get_user_input(
        "🌊 Размер чанка для стриминга", 
        default="4096"
    )
    
    print()
    return config

def setup_grpc_config() -> Dict[str, str]:
    """Настройка конфигурации gRPC"""
    print("🌐 НАСТРОЙКА GRPC СЕРВЕРА")
    print("-" * 40)
    print()
    
    config = {}
    config['GRPC_HOST'] = get_user_input(
        "🏠 Хост gRPC сервера", 
        default="0.0.0.0"
    )
    
    config['GRPC_PORT'] = get_user_input(
        "🔌 Порт gRPC сервера", 
        default="50051"
    )
    
    config['MAX_WORKERS'] = get_user_input(
        "👥 Максимум воркеров", 
        default="10"
    )
    
    print()
    return config

def save_config_to_env(config: Dict[str, str], env_file: str = "config.env"):
    """Сохранение конфигурации в .env файл"""
    print(f"💾 Сохранение конфигурации в {env_file}...")
    
    # Читаем существующий файл если есть
    existing_lines = []
    if Path(env_file).exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()
    
    # Создаем новый файл
    with open(env_file, 'w', encoding='utf-8') as f:
        # Записываем заголовок
        f.write("# =====================================================\n")
        f.write("# ЦЕНТРАЛИЗОВАННАЯ КОНФИГУРАЦИЯ NEXY SERVER\n")
        f.write("# =====================================================\n")
        f.write("# Автоматически сгенерировано скриптом setup_api_keys.py\n")
        f.write(f"# Дата создания: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("\n")
        
        # Группируем настройки по категориям
        categories = {
            "API КЛЮЧИ": ["GEMINI_API_KEY", "AZURE_SPEECH_KEY", "AZURE_SPEECH_REGION"],
            "GEMINI НАСТРОЙКИ": ["GEMINI_MODEL", "GEMINI_TEMPERATURE", "GEMINI_MAX_TOKENS"],
            "AZURE НАСТРОЙКИ": ["AZURE_VOICE_NAME", "AZURE_VOICE_STYLE", "AZURE_SPEECH_RATE", "AZURE_SPEECH_PITCH", "AZURE_SPEECH_VOLUME"],
            "АУДИО НАСТРОЙКИ": ["SAMPLE_RATE", "CHUNK_SIZE", "AUDIO_FORMAT", "STREAMING_CHUNK_SIZE"],
            "БАЗА ДАННЫХ": ["DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD"],
            "GRPC НАСТРОЙКИ": ["GRPC_HOST", "GRPC_PORT", "MAX_WORKERS"]
        }
        
        for category, keys in categories.items():
            f.write(f"\n# =====================================================\n")
            f.write(f"# {category}\n")
            f.write(f"# =====================================================\n")
            
            for key in keys:
                if key in config:
                    f.write(f"{key}={config[key]}\n")
        
        # Добавляем остальные настройки из существующего файла
        f.write("\n# =====================================================\n")
        f.write("# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ\n")
        f.write("# =====================================================\n")
        
        # Настройки по умолчанию
        default_settings = {
            "MAX_CONCURRENT_REQUESTS": "10",
            "REQUEST_TIMEOUT": "60",
            "FALLBACK_TIMEOUT": "30",
            "LOG_LEVEL": "INFO",
            "LOG_REQUESTS": "true",
            "LOG_RESPONSES": "false",
            "MAX_SESSIONS": "100",
            "SESSION_TIMEOUT": "3600",
            "HARDWARE_ID_LENGTH": "32"
        }
        
        for key, value in default_settings.items():
            if key not in config:
                f.write(f"{key}={value}\n")
    
    print(f"✅ Конфигурация сохранена в {env_file}")

def test_configuration():
    """Тестирование конфигурации"""
    print("🧪 ТЕСТИРОВАНИЕ КОНФИГУРАЦИИ")
    print("-" * 40)
    
    try:
        # Добавляем текущую директорию в путь
        sys.path.append('.')
        
        # Импортируем и тестируем конфигурацию
        from config.unified_config import get_config
        config = get_config()
        
        print("✅ Централизованная конфигурация загружена успешно")
        
        # Проверяем статус
        status = config.get_status()
        
        print("\n📊 Статус конфигурации:")
        for section, values in status.items():
            print(f"\n🔧 {section.upper()}:")
            for key, value in values.items():
                if 'key' in key.lower() or 'password' in key.lower():
                    display_value = "✅ Установлен" if value else "❌ Не установлен"
                else:
                    display_value = value
                print(f"  {key}: {display_value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования конфигурации: {e}")
        return False

def main():
    """Основная функция"""
    print_banner()
    
    # Собираем конфигурацию
    all_config = {}
    
    # Настройка Gemini
    all_config.update(setup_gemini_config())
    
    # Настройка Azure
    all_config.update(setup_azure_config())
    
    # Настройка базы данных
    all_config.update(setup_database_config())
    
    # Настройка аудио
    all_config.update(setup_audio_config())
    
    # Настройка gRPC
    all_config.update(setup_grpc_config())
    
    # Сохраняем конфигурацию
    save_config_to_env(all_config)
    
    # Тестируем конфигурацию
    if test_configuration():
        print("\n🎉 НАСТРОЙКА ЗАВЕРШЕНА УСПЕШНО!")
        print("\n📋 Следующие шаги:")
        print("1. Проверьте файл config.env")
        print("2. Запустите сервер: python3 grpc_server.py")
        print("3. Протестируйте с клиентом")
    else:
        print("\n⚠️ НАСТРОЙКА ЗАВЕРШЕНА С ПРЕДУПРЕЖДЕНИЯМИ")
        print("Проверьте конфигурацию и попробуйте снова")

if __name__ == "__main__":
    main()
