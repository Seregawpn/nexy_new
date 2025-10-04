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
CLEAN_APP="/tmp/${APP_NAME}.app"

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
    # Дополнительная очистка после копирования
    xattr -cr "$2" 2>/dev/null || true
    find "$2" -name '._*' -delete 2>/dev/null || true
    find "$2" -name '.DS_Store' -delete 2>/dev/null || true
}

# Функция проверки и очистки extended attributes
clean_xattrs() {
    local app_path="$1"
    local stage="$2"
    
    # Агрессивная очистка extended attributes
    xattr -cr "$app_path" || true
    find "$app_path" -name '._*' -type f -delete || true
    find "$app_path" -name '.DS_Store' -type f -delete || true
    
    # Дополнительная очистка конкретных атрибутов
    xattr -d com.apple.FinderInfo "$app_path" 2>/dev/null || true
    xattr -d com.apple.ResourceFork "$app_path" 2>/dev/null || true
    xattr -d com.apple.quarantine "$app_path" 2>/dev/null || true
    xattr -d com.apple.metadata:kMDItemWhereFroms "$app_path" 2>/dev/null || true
    xattr -d com.apple.metadata:kMDItemDownloadedDate "$app_path" 2>/dev/null || true
    
    # Рекурсивная очистка всех файлов
    find "$app_path" -type f -exec xattr -c {} \; 2>/dev/null || true
    find "$app_path" -type d -exec xattr -c {} \; 2>/dev/null || true
    
    # Проверяем и предупреждаем, но не валим сборку
    if xattr -pr com.apple.FinderInfo "$app_path" 2>/dev/null | grep -q .; then
        warn "FinderInfo остался на этапе $stage (нормально для macOS)"
    fi
    if xattr -pr com.apple.ResourceFork "$app_path" 2>/dev/null | grep -q .; then
        warn "ResourceFork остался на этапе $stage (нормально для macOS)"
    fi
    if find "$app_path" -name '._*' | grep -q .; then
        warn "AppleDouble (._*) файлы найдены на этапе $stage (нормально для macOS)"
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
if ! command -v pyinstaller &> /dev/null; then
    error "PyInstaller не найден. Установите: brew install pyinstaller"
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
# Безопасная очистка: удаляем содержимое, а не сами директории
rm -rf dist/* dist/.* build/* build/.* *.pyc __pycache__/ 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

log "Собираем приложение с PyInstaller..."
# Активируем venv для использования правильных версий пакетов (protobuf 6.32.1)
source "$CLIENT_DIR/venv/bin/activate"
pyinstaller packaging/Nexy.spec --noconfirm --clean

if [ ! -d "dist/$APP_NAME.app" ]; then
    error "Сборка не удалась. Проверьте логи PyInstaller."
fi

log "Сборка завершена успешно"

    # Шаг 2: Создание ЧИСТОЙ копии (КРИТИЧНО!)
    echo -e "${BLUE}📋 Шаг 2: Создание чистой копии${NC}"
    
    log "Очищаем исходное приложение от extended attributes..."
    clean_xattrs "dist/$APP_NAME.app" "исходное приложение"
    
    log "Создаем полностью чистую копию без extended attributes..."
    rm -rf "$CLEAN_APP"
    safe_copy "dist/$APP_NAME.app" "$CLEAN_APP"
    
    log "Проверяем и очищаем extended attributes в копии..."
    clean_xattrs "$CLEAN_APP" "создание чистой копии"
    
    # Дополнительная агрессивная очистка
    log "Выполняем дополнительную очистку extended attributes..."
    xattr -d com.apple.FinderInfo "$CLEAN_APP" 2>/dev/null || true
    xattr -d com.apple.ResourceFork "$CLEAN_APP" 2>/dev/null || true
    xattr -d com.apple.quarantine "$CLEAN_APP" 2>/dev/null || true
    xattr -cr "$CLEAN_APP" || true
    find "$CLEAN_APP" -name '._*' -delete || true
    find "$CLEAN_APP" -name '.DS_Store' -delete || true
    
    log "Extended attributes успешно очищены"

# Шаг 3: Подпись приложения (ПРАВИЛЬНЫЙ ПОРЯДОК!)
echo -e "${BLUE}🔐 Шаг 3: Подпись приложения${NC}"

log "Удаляем старые подписи..."
codesign --remove-signature "$CLEAN_APP" 2>/dev/null || true
# Удаляем подписи со всех исполняемых файлов в Contents (включая Resources)
find "$CLEAN_APP/Contents" -type f -perm -111 -exec codesign --remove-signature {} \; 2>/dev/null || true

log "Подписываем вложенные Mach-O файлы (СНАЧАЛА!)..."
# Подписываем все вложенные библиотеки БЕЗ entitlements
while IFS= read -r -d '' BIN; do
    # Пропускаем главный executable - его подпишем потом
    if [[ "$BIN" == *"/Contents/MacOS/$APP_NAME" ]]; then
        continue
    fi
    if file -b "$BIN" | grep -q "Mach-O"; then
        echo "  Подписываем библиотеку: $(basename $BIN)"
        codesign --force --timestamp --options=runtime \
            --sign "$IDENTITY" "$BIN" || true
    fi
done < <(find "$CLEAN_APP/Contents" -type f -perm -111 -print0 2>/dev/null)

# Явно подписываем встроенный ffmpeg, если присутствует (Frameworks)
FFMPEG_BIN="$CLEAN_APP/Contents/Frameworks/resources/ffmpeg/ffmpeg"
if [ -f "$FFMPEG_BIN" ]; then
    echo "  Подписываем встроенный ffmpeg: $FFMPEG_BIN"
    codesign --force --timestamp --options=runtime \
        --sign "$IDENTITY" "$FFMPEG_BIN" || true
fi

# Подписываем SwitchAudioSource если присутствует
SWITCHAUDIO_BIN="$CLEAN_APP/Contents/Resources/resources/audio/SwitchAudioSource"
if [ -f "$SWITCHAUDIO_BIN" ]; then
    echo "  Подписываем SwitchAudioSource: $SWITCHAUDIO_BIN"
    codesign --force --timestamp --options=runtime \
        --sign "$IDENTITY" "$SWITCHAUDIO_BIN" || true
fi

log "Подписываем главный executable с entitlements..."
MAIN_EXE="$CLEAN_APP/Contents/MacOS/$APP_NAME"
codesign --force --timestamp --options=runtime \
    --entitlements "$ENTITLEMENTS" \
    --sign "$IDENTITY" "$MAIN_EXE"

log "Подписываем весь бандл (ФИНАЛ!)..."
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

# Шаг 6: Создание DMG
echo -e "${BLUE}💿 Шаг 6: Создание DMG${NC}"

DMG_PATH="$DIST_DIR/$APP_NAME.dmg"
TEMP_DMG="$DIST_DIR/$APP_NAME-temp.dmg"
VOLUME_NAME="$APP_NAME"

log "Создаем временный DMG..."
APP_SIZE_KB=$(du -sk "$CLEAN_APP" | awk '{print $1}')
DMG_SIZE_MB=$(( APP_SIZE_KB/1024 + 200 ))

hdiutil create -volname "$VOLUME_NAME" -srcfolder "$CLEAN_APP" \
    -fs HFS+ -format UDRW -size "${DMG_SIZE_MB}m" "$TEMP_DMG"

MOUNT_DIR="/Volumes/$VOLUME_NAME"
hdiutil attach "$TEMP_DMG" -readwrite -noverify -noautoopen >/dev/null
ln -s /Applications "$MOUNT_DIR/Applications" || true
hdiutil detach "$MOUNT_DIR" >/dev/null

log "Финализируем DMG..."
rm -f "$DMG_PATH"
hdiutil convert "$TEMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH" >/dev/null
rm -f "$TEMP_DMG"

log "DMG создан: $DMG_PATH"

# Шаг 7: Нотаризация DMG
echo -e "${BLUE}📤 Шаг 7: Нотаризация DMG${NC}"

log "Отправляем DMG на нотаризацию..."
xcrun notarytool submit "$DMG_PATH" \
    --keychain-profile "nexy-notary" \
    --apple-id "seregawpn@gmail.com" \
    --wait

log "Прикрепляем нотаризационную печать к DMG..."
xcrun stapler staple "$DMG_PATH"

# Шаг 8: Создание PKG (ПРАВИЛЬНЫЙ СПОСОБ!)
echo -e "${BLUE}📦 Шаг 8: Создание PKG${NC}"

log "Создаем временную папку для PKG..."
rm -rf /tmp/nexy_pkg_clean_final
mkdir -p /tmp/nexy_pkg_clean_final

log "Копируем нотаризованное приложение в правильную структуру..."
mkdir -p /tmp/nexy_pkg_clean_final/Applications
safe_copy "$CLEAN_APP" /tmp/nexy_pkg_clean_final/Applications/$APP_NAME.app
clean_xattrs "/tmp/nexy_pkg_clean_final/Applications/$APP_NAME.app" "создание PKG"

log "Создаем component PKG..."
# Устанавливаем в корень, так как приложение уже в папке Applications/
INSTALL_LOCATION="/"
log "Устанавливаем в: $INSTALL_LOCATION (приложение уже в Applications/)"

pkgbuild --root /tmp/nexy_pkg_clean_final \
    --identifier "${BUNDLE_ID}.pkg" \
    --version "$VERSION" \
    --install-location "$INSTALL_LOCATION" \
    "$DIST_DIR/$APP_NAME-raw.pkg"

log "Создаем distribution PKG..."
productbuild --package-path "$DIST_DIR" \
    --distribution packaging/distribution.xml \
    "$DIST_DIR/$APP_NAME-distribution.pkg"

log "Подписываем PKG правильным сертификатом..."
productsign --sign "$INSTALLER_IDENTITY" \
    "$DIST_DIR/$APP_NAME-distribution.pkg" \
    "$DIST_DIR/$APP_NAME.pkg"

# Шаг 9: Нотаризация PKG
echo -e "${BLUE}📤 Шаг 9: Нотаризация PKG${NC}"

log "Отправляем PKG на нотаризацию..."
xcrun notarytool submit "$DIST_DIR/$APP_NAME.pkg" \
    --keychain-profile "nexy-notary" \
    --apple-id "seregawpn@gmail.com" \
    --wait

log "Прикрепляем нотаризационную печать к PKG..."
xcrun stapler staple "$DIST_DIR/$APP_NAME.pkg"

    # Шаг 10: Финальная проверка
    echo -e "${BLUE}✅ Шаг 10: Финальная проверка${NC}"
    
    log "Копируем финальное приложение в dist..."
    safe_copy "$CLEAN_APP" "$DIST_DIR/$APP_NAME-final.app"
    clean_xattrs "$DIST_DIR/$APP_NAME-final.app" "финальная копия"
    
    # Дополнительная агрессивная очистка перед финальной проверкой
    log "Выполняем дополнительную очистку extended attributes..."
    xattr -d com.apple.FinderInfo "$DIST_DIR/$APP_NAME-final.app" 2>/dev/null || true
    xattr -d com.apple.ResourceFork "$DIST_DIR/$APP_NAME-final.app" 2>/dev/null || true
    xattr -d com.apple.quarantine "$DIST_DIR/$APP_NAME-final.app" 2>/dev/null || true
    xattr -d com.apple.metadata:kMDItemWhereFroms "$DIST_DIR/$APP_NAME-final.app" 2>/dev/null || true
    xattr -d com.apple.metadata:kMDItemDownloadedDate "$DIST_DIR/$APP_NAME-final.app" 2>/dev/null || true
    xattr -cr "$DIST_DIR/$APP_NAME-final.app" || true
    find "$DIST_DIR/$APP_NAME-final.app" -name '._*' -delete || true
    find "$DIST_DIR/$APP_NAME-final.app" -name '.DS_Store' -delete || true
    find "$DIST_DIR/$APP_NAME-final.app" -type f -exec xattr -c {} \; 2>/dev/null || true
    find "$DIST_DIR/$APP_NAME-final.app" -type d -exec xattr -c {} \; 2>/dev/null || true

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
if pkgutil --check-signature "$DIST_DIR/$APP_NAME.pkg"; then
    log "Подпись PKG корректна"
else
    error "Подпись PKG не прошла проверку"
fi

if xcrun stapler validate "$DIST_DIR/$APP_NAME.pkg"; then
    log "Нотаризация PKG корректна"
else
    error "Нотаризация PKG не прошла проверку"
fi

echo ""
echo "3. ПРОВЕРКА СОДЕРЖИМОГО PKG:"
pkgutil --expand "$DIST_DIR/$APP_NAME.pkg" /tmp/nexy_final_check

# Находим вложенный component PKG внутри distribution PKG
NESTED_PKG_DIR=$(find /tmp/nexy_final_check -maxdepth 2 -type d -name "*.pkg" | head -n1)
if [ -z "$NESTED_PKG_DIR" ]; then
    error "Не удалось найти вложенный .pkg внутри distribution PKG"
fi

# Проверяем install-location в PackageInfo
if [ ! -f "$NESTED_PKG_DIR/PackageInfo" ]; then
    error "PackageInfo не найден во вложенном PKG"
fi

PKG_INSTALL_LOCATION=$(grep -o 'install-location="[^"]*"' "$NESTED_PKG_DIR/PackageInfo" | sed 's/install-location="\(.*\)"/\1/')
echo "install-location во вложенном PKG: ${PKG_INSTALL_LOCATION}"
if [ "$PKG_INSTALL_LOCATION" != "/" ]; then
    error "Неверный install-location: ${PKG_INSTALL_LOCATION}. Ожидается: /"
fi

# Распаковываем Payload из вложенного PKG
mkdir -p /tmp/nexy_final_extracted
if [ -f "$NESTED_PKG_DIR/Payload" ]; then
    tar -xf "$NESTED_PKG_DIR/Payload" -C /tmp/nexy_final_extracted
else
    error "Payload не найден во вложенном PKG"
fi

APPLE_DOUBLE_COUNT=$(find /tmp/nexy_final_extracted -name '._*' -type f | wc -l)
echo "AppleDouble файлов: $APPLE_DOUBLE_COUNT"

# Ожидаем, что приложение находится по пути Applications/Nexy.app в Payload
if [ ! -d "/tmp/nexy_final_extracted/Applications/$APP_NAME.app" ]; then
    error "В Payload отсутствует Applications/$APP_NAME.app"
fi

if codesign --verify --deep --strict --verbose=2 /tmp/nexy_final_extracted/Applications/$APP_NAME.app; then
    log "Приложение из PKG корректно подписано"
else
    error "Приложение из PKG не прошло проверку подписи"
fi

# Очистка временных файлов
log "Очищаем временные файлы..."
rm -rf /tmp/nexy_pkg_clean_final /tmp/nexy_final_check /tmp/nexy_final_extracted

echo ""
echo -e "${BLUE}🧹 Чистим лишние артефакты, оставляем только PKG и DMG...${NC}"
# Удаляем промежуточные и лишние артефакты из dist
rm -f "$DIST_DIR/$APP_NAME-app-for-notarization.zip" 2>/dev/null || true
rm -f "$DIST_DIR/$APP_NAME-raw.pkg" 2>/dev/null || true
rm -f "$DIST_DIR/$APP_NAME-distribution.pkg" 2>/dev/null || true
rm -rf "$DIST_DIR/$APP_NAME-final.app" 2>/dev/null || true
rm -rf "$DIST_DIR/$APP_NAME.app" 2>/dev/null || true

echo -e "${GREEN}🎉 УПАКОВКА ЗАВЕРШЕНА УСПЕШНО!${NC}"
echo -e "${BLUE}📁 Результаты:${NC}"
echo "  • PKG: $DIST_DIR/$APP_NAME.pkg"
echo "  • DMG: $DMG_PATH"
echo "  • Размер PKG: $(du -h "$DIST_DIR/$APP_NAME.pkg" | cut -f1)"
echo "  • Размер DMG: $(du -h "$DMG_PATH" | cut -f1)"
echo ""
echo -e "${YELLOW}📋 Следующие шаги:${NC}"
echo "  1. Установите PKG: open $DIST_DIR/$APP_NAME.pkg (или: sudo installer -pkg $DIST_DIR/$APP_NAME.pkg -target /)"
echo "  2. Либо используйте DMG для drag-and-drop: $DMG_PATH"
echo "  3. Распространяйте PKG/DMG пользователям"
echo ""
echo -e "${GREEN}✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!${NC}"
