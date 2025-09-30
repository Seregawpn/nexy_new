#!/bin/bash

# Скрипт подписи и нотаризации input_processing для macOS
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

# Конфигурация
APP_NAME="Input Processing"
APP_PATH="dist/${APP_NAME}.app"
BUNDLE_ID="com.nexy.input.processing"
ENTITLEMENTS="entitlements/input_processing.entitlements"
INFO_PLIST="info/Info.plist"

# Проверка переменных окружения
check_environment() {
    log "Проверяем переменные окружения..."
    
    if [ -z "$DEVELOPER_ID" ]; then
        error "DEVELOPER_ID не установлен. Установите: export DEVELOPER_ID='Developer ID Application: Your Name (TEAM_ID)'"
        exit 1
    fi
    
    if [ -z "$APPLE_ID" ]; then
        error "APPLE_ID не установлен. Установите: export APPLE_ID='your@email.com'"
        exit 1
    fi
    
    if [ -z "$APP_PASSWORD" ]; then
        error "APP_PASSWORD не установлен. Установите: export APP_PASSWORD='app-specific-password'"
        exit 1
    fi
    
    if [ -z "$TEAM_ID" ]; then
        error "TEAM_ID не установлен. Установите: export TEAM_ID='5NKLL2CLB9'"
        exit 1
    fi
    
    success "Переменные окружения настроены"
}

# Проверка приложения
check_app() {
    log "Проверяем приложение..."
    
    if [ ! -d "$APP_PATH" ]; then
        error "Приложение не найдено: $APP_PATH"
        error "Сначала запустите: ./build_macos.sh"
        exit 1
    fi
    
    success "Приложение найдено: $APP_PATH"
}

# Подпись приложения
sign_app() {
    log "Подписываем приложение..."
    
    # Подписываем все исполняемые файлы
    find "$APP_PATH" -type f -name "*.dylib" -exec codesign --force --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS" {} \;
    find "$APP_PATH" -type f -name "*.so" -exec codesign --force --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS" {} \;
    find "$APP_PATH" -type f -name "*.framework" -exec codesign --force --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS" {} \;
    
    # Подписываем основное приложение
    codesign --force --sign "$DEVELOPER_ID" --entitlements "$ENTITLEMENTS" --options runtime "$APP_PATH"
    
    if [ $? -eq 0 ]; then
        success "Приложение подписано успешно"
    else
        error "Ошибка при подписи приложения"
        exit 1
    fi
}

# Проверка подписи
verify_signature() {
    log "Проверяем подпись..."
    
    codesign --verify --verbose "$APP_PATH"
    
    if [ $? -eq 0 ]; then
        success "Подпись проверена успешно"
    else
        error "Ошибка проверки подписи"
        exit 1
    fi
    
    # Показываем информацию о подписи
    log "Информация о подписи:"
    codesign --display --verbose "$APP_PATH"
}

# Создание архива для нотаризации
create_archive() {
    log "Создаем архив для нотаризации..."
    
    ARCHIVE_NAME="${APP_NAME}_${BUNDLE_ID}.zip"
    
    # Удаляем старый архив если есть
    if [ -f "$ARCHIVE_NAME" ]; then
        rm -f "$ARCHIVE_NAME"
    fi
    
    # Создаем архив
    ditto -c -k --keepParent "$APP_PATH" "$ARCHIVE_NAME"
    
    if [ $? -eq 0 ]; then
        success "Архив создан: $ARCHIVE_NAME"
        
        # Показываем размер
        size=$(du -sh "$ARCHIVE_NAME" | cut -f1)
        log "Размер архива: $size"
    else
        error "Ошибка создания архива"
        exit 1
    fi
}

# Отправка на нотаризацию
submit_notarization() {
    log "Отправляем на нотаризацию..."
    
    ARCHIVE_NAME="${APP_NAME}_${BUNDLE_ID}.zip"
    
    # Отправляем на нотаризацию
    xcrun notarytool submit "$ARCHIVE_NAME" \
        --apple-id "$APPLE_ID" \
        --password "$APP_PASSWORD" \
        --team-id "$TEAM_ID" \
        --wait
    
    if [ $? -eq 0 ]; then
        success "Нотаризация завершена успешно"
    else
        error "Ошибка нотаризации"
        exit 1
    fi
}

# Прикрепление тикета нотаризации
staple_notarization() {
    log "Прикрепляем тикет нотаризации..."
    
    xcrun stapler staple "$APP_PATH"
    
    if [ $? -eq 0 ]; then
        success "Тикет нотаризации прикреплен"
    else
        error "Ошибка прикрепления тикета"
        exit 1
    fi
}

# Проверка финального результата
verify_final() {
    log "Проверяем финальный результат..."
    
    # Проверяем подпись
    codesign --verify --verbose "$APP_PATH"
    
    # Проверяем нотаризацию
    xcrun stapler validate "$APP_PATH"
    
    if [ $? -eq 0 ]; then
        success "Приложение готово к распространению!"
        log "Путь к приложению: $APP_PATH"
    else
        error "Ошибка финальной проверки"
        exit 1
    fi
}

# Создание PKG
create_pkg() {
    log "Создаем PKG пакет..."
    
    PKG_NAME="${APP_NAME}_${BUNDLE_ID}.pkg"
    
    # Создаем PKG
    pkgbuild --root "$APP_PATH" \
        --identifier "$BUNDLE_ID" \
        --version "1.0.0" \
        --install-location "/Applications" \
        --sign "$DEVELOPER_ID" \
        "$PKG_NAME"
    
    if [ $? -eq 0 ]; then
        success "PKG пакет создан: $PKG_NAME"
        
        # Показываем размер
        size=$(du -sh "$PKG_NAME" | cut -f1)
        log "Размер PKG: $size"
    else
        error "Ошибка создания PKG"
        exit 1
    fi
}

# Основная функция
main() {
    log "Начинаем подпись и нотаризацию input_processing..."
    
    check_environment
    check_app
    sign_app
    verify_signature
    create_archive
    submit_notarization
    staple_notarization
    verify_final
    create_pkg
    
    success "Подпись и нотаризация завершены успешно!"
    log "Приложение готово к распространению: $APP_PATH"
    log "PKG пакет: ${APP_NAME}_${BUNDLE_ID}.pkg"
}

# Запуск
main "$@"
