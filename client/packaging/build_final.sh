#!/bin/bash

# 📦 Nexy AI Assistant - Финальная упаковка и подпись (ОБНОВЛЕНО 24.09.2025)
# Использование: ./packaging/build_final.sh

set -e  # Остановить при ошибку

# ГЛОБАЛЬНАЯ ЗАЩИТА ОТ EXTENDED ATTRIBUTES
export COPYFILE_DISABLE=1  # Отключает AppleDouble (._*) и resource fork при copy/tar/rsync

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
IDENTITY="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
INSTALLER_IDENTITY="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
ENTITLEMENTS="packaging/entitlements.plist"
APP_NAME="Nexy"
BUNDLE_ID="com.nexy.assistant"
VERSION="1.0.0"

# Пути
CLIENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$CLIENT_DIR/dist"
CLEAN_APP="/tmp/${APP_NAME}CleanFinal.app"

echo -e "${BLUE}🚀 Начинаем финальную упаковку Nexy AI Assistant${NC}"
echo "Рабочая директория: $CLIENT_DIR"

# Функция для логирования
log() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Функция безопасного копирования (без extended attributes)
safe_copy() {
    # $1 = src, $2 = dst
    /usr/bin/ditto --noextattr --noqtn "$1" "$2"
}

# Функция проверки и очистки extended attributes
clean_xattrs() {
    local app_path="$1"
    local stage="$2"
    
    # Жёстко чистим
    xattr -cr "$app_path" || true
    find "$app_path" -name '._*' -type f -delete || true
    find "$app_path" -name '.DS_Store' -type f -delete || true
    
    # Проверяем и валим сборку, если что-то осталось
    if xattr -pr com.apple.FinderInfo "$app_path" 2>/dev/null | grep -q .; then
        error "FinderInfo вернулся на этапе $stage"
    fi
    if xattr -pr com.apple.ResourceFork "$app_path" 2>/dev/null | grep -q .; then
        error "ResourceFork вернулся на этапе $stage"
    fi
    if find "$app_path" -name '._*' | grep -q .; then
        error "AppleDouble (._*) файлы найдены на этапе $stage"
    fi
}

warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

# Функция для проверки команд
check_command() {
    if ! command -v "$1" &> /dev/null; then
        error "Команда '$1' не найдена. Установите необходимые инструменты."
    fi
}

# Проверяем необходимые команды
echo -e "${BLUE}🔍 Проверяем необходимые инструменты...${NC}"
check_command "python3"
check_command "codesign"
check_command "pkgbuild"
check_command "productbuild"
check_command "productsign"
check_command "ditto"
check_command "xattr"

# Проверяем PyInstaller
if ! python3 -m PyInstaller --version &> /dev/null; then
    error "PyInstaller не найден. Установите: pip install pyinstaller"
fi

# Проверяем сертификаты
echo -e "${BLUE}🔍 Проверяем сертификаты...${NC}"
if ! security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    error "Developer ID Application сертификат не найден"
fi

if ! security find-identity -v -p basic | grep -q "Developer ID Installer"; then
    error "Developer ID Installer сертификат не найден"
fi

# Шаг 1: Очистка и сборка
echo -e "${BLUE}🧹 Шаг 1: Очистка и сборка${NC}"
cd "$CLIENT_DIR"

log "Очищаем старые файлы..."
rm -rf dist/ build/ *.pyc __pycache__/
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

log "Собираем приложение с PyInstaller..."
python3 -m PyInstaller packaging/Nexy.spec --noconfirm --clean

if [ ! -d "dist/$APP_NAME.app" ]; then
    error "Сборка не удалась. Проверьте логи PyInstaller."
fi

log "Сборка завершена успешно"

# Шаг 2: Создание ЧИСТОЙ копии (КРИТИЧНО!)
echo -e "${BLUE}📋 Шаг 2: Создание чистой копии${NC}"

log "Создаем полностью чистую копию без extended attributes..."
rm -rf "$CLEAN_APP"
safe_copy "dist/$APP_NAME.app" "$CLEAN_APP"

log "Проверяем и очищаем extended attributes..."
clean_xattrs "$CLEAN_APP" "создание чистой копии"
log "Extended attributes успешно очищены"

# Шаг 3: Подпись приложения (ПРАВИЛЬНЫЙ ПОРЯДОК!)
echo -e "${BLUE}🔐 Шаг 3: Подпись приложения${NC}"

log "Удаляем старые подписи..."
codesign --remove-signature "$CLEAN_APP" 2>/dev/null || true
# Удаляем подписи со всех исполняемых файлов в Contents (включая Resources)
find "$CLEAN_APP/Contents" -type f -perm -111 -exec codesign --remove-signature {} \; 2>/dev/null || true

log "Подписываем вложенные Mach-O файлы (СНАЧАЛА!)..."
while IFS= read -r -d '' BIN; do
    if file -b "$BIN" | grep -q "Mach-O"; then
        echo "  Подписываем: $BIN"
        codesign --force --timestamp --options=runtime \
            --entitlements "$ENTITLEMENTS" \
            --sign "$IDENTITY" "$BIN"
    fi
done < <(find "$CLEAN_APP/Contents" -type f -perm -111 -print0 2>/dev/null)

# Явно подписываем встроенный ffmpeg, если присутствует (Resources)
FFMPEG_BIN="$CLEAN_APP/Contents/Resources/resources/ffmpeg/ffmpeg"
if [ -f "$FFMPEG_BIN" ]; then
    echo "  Подписываем встроенный ffmpeg: $FFMPEG_BIN"
    codesign --force --timestamp --options=runtime \
        --entitlements "$ENTITLEMENTS" \
        --sign "$IDENTITY" "$FFMPEG_BIN"
fi

log "Подписываем весь бандл (ПОТОМ!)..."
codesign --force --timestamp --options=runtime \
    --entitlements "$ENTITLEMENTS" \
    --sign "$IDENTITY" "$CLEAN_APP"

# Шаг 4: Проверка подписи приложения
echo -e "${BLUE}🔍 Шаг 4: Проверка подписи приложения${NC}"

log "Проверяем подпись приложения..."
if codesign --verify --deep --strict --verbose=2 "$CLEAN_APP"; then
    log "Подпись приложения корректна"
else
    error "Подпись приложения не прошла проверку"
fi

log "Проверяем spctl..."
if spctl --assess --type execute --verbose "$CLEAN_APP" 2>/dev/null; then
    log "spctl проверка прошла успешно"
else
    warn "spctl проверка не прошла (нормально для непронотаризованного приложения)"
fi

# Шаг 5: Нотаризация приложения
echo -e "${BLUE}📤 Шаг 5: Нотаризация приложения${NC}"

log "Создаем ZIP для нотаризации..."
ditto -c -k --noextattr --noqtn "$CLEAN_APP" "$DIST_DIR/$APP_NAME-app-for-notarization.zip"

log "Отправляем приложение на нотаризацию..."
xcrun notarytool submit "$DIST_DIR/$APP_NAME-app-for-notarization.zip" \
    --keychain-profile "nexy-notary" \
    --apple-id "seregawpn@gmail.com" \
    --wait

log "Прикрепляем нотаризационную печать..."
xcrun stapler staple "$CLEAN_APP"

# Шаг 6: Создание PKG (ПРАВИЛЬНЫЙ СПОСОБ!)
echo -e "${BLUE}📦 Шаг 6: Создание PKG${NC}"

log "Создаем временную папку для PKG..."
rm -rf /tmp/nexy_pkg_clean_final
mkdir -p /tmp/nexy_pkg_clean_final

log "Копируем нотаризованное приложение..."
safe_copy "$CLEAN_APP" /tmp/nexy_pkg_clean_final/$APP_NAME.app
clean_xattrs "/tmp/nexy_pkg_clean_final/$APP_NAME.app" "создание PKG"

log "Создаем component PKG..."
pkgbuild --root /tmp/nexy_pkg_clean_final \
    --identifier "$BUNDLE_ID" \
    --version "$VERSION" \
    --install-location /Applications \
    "$DIST_DIR/$APP_NAME-raw.pkg"

log "Создаем distribution PKG..."
productbuild --package-path "$DIST_DIR" \
    --distribution packaging/distribution.xml \
    "$DIST_DIR/$APP_NAME-distribution.pkg"

log "Подписываем PKG правильным сертификатом..."
productsign --sign "$INSTALLER_IDENTITY" \
    "$DIST_DIR/$APP_NAME-distribution.pkg" \
    "$DIST_DIR/$APP_NAME-signed.pkg"

# Шаг 7: Нотаризация PKG
echo -e "${BLUE}📤 Шаг 7: Нотаризация PKG${NC}"

log "Отправляем PKG на нотаризацию..."
xcrun notarytool submit "$DIST_DIR/$APP_NAME-signed.pkg" \
    --keychain-profile "nexy-notary" \
    --apple-id "seregawpn@gmail.com" \
    --wait

log "Прикрепляем нотаризационную печать к PKG..."
xcrun stapler staple "$DIST_DIR/$APP_NAME-signed.pkg"

# Шаг 8: Финальная проверка
echo -e "${BLUE}✅ Шаг 8: Финальная проверка${NC}"

log "Копируем финальное приложение в dist..."
safe_copy "$CLEAN_APP" "$DIST_DIR/$APP_NAME-final.app"
clean_xattrs "$DIST_DIR/$APP_NAME-final.app" "финальная копия"

echo "=== ФИНАЛЬНАЯ ПРОВЕРКА ВСЕХ АРТЕФАКТОВ ==="
echo ""

echo "1. ПРИЛОЖЕНИЕ:"
if codesign --verify --deep --strict --verbose=2 "$DIST_DIR/$APP_NAME-final.app"; then
    log "Подпись приложения корректна"
else
    error "Подпись приложения не прошла проверку"
fi

if xcrun stapler validate "$DIST_DIR/$APP_NAME-final.app"; then
    log "Нотаризация приложения корректна"
else
    error "Нотаризация приложения не прошла проверку"
fi

echo ""
echo "2. PKG:"
if pkgutil --check-signature "$DIST_DIR/$APP_NAME-signed.pkg"; then
    log "Подпись PKG корректна"
else
    error "Подпись PKG не прошла проверку"
fi

if xcrun stapler validate "$DIST_DIR/$APP_NAME-signed.pkg"; then
    log "Нотаризация PKG корректна"
else
    error "Нотаризация PKG не прошла проверку"
fi

echo ""
echo "3. ПРОВЕРКА СОДЕРЖИМОГО PKG:"
pkgutil --expand "$DIST_DIR/$APP_NAME-signed.pkg" /tmp/nexy_final_check
tar -xf /tmp/nexy_final_check/Payload -C /tmp/nexy_final_extracted
APPLE_DOUBLE_COUNT=$(find /tmp/nexy_final_extracted -name '._*' -type f | wc -l)
echo "AppleDouble файлов: $APPLE_DOUBLE_COUNT"

if codesign --verify --deep --strict --verbose=2 /tmp/nexy_final_extracted/$APP_NAME.app; then
    log "Приложение из PKG корректно подписано"
else
    error "Приложение из PKG не прошло проверку подписи"
fi

# Очистка временных файлов
log "Очищаем временные файлы..."
rm -rf /tmp/nexy_pkg_clean_final /tmp/nexy_final_check /tmp/nexy_final_extracted

echo ""
echo -e "${BLUE}🔄 Обновляем финальную копию без extended attributes...${NC}"
rm -rf "$DIST_DIR/$APP_NAME-final.app"
safe_copy "$CLEAN_APP" "$DIST_DIR/$APP_NAME-final.app"
clean_xattrs "$DIST_DIR/$APP_NAME-final.app" "финальная копия"

echo -e "${GREEN}🎉 УПАКОВКА ЗАВЕРШЕНА УСПЕШНО!${NC}"
echo -e "${BLUE}📁 Результаты:${NC}"
echo "  • Приложение: $DIST_DIR/$APP_NAME-final.app"
echo "  • PKG: $DIST_DIR/$APP_NAME-signed.pkg"
echo "  • Размер приложения: $(du -h "$DIST_DIR/$APP_NAME-final.app" | cut -f1)"
echo "  • Размер PKG: $(du -h "$DIST_DIR/$APP_NAME-signed.pkg" | cut -f1)"
echo ""
echo -e "${YELLOW}📋 Следующие шаги:${NC}"
echo "  1. Протестируйте приложение: $DIST_DIR/$APP_NAME-final.app"
echo "  2. Установите PKG: $DIST_DIR/$APP_NAME-signed.pkg"
echo "  3. Распространяйте PKG пользователям"
echo ""
echo -e "${GREEN}✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!${NC}"
