#!/usr/bin/env python3
"""
Скрипт для переупаковки Nexy AI Assistant
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def main():
    print("🎯 NEXY AI ASSISTANT - ПЕРЕУПАКОВКА")
    print("==================================")
    
    # Переходим в директорию проекта
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"📁 Рабочая директория: {os.getcwd()}")
    
    # Очищаем старые сборки
    print("🧹 Очистка старых сборок...")
    for dir_name in ['dist', 'build']:
        if os.path.exists(dir_name):
            print(f"  Удаляем {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Удаляем старые файлы
    for pattern in ['*.pkg', '*.dmg', '*.app']:
        for file_path in Path('.').glob(pattern):
            if file_path.is_file():
                print(f"  Удаляем {file_path}")
                file_path.unlink()
    
    print("✅ Очистка завершена")
    
    # Проверяем архитектуру
    print("🔍 Проверка архитектуры...")
    result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
    if result.returncode != 0 or 'arm64' not in result.stdout:
        print("❌ Требуется Apple Silicon (arm64)")
        sys.exit(1)
    print("✅ Архитектура: arm64")
    
    # Проверяем PyInstaller
    print("🔍 Проверка PyInstaller...")
    try:
        result = subprocess.run(['pyinstaller', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ PyInstaller не найден")
            sys.exit(1)
        print(f"✅ PyInstaller: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ PyInstaller не найден")
        sys.exit(1)
    
    # Проверяем сертификаты
    print("🔍 Проверка сертификатов...")
    try:
        result = subprocess.run(['security', 'find-identity', '-p', 'codesigning', '-v'], 
                              capture_output=True, text=True)
        if 'Developer ID Application' not in result.stdout:
            print("❌ Сертификат приложения не найден")
            sys.exit(1)
        if 'Developer ID Installer' not in result.stdout:
            print("❌ Сертификат инсталлятора не найден")
            sys.exit(1)
        print("✅ Сертификаты найдены")
    except FileNotFoundError:
        print("❌ security не найден")
        sys.exit(1)
    
    # Делаем скрипты исполняемыми
    print("🔧 Настройка скриптов...")
    os.chmod('packaging/build_all.sh', 0o755)
    os.chmod('scripts/postinstall', 0o755)
    print("✅ Скрипты настроены")
    
    # Запускаем сборку
    print("🚀 Запуск сборки...")
    try:
        result = subprocess.run(['./packaging/build_all.sh'], 
                              cwd=os.getcwd(),
                              capture_output=False,
                              text=True)
        if result.returncode == 0:
            print("✅ Сборка завершена успешно")
        else:
            print(f"❌ Ошибка сборки: {result.returncode}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка запуска сборки: {e}")
        sys.exit(1)
    
    print("🎉 ПЕРЕУПАКОВКА ЗАВЕРШЕНА!")
    print("📦 Проверьте папку dist/ для артефактов")

if __name__ == "__main__":
    main()