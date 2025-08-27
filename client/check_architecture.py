#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Проверка архитектуры системы для macOS приложения
"""

import platform
import subprocess
import sys

def check_system_architecture():
    """Проверяет архитектуру системы"""
    print("🔍 Проверяю архитектуру системы...")
    
    # Python архитектура
    python_arch = platform.machine()
    print(f"🐍 Python архитектура: {python_arch}")
    
    # Системная архитектура
    system_arch = platform.processor()
    print(f"💻 Системная архитектура: {system_arch}")
    
    # macOS версия
    try:
        result = subprocess.run(['sw_vers', '-productVersion'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            macos_version = result.stdout.strip()
            print(f"🍎 macOS версия: {macos_version}")
        else:
            print("❌ Не удалось определить версию macOS")
            macos_version = "Unknown"
    except Exception as e:
        print(f"❌ Ошибка при определении версии macOS: {e}")
        macos_version = "Unknown"
    
    # Проверяем совместимость
    is_arm64 = python_arch == "arm64"
    is_macos_12_plus = False
    
    if macos_version != "Unknown":
        try:
            major_version = int(macos_version.split('.')[0])
            is_macos_12_plus = major_version >= 12
        except:
            is_macos_12_plus = False
    
    print(f"\n📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
    print(f"   ARM64 архитектура: {'✅ ДА' if is_arm64 else '❌ НЕТ'}")
    print(f"   macOS 12.0+: {'✅ ДА' if is_macos_12_plus else '❌ НЕТ'}")
    
    # Вывод рекомендаций
    if is_arm64 and is_macos_12_plus:
        print("\n🎉 Система полностью совместима!")
        print("   ✅ Можно собирать приложение для M1/M2")
        print("   ✅ Поддерживается macOS 12.0+")
        return True
    elif is_arm64:
        print("\n⚠️ Частично совместима")
        print("   ✅ ARM64 архитектура поддерживается")
        print("   ❌ macOS версия ниже 12.0")
        print("   💡 Обновите macOS до версии 12.0+")
        return False
    else:
        print("\n❌ Система НЕ совместима!")
        print("   ❌ Intel архитектура НЕ поддерживается")
        print("   💡 Приложение работает только на M1/M2 Mac")
        return False

def check_rosetta():
    """Проверяет наличие Rosetta 2"""
    print("\n🔍 Проверяю Rosetta 2...")
    
    try:
        result = subprocess.run(['softwareupdate', '--list-rosetta'], 
                              capture_output=True, text=True, timeout=10)
        
        if "Rosetta 2 is already installed" in result.stdout:
            print("✅ Rosetta 2 установлен")
            print("⚠️  ВНИМАНИЕ: Rosetta 2 может запускать Intel приложения")
            print("💡 Для чистого ARM64 приложения рекомендуется отключить Rosetta 2")
            return True
        elif "Rosetta 2 is not installed" in result.stdout:
            print("✅ Rosetta 2 НЕ установлен")
            print("🎉 Система работает в чистом ARM64 режиме")
            return False
        else:
            print("❓ Статус Rosetta 2 не определен")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка при проверке Rosetta 2: {e}")
        return None

def check_required_tools():
    """Проверяет необходимые инструменты для сборки"""
    print("\n🔧 Проверяю инструменты для сборки...")
    
    tools = {
        "PyInstaller": "pyinstaller",
        "Python 3.12+": "python3",
        "Homebrew": "brew",
        "FLAC": "flac",
        "FFmpeg": "ffmpeg"
    }
    
    missing_tools = []
    
    for tool_name, command in tools.items():
        try:
            # FFmpeg использует другой флаг
            if command == "ffmpeg":
                result = subprocess.run([command, '-version'], 
                                      capture_output=True, text=True, timeout=10)
                # FFmpeg возвращает версию в stdout
                if result.stdout and "ffmpeg version" in result.stdout:
                    version = result.stdout.strip().split('\n')[0]
                    print(f"✅ {tool_name}: {version}")
                else:
                    print(f"❌ {tool_name}: не работает")
                    missing_tools.append(tool_name)
            else:
                result = subprocess.run([command, '--version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    version = result.stdout.strip().split('\n')[0]
                    print(f"✅ {tool_name}: {version}")
                else:
                    print(f"❌ {tool_name}: не работает")
                    missing_tools.append(tool_name)
        except FileNotFoundError:
            print(f"❌ {tool_name}: не найден")
            missing_tools.append(tool_name)
        except Exception as e:
            print(f"❌ {tool_name}: ошибка проверки - {e}")
            missing_tools.append(tool_name)
    
    if missing_tools:
        print(f"\n⚠️ Отсутствуют инструменты: {', '.join(missing_tools)}")
        return False
    else:
        print("\n✅ Все необходимые инструменты установлены")
        return True

def main():
    """Основная функция проверки"""
    print("🚀 Проверка совместимости системы для сборки macOS приложения\n")
    
    # Проверяем архитектуру
    arch_compatible = check_system_architecture()
    
    # Проверяем Rosetta 2
    rosetta_status = check_rosetta()
    
    # Проверяем инструменты
    tools_ready = check_required_tools()
    
    # Итоговый результат
    print("\n" + "="*50)
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("="*50)
    
    if arch_compatible and tools_ready:
        print("🎉 СИСТЕМА ГОТОВА К СБОРКЕ!")
        print("   ✅ Архитектура ARM64 (M1/M2)")
        print("   ✅ macOS 12.0+")
        print("   ✅ Все инструменты установлены")
        print("\n💡 Можете запускать сборку:")
        print("   ./build/pyinstaller/build_script.sh")
        return True
    else:
        print("⚠️ СИСТЕМА НЕ ГОТОВА К СБОРКЕ")
        if not arch_compatible:
            print("   ❌ Проблемы с архитектурой")
        if not tools_ready:
            print("   ❌ Отсутствуют инструменты")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
