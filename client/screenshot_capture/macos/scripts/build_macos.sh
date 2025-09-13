#!/bin/bash

# Скрипт сборки screenshot_capture для macOS
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
    
    # Проверяем PyObjC
    if ! python3 -c "import AppKit" &> /dev/null; then
        error "PyObjC не найден. Установите: pip install pyobjc-framework-Cocoa pyobjc-framework-CoreGraphics"
        exit 1
    fi
    
    # Проверяем PIL
    if ! python3 -c "import PIL" &> /dev/null; then
        error "PIL не найден. Установите: pip install Pillow"
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
    
    if [ -f "screenshot_capture.spec" ]; then
        rm -f screenshot_capture.spec
        log "Удален файл .spec"
    fi
    
    success "Очистка завершена"
}

# Создание .spec файла
create_spec() {
    log "Создаем .spec файл для PyInstaller..."
    
    cat > screenshot_capture.spec << 'EOF'
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
    'AppKit',
    'CoreGraphics',
    'Foundation',
    'Quartz',
    'PIL',
    'PIL.Image',
    'base64',
    'logging',
    'asyncio',
    'yaml',
    'pathlib',
    'typing',
    'dataclasses',
    'enum',
    'time',
    'threading'
]

# Основная конфигурация
a = Analysis(
    ['../screenshot_capture/__init__.py'],
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
    name='screenshot_capture',
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
    entitlements_file='entitlements/screenshot_capture.entitlements',
    icon='../assets/screenshot_capture.icns'
)

# Создание приложения
app = BUNDLE(
    exe,
    name='Screenshot Capture.app',
    icon='../assets/screenshot_capture.icns',
    bundle_identifier='com.nexy.screenshot.capture',
    info_plist='info/Info.plist',
    version='1.0.0',
    short_version='1.0.0',
    entitlements_file='entitlements/screenshot_capture.entitlements'
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
    pyinstaller screenshot_capture.spec \
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
    
    if [ -d "dist/Screenshot Capture.app" ]; then
        success "Приложение создано: dist/Screenshot Capture.app"
        
        # Показываем размер
        size=$(du -sh "dist/Screenshot Capture.app" | cut -f1)
        log "Размер приложения: $size"
        
        # Показываем содержимое
        log "Содержимое приложения:"
        ls -la "dist/Screenshot Capture.app/Contents/"
        
    else
        error "Приложение не найдено"
        exit 1
    fi
}

# Основная функция
main() {
    log "Начинаем сборку screenshot_capture для macOS..."
    
    check_dependencies
    clean_build
    create_spec
    build_app
    check_result
    
    success "Сборка завершена успешно!"
    log "Приложение находится в: dist/Screenshot Capture.app"
    log "Для подписи и нотаризации используйте: ./sign_and_notarize.sh"
}

# Запуск
main "$@"