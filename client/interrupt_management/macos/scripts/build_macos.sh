#!/bin/bash

# Скрипт сборки interrupt_management для macOS
# Автор: Nexy Development Team
# Версия: 1.0.0

set -e  # Остановка при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для логирования
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверяем зависимости..."
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        error "Python3 не найден. Установите Python 3.8+"
        exit 1
    fi
    
    # Проверяем PyInstaller
    if ! python3 -c "import PyInstaller" &> /dev/null; then
        error "PyInstaller не найден. Установите: pip install PyInstaller"
        exit 1
    fi
    
    # Проверяем asyncio
    if ! python3 -c "import asyncio" &> /dev/null; then
        error "asyncio не найден. Установите: pip install asyncio"
        exit 1
    fi
    
    # Проверяем threading
    if ! python3 -c "import threading" &> /dev/null; then
        error "threading не найден. Установите: pip install threading"
        exit 1
    fi
    
    success "Все зависимости найдены"
}

# Очистка предыдущих сборок
clean_build() {
    log "Очищаем предыдущие сборки..."
    
    if [ -d "build" ]; then
        rm -rf build
        log "Удалена папка build"
    fi
    
    if [ -d "dist" ]; then
        rm -rf dist
        log "Удалена папка dist"
    fi
    
    if [ -f "interrupt_management.spec" ]; then
        rm -f interrupt_management.spec
        log "Удален файл .spec"
    fi
    
    success "Очистка завершена"
}

# Создание .spec файла
create_spec() {
    log "Создаем .spec файл для PyInstaller..."
    
    cat > interrupt_management.spec << 'EOF'
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

# Путь к модулю
module_path = os.path.join(os.path.dirname(__file__), '..')

# Собираем данные
datas = []

# Скрытые импорты
hiddenimports = [
    'asyncio',
    'threading',
    'logging',
    'json',
    'time',
    'datetime',
    'typing',
    'dataclasses',
    'enum',
    'pathlib',
    'os',
    'sys',
    'queue',
    'collections',
    'itertools',
    'functools',
    'concurrent.futures',
    'weakref',
    'copy',
    'abc',
    'contextlib'
]

# Основная конфигурация
a = Analysis(
    ['../interrupt_management/__init__.py'],
    pathex=[module_path],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Создание PYZ
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Создание исполняемого файла
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='interrupt_management',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements/interrupt_management.entitlements',
    icon='../assets/interrupt_management.icns'
)

# Создание приложения
app = BUNDLE(
    exe,
    name='Interrupt Management.app',
    icon='../assets/interrupt_management.icns',
    bundle_identifier='com.nexy.interrupt.management',
    info_plist='info/Info.plist',
    version='1.0.0',
    short_version='1.0.0',
    entitlements_file='entitlements/interrupt_management.entitlements'
)
EOF

    success ".spec файл создан"
}

# Сборка приложения
build_app() {
    log "Собираем приложение..."
    
    # Переходим в папку macos
    cd "$(dirname "$0")"
    
    # Запускаем PyInstaller
    pyinstaller interrupt_management.spec \
        --clean \
        --noconfirm \
        --log-level=INFO \
        --distpath=dist \
        --workpath=build \
        --specpath=.
    
    if [ $? -eq 0 ]; then
        success "Сборка завершена успешно"
    else
        error "Ошибка при сборке"
        exit 1
    fi
}

# Проверка результата
check_result() {
    log "Проверяем результат сборки..."
    
    if [ -d "dist/Interrupt Management.app" ]; then
        success "Приложение создано: dist/Interrupt Management.app"
        
        # Показываем размер
        size=$(du -sh "dist/Interrupt Management.app" | cut -f1)
        log "Размер приложения: $size"
        
        # Показываем содержимое
        log "Содержимое приложения:"
        ls -la "dist/Interrupt Management.app/Contents/"
        
    else
        error "Приложение не найдено"
        exit 1
    fi
}

# Основная функция
main() {
    log "Начинаем сборку interrupt_management для macOS..."
    
    check_dependencies
    clean_build
    create_spec
    build_app
    check_result
    
    success "Сборка завершена успешно!"
    log "Приложение находится в: dist/Interrupt Management.app"
    log "Для подписи и нотаризации используйте: ./sign_and_notarize.sh"
}

# Запуск
main "$@"
