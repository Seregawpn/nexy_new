#!/usr/bin/env python3
"""
Скрипт для очистки старых сборок и запуска новой упаковки
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def clean_old_builds():
    """Очистка старых сборок"""
    print("🧹 Очистка старых сборок...")
    
    # Удаляем старые папки
    dirs_to_remove = ['dist', 'build']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"  Удаляем {dir_name}/")
            shutil.rmtree(dir_name)
    
    # Удаляем старые файлы
    files_to_remove = ['*.pkg', '*.dmg', '*.app']
    for pattern in files_to_remove:
        for file_path in Path('.').glob(pattern):
            if file_path.is_file():
                print(f"  Удаляем {file_path}")
                file_path.unlink()
    
    print("✅ Очистка завершена")

def check_requirements():
    """Проверка требований"""
    print("🔍 Проверка требований...")
    
    # Проверяем архитектуру
    result = subprocess.run(['uname', '-m'], capture_output=True, text=True)
    if result.returncode != 0 or 'arm64' not in result.stdout:
        print("❌ Требуется Apple Silicon (arm64)")
        return False
    
    # Проверяем PyInstaller
    try:
        result = subprocess.run(['pyinstaller', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ PyInstaller не найден")
            return False
        print(f"  PyInstaller: {result.stdout.strip()}")
    except FileNotFoundError:
        print("❌ PyInstaller не найден")
        return False
    
    # Проверяем сертификаты
    try:
        result = subprocess.run(['security', 'find-identity', '-p', 'codesigning', '-v'], 
                              capture_output=True, text=True)
        if 'Developer ID Application' not in result.stdout:
            print("❌ Сертификат приложения не найден")
            return False
        if 'Developer ID Installer' not in result.stdout:
            print("❌ Сертификат инсталлятора не найден")
            return False
        print("  Сертификаты: OK")
    except FileNotFoundError:
        print("❌ security не найден")
        return False
    
    print("✅ Все требования выполнены")
    return True

def run_build():
    """Запуск сборки"""
    print("🚀 Запуск сборки...")
    
    build_script = Path('packaging/build_all.sh')
    if not build_script.exists():
        print("❌ Скрипт сборки не найден")
        return False
    
    # Делаем скрипт исполняемым
    os.chmod(build_script, 0o755)
    
    # Запускаем сборку
    try:
        result = subprocess.run([str(build_script)], 
                              cwd=os.getcwd(),
                              capture_output=False,
                              text=True)
        if result.returncode == 0:
            print("✅ Сборка завершена успешно")
            return True
        else:
            print(f"❌ Ошибка сборки: {result.returncode}")
            return False
    except Exception as e:
        print(f"❌ Ошибка запуска сборки: {e}")
        return False

def main():
    """Главная функция"""
    print("🎯 NEXY AI ASSISTANT - ОЧИСТКА И СБОРКА")
    print("=======================================")
    
    # Переходим в директорию проекта
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    print(f"📁 Рабочая директория: {os.getcwd()}")
    
    # Очищаем старые сборки
    clean_old_builds()
    
    # Проверяем требования
    if not check_requirements():
        print("❌ Требования не выполнены")
        sys.exit(1)
    
    # Запускаем сборку
    if not run_build():
        print("❌ Сборка не удалась")
        sys.exit(1)
    
    print("🎉 ВСЕ ГОТОВО!")
    print("📦 Проверьте папку dist/ для артефактов")

if __name__ == "__main__":
    main()

