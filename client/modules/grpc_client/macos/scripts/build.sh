#!/bin/bash

# Скрипт сборки gRPC клиента для macOS
# Автор: Nexy Development Team
# Версия: 1.0.0

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверка зависимостей
check_dependencies() {
    log "Проверка зависимостей..."
    
    # Проверяем Python
    if ! command -v python3 &> /dev/null; then
        error "Python 3 не найден"
        exit 1
    fi
    
    # Проверяем pip
    if ! command -v pip3 &> /dev/null; then
        error "pip3 не найден"
        exit 1
    fi
    
    # Проверяем PyInstaller
    if ! python3 -c "import PyInstaller" &> /dev/null; then
        warning "PyInstaller не найден, устанавливаем..."
        pip3 install PyInstaller
    fi
    
    # Проверяем grpc
    if ! python3 -c "import grpc" &> /dev/null; then
        warning "grpc не найден, устанавливаем..."
        pip3 install grpcio grpcio-tools
    fi
    
    success "Все зависимости установлены"
}

# Очистка предыдущих сборок
clean() {
    log "Очистка предыдущих сборок..."
    
    if [ -d "dist" ]; then
        rm -rf dist
    fi
    
    if [ -d "build" ]; then
        rm -rf build
    fi
    
    if [ -f "grpc_client.spec" ]; then
        rm grpc_client.spec
    fi
    
    success "Очистка завершена"
}

# Сборка приложения
build() {
    log "Сборка gRPC клиента..."
    
    # Создаем spec файл для PyInstaller
    cat > grpc_client.spec << 'SPEC_EOF'
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['grpc_client/__init__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('grpc_client/macos/entitlements/grpc_client.entitlements', 'entitlements'),
        ('grpc_client/macos/info/Info.plist', 'info'),
    ],
    hiddenimports=[
        'grpc_client.core.grpc_client',
        'grpc_client.core.types',
        'grpc_client.core.retry_manager',
        'grpc_client.core.health_checker',
        'grpc_client.core.connection_manager',
        'grpc_client.config.grpc_config',
        'grpc',
        'grpc.tools',
        'asyncio',
        'logging',
        'typing',
        'dataclasses',
        'enum',
        'time',
        'random',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='grpc_client',
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
    entitlements_file='grpc_client/macos/entitlements/grpc_client.entitlements',
    icon='grpc_client/macos/info/icon.icns',
)
SPEC_EOF
    
    # Запускаем PyInstaller
    pyinstaller grpc_client.spec --clean --noconfirm
    
    success "Сборка завершена"
}

# Подписание приложения
sign() {
    log "Подписание приложения..."
    
    # Проверяем наличие сертификата
    if [ -z "$CODESIGN_IDENTITY" ]; then
        warning "CODESIGN_IDENTITY не установлен, используем ad-hoc подпись"
        CODESIGN_IDENTITY="-"
    fi
    
    # Подписываем приложение
    codesign --force --sign "$CODESIGN_IDENTITY" \
        --entitlements grpc_client/macos/entitlements/grpc_client.entitlements \
        --options runtime \
        dist/grpc_client
    
    success "Подписание завершено"
}

# Создание PKG пакета
package() {
    log "Создание PKG пакета..."
    
    # Создаем временную директорию для пакета
    PKG_DIR="pkg_temp"
    mkdir -p "$PKG_DIR/usr/local/bin"
    
    # Копируем исполняемый файл
    cp dist/grpc_client "$PKG_DIR/usr/local/bin/"
    
    # Создаем PKG
    pkgbuild --root "$PKG_DIR" \
        --identifier com.nexy.grpc-client \
        --version 1.0.0 \
        --install-location /usr/local/bin \
        dist/grpc_client.pkg
    
    # Очищаем временную директорию
    rm -rf "$PKG_DIR"
    
    success "PKG пакет создан: dist/grpc_client.pkg"
}

# Основная функция
main() {
    log "🚀 Начало сборки gRPC клиента для macOS"
    
    check_dependencies
    clean
    build
    sign
    package
    
    success "🎉 Сборка завершена успешно!"
    log "Результат: dist/grpc_client.pkg"
}

# Запуск
main "$@"
