#!/usr/bin/env python3
"""
Конфигуратор TTS методов для Nexy
Позволяет быстро переключаться между Azure TTS, Edge TTS и fallback методами
"""

import os
import sys
from pathlib import Path

def configure_azure_tts():
    """Настройка Azure Speech Services"""
    print("🇺🇸 НАСТРОЙКА AZURE SPEECH SERVICES")
    print("=" * 50)
    print("Для получения ключей:")
    print("1. Перейдите на https://portal.azure.com/")
    print("2. Создайте ресурс 'Speech Services'")
    print("3. Скопируйте ключ и регион")
    print()
    
    # Получаем данные от пользователя
    speech_key = input("Введите SPEECH_KEY (или Enter для пропуска): ").strip()
    speech_region = input("Введите SPEECH_REGION (например, eastus): ").strip()
    
    if speech_key and speech_region:
        # Обновляем config.env
        config_path = Path(__file__).parent / "server" / "config.env"
        
        # Читаем текущий config
        lines = []
        if config_path.exists():
            with open(config_path, 'r') as f:
                lines = f.readlines()
        
        # Обновляем строки
        updated_lines = []
        speech_key_found = False
        speech_region_found = False
        
        for line in lines:
            if line.startswith('SPEECH_KEY=') or line.startswith('# SPEECH_KEY='):
                updated_lines.append(f'SPEECH_KEY={speech_key}\n')
                speech_key_found = True
            elif line.startswith('SPEECH_REGION=') or line.startswith('# SPEECH_REGION='):
                updated_lines.append(f'SPEECH_REGION={speech_region}\n')
                speech_region_found = True
            else:
                updated_lines.append(line)
        
        # Добавляем если не найдены
        if not speech_key_found:
            updated_lines.append(f'SPEECH_KEY={speech_key}\n')
        if not speech_region_found:
            updated_lines.append(f'SPEECH_REGION={speech_region}\n')
        
        # Записываем обратно
        with open(config_path, 'w') as f:
            f.writelines(updated_lines)
        
        print(f"✅ Azure TTS настроен в {config_path}")
        return True
    else:
        print("⏭️ Azure TTS пропущен")
        return False

def configure_edge_tts():
    """Настройка Edge TTS"""
    print("🗣️ НАСТРОЙКА EDGE TTS")
    print("=" * 50)
    print("Edge TTS - бесплатный сервис Microsoft")
    print("Не требует API ключей, только интернет")
    print()
    
    # Выбор голоса
    voices = [
        "en-US-JennyNeural",
        "en-US-AriaNeural",
        "en-US-GuyNeural", 
        "en-US-DavisNeural",
        "en-US-AmberNeural"
    ]
    
    print("Доступные голоса:")
    for i, voice in enumerate(voices, 1):
        print(f"{i}. {voice}")
    
    choice = input(f"\nВыберите голос (1-{len(voices)}) или Enter для JennyNeural: ").strip()
    
    if choice.isdigit() and 1 <= int(choice) <= len(voices):
        selected_voice = voices[int(choice) - 1]
    else:
        selected_voice = voices[0]  # JennyNeural по умолчанию
    
    # Обновляем config.env
    config_path = Path(__file__).parent / "server" / "config.env"
    
    lines = []
    if config_path.exists():
        with open(config_path, 'r') as f:
            lines = f.readlines()
    
    # Обновляем настройки Edge TTS
    updated_lines = []
    for line in lines:
        if line.startswith('EDGE_TTS_VOICE='):
            updated_lines.append(f'EDGE_TTS_VOICE={selected_voice}\n')
        elif line.startswith('USE_EDGE_TTS='):
            updated_lines.append('USE_EDGE_TTS=true\n')
        else:
            updated_lines.append(line)
    
    # Записываем обратно
    with open(config_path, 'w') as f:
        f.writelines(updated_lines)
    
    print(f"✅ Edge TTS настроен: {selected_voice}")
    return True

def disable_all_tts():
    """Отключить все TTS (только fallback)"""
    print("🔇 ОТКЛЮЧЕНИЕ ВСЕХ TTS")
    print("=" * 50)
    print("Будет использоваться только локальный fallback")
    print("⚠️ Вместо речи будут короткие beep'ы")
    print()
    
    confirm = input("Подтвердите отключение (yes/no): ").strip().lower()
    if confirm in ['yes', 'y', 'да', 'д']:
        # Обновляем config.env
        config_path = Path(__file__).parent / "server" / "config.env"
        
        lines = []
        if config_path.exists():
            with open(config_path, 'r') as f:
                lines = f.readlines()
        
        updated_lines = []
        for line in lines:
            if line.startswith('USE_EDGE_TTS='):
                updated_lines.append('USE_EDGE_TTS=false\n')
            elif line.startswith('SPEECH_KEY='):
                updated_lines.append('# SPEECH_KEY=отключен\n')
            elif line.startswith('SPEECH_REGION='):
                updated_lines.append('# SPEECH_REGION=отключен\n')
            else:
                updated_lines.append(line)
        
        with open(config_path, 'w') as f:
            f.writelines(updated_lines)
        
        print("✅ Все TTS отключены")
        return True
    else:
        print("⏭️ Отключение отменено")
        return False

def show_current_config():
    """Показать текущую конфигурацию TTS"""
    print("📋 ТЕКУЩАЯ КОНФИГУРАЦИЯ TTS")
    print("=" * 50)
    
    config_path = Path(__file__).parent / "server" / "config.env"
    
    if not config_path.exists():
        print("❌ Файл config.env не найден")
        return
    
    with open(config_path, 'r') as f:
        lines = f.readlines()
    
    # Извлекаем TTS настройки
    tts_settings = {}
    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            if key in ['USE_EDGE_TTS', 'EDGE_TTS_VOICE', 'SPEECH_KEY', 'SPEECH_REGION']:
                tts_settings[key] = value
    
    # Определяем активный метод
    use_edge = tts_settings.get('USE_EDGE_TTS', 'false').lower() == 'true'
    has_azure = bool(tts_settings.get('SPEECH_KEY')) and bool(tts_settings.get('SPEECH_REGION'))
    
    print("🎤 Активные методы TTS:")
    
    if has_azure:
        print(f"✅ Azure Speech Services")
        print(f"   Ключ: {tts_settings.get('SPEECH_KEY', 'НЕТ')[:10]}...")
        print(f"   Регион: {tts_settings.get('SPEECH_REGION', 'НЕТ')}")
    else:
        print(f"❌ Azure Speech Services (нет ключей)")
    
    if use_edge:
        print(f"✅ Edge TTS")
        print(f"   Голос: {tts_settings.get('EDGE_TTS_VOICE', 'en-US-JennyNeural')}")
    else:
        print(f"❌ Edge TTS (отключен)")
    
    if not has_azure and not use_edge:
        print(f"⚠️ Только локальный fallback (sine-wave)")
    
    print(f"\n🎯 Приоритет:")
    if has_azure:
        print(f"1. Azure TTS (основной)")
        if use_edge:
            print(f"2. Edge TTS (fallback)")
            print(f"3. Sine-wave (последний fallback)")
        else:
            print(f"2. Sine-wave (fallback)")
    elif use_edge:
        print(f"1. Edge TTS (основной)")
        print(f"2. Sine-wave (fallback)")
    else:
        print(f"1. Sine-wave (единственный)")

def main():
    """Главное меню конфигуратора"""
    while True:
        print("\n🎵 КОНФИГУРАТОР TTS ДЛЯ NEXY")
        print("=" * 40)
        print("1. Показать текущую конфигурацию")
        print("2. Настроить Azure TTS")
        print("3. Настроить Edge TTS")
        print("4. Отключить все TTS")
        print("5. Запустить тестирование")
        print("6. Выход")
        
        choice = input("\nВаш выбор (1-6): ").strip()
        
        if choice == "1":
            show_current_config()
        elif choice == "2":
            configure_azure_tts()
        elif choice == "3":
            configure_edge_tts()
        elif choice == "4":
            disable_all_tts()
        elif choice == "5":
            print("\n🧪 Запуск тестирования...")
            print("Выполните: python test_tts_methods.py")
        elif choice == "6":
            print("👋 До свидания!")
            break
        else:
            print("❌ Неверный выбор")

if __name__ == "__main__":
    main()
