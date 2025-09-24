#!/bin/bash

# 📦 Nexy AI Assistant - Автоматизированная упаковка и подпись
# Использование: ./packaging/build_and_sign.sh

set -e  # Остановить при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
IDENTITY="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
ENTITLEMENTS="packaging/entitlements.plist"
APP_NAME="Nexy"
BUNDLE_ID="com.nexy.assistant"
VERSION="1.0.0"

# Пути
CLIENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="$CLIENT_DIR/dist"
CLEAN_APP="/tmp/${APP_NAME}Clean.app"
TEMP_PKG="/tmp/nexy_pkg"

echo -e "${BLUE}🚀 Начинаем упаковку Nexy AI Assistant${NC}"
echo "Рабочая директория: $CLIENT_DIR"

# Функция для логирования
log() {
    echo -e "${GREEN}✅ $1${NC}"
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
check_command "ditto"
check_command "xattr"

# Проверяем PyInstaller через python3 -m
if ! python3 -m PyInstaller --version &> /dev/null; then
    error "PyInstaller не найден. Установите: pip install pyinstaller"
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

# Шаг 2: Создание чистой копии
echo -e "${BLUE}📋 Шаг 2: Создание чистой копии${NC}"

log "Создаем чистую копию без extended attributes..."
rm -rf "$CLEAN_APP"
ditto --noextattr --noqtn "dist/$APP_NAME.app" "$CLEAN_APP"

log "Дополнительная очистка extended attributes..."
xattr -cr "$CLEAN_APP" || true
find "$CLEAN_APP" -name '._*' -type f -delete

log "Проверяем очистку extended attributes..."
if xattr -lr "$CLEAN_APP" | grep -q "com.apple.FinderInfo\|com.apple.ResourceFork\|com.apple.quarantine"; then
    warn "Обнаружены остаточные extended attributes, но продолжаем..."
else
    log "Extended attributes успешно очищены"
fi

# Шаг 3: Подпись приложения
echo -e "${BLUE}🔐 Шаг 3: Подпись приложения${NC}"

log "Удаляем старые подписи..."
codesign --remove-signature "$CLEAN_APP" 2>/dev/null || true
find "$CLEAN_APP/Contents" -type f -perm -111 -exec codesign --remove-signature {} \; 2>/dev/null || true

log "Подписываем вложенные Mach-O файлы..."
while IFS= read -r -d '' BIN; do
    if file -b "$BIN" | grep -q "Mach-O"; then
        echo "  Подписываем: $BIN"
        codesign --force --timestamp --options=runtime \
            --entitlements "$ENTITLEMENTS" \
            --sign "$IDENTITY" "$BIN"
    fi
done < <(find "$CLEAN_APP/Contents/Frameworks" "$CLEAN_APP/Contents/MacOS" -type f -perm -111 -print0 2>/dev/null)

log "Подписываем весь бандл..."
codesign --force --timestamp --options=runtime \
    --entitlements "$ENTITLEMENTS" \
    --sign "$IDENTITY" "$CLEAN_APP"

# Шаг 4: Проверка подписи
echo -e "${BLUE}🔍 Шаг 4: Проверка подписи${NC}"

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
    warn "spctl проверка не прошла (это нормально для непронотаризованного приложения)"
fi

log "Проверяем entitlements..."
codesign -d --entitlements - "$CLEAN_APP"

# Шаг 5: Создание PKG
echo -e "${BLUE}📦 Шаг 5: Создание PKG${NC}"

log "Создаем временную папку для PKG..."
rm -rf "$TEMP_PKG"
mkdir -p "$TEMP_PKG"
cp -R "$CLEAN_APP" "$TEMP_PKG/$APP_NAME.app"

log "Создаем component PKG..."
pkgbuild --root "$TEMP_PKG" \
    --identifier "$BUNDLE_ID" \
    --version "$VERSION" \
    --install-location /Applications \
    "$DIST_DIR/$APP_NAME-raw.pkg"

log "Создаем distribution PKG..."
productbuild --package-path "$DIST_DIR" \
    --distribution packaging/distribution.xml \
    "$DIST_DIR/$APP_NAME-signed.pkg"

log "Подписываем PKG..."
codesign --force --timestamp --deep \
    --sign "$IDENTITY" \
    "$DIST_DIR/$APP_NAME-signed.pkg"

# Шаг 6: Финальная проверка
echo -e "${BLUE}✅ Шаг 6: Финальная проверка${NC}"

log "Копируем подписанное приложение в dist..."
cp -R "$CLEAN_APP" "$DIST_DIR/$APP_NAME-signed.app"

log "Проверяем финальные файлы..."
echo "=== Подписанное приложение ==="
ls -la "$DIST_DIR/$APP_NAME-signed.app/Contents/MacOS/$APP_NAME"

echo "=== PKG файл ==="
ls -la "$DIST_DIR/$APP_NAME-signed.pkg"

echo "=== Проверка подписи приложения ==="
codesign -v "$DIST_DIR/$APP_NAME-signed.app"

echo "=== Проверка подписи PKG ==="
codesign -v "$DIST_DIR/$APP_NAME-signed.pkg"

# Очистка временных файлов
log "Очищаем временные файлы..."
rm -rf "$CLEAN_APP" "$TEMP_PKG"

echo -e "${GREEN}🎉 Упаковка завершена успешно!${NC}"
echo -e "${BLUE}📁 Результаты:${NC}"
echo "  • Приложение: $DIST_DIR/$APP_NAME-signed.app"
echo "  • PKG: $DIST_DIR/$APP_NAME-signed.pkg"
echo ""
echo -e "${YELLOW}📋 Следующие шаги:${NC}"
echo "  1. Протестируйте приложение: $DIST_DIR/$APP_NAME-signed.app"
echo "  2. Для нотаризации используйте: xcrun notarytool submit"
echo "  3. Для установки используйте: $DIST_DIR/$APP_NAME-signed.pkg"
