#!/bin/bash
set -euo pipefail

echo "🚀 ИСПРАВЛЕННАЯ СБОРКА NEXY AI ASSISTANT"
echo "========================================"
echo "Версия: 1.71.0 с исправленными разрешениями"
echo ""

VERSION="1.71.0"
BUILD="171"
TEAM_ID="5NKLL2CLB9"

# Проверяем архитектуру
if [ "$(uname -m)" != "arm64" ]; then
    echo "❌ Требуется сборка на Apple Silicon (arm64)"
    exit 1
fi

# Проверяем сертификаты
echo "🔍 Проверка сертификатов..."
if ! security find-identity -p codesigning -v | grep -q "Developer ID Application.*$TEAM_ID"; then
    echo "❌ Сертификат приложения не найден"
    security find-identity -p codesigning -v
    exit 1
fi

if ! security find-identity -p codesigning -v | grep -q "Developer ID Installer.*$TEAM_ID"; then
    echo "❌ Сертификат инсталлятора не найден"
    security find-identity -p codesigning -v
    exit 1
fi

echo "✅ Сертификаты найдены"
echo ""

# ЭТАП 1: Сборка приложения
echo "1️⃣ СБОРКА ПРИЛОЖЕНИЯ"
echo "===================="

BUILD_DIR="/tmp/nexy_fixed_$(date +%s)"
mkdir -p "$BUILD_DIR"
echo "📁 Временная папка: $BUILD_DIR"

echo "📋 Копирование проекта..."
cp -R . "$BUILD_DIR/"
cd "$BUILD_DIR"

echo "🔨 PyInstaller сборка..."
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
pyinstaller --clean -y packaging/Nexy.spec

if [ ! -d "dist/Nexy.app" ]; then
    echo "❌ Ошибка сборки приложения"
    exit 1
fi

echo "✅ Приложение собрано: dist/Nexy.app"
APP_PATH="$BUILD_DIR/dist/Nexy.app"

# ЭТАП 2: Подпись приложения
echo ""
echo "2️⃣ ПОДПИСЬ ПРИЛОЖЕНИЯ"
echo "===================="

APP_IDENTITY="Developer ID Application: Sergiy Zasorin ($TEAM_ID)"

echo "🧹 Очистка атрибутов macOS..."
xattr -cr "$APP_PATH"

echo "✍️ Подпись с Hardened Runtime..."
/usr/bin/codesign --force --timestamp \
    --options runtime \
    --entitlements packaging/entitlements.plist \
    --sign "$APP_IDENTITY" \
    "$APP_PATH"

echo "🔍 Проверка подписи..."
/usr/bin/codesign --verify --strict --deep "$APP_PATH"

echo "✅ Приложение подписано"

# ЭТАП 3: Создание PKG
echo ""
echo "3️⃣ СОЗДАНИЕ PKG"
echo "==============="

PKG_ROOT="build/payload"
RAW_PKG="dist/Nexy-raw.pkg"
DIST_PKG="dist/Nexy.pkg"
SIGNED_PKG="dist/Nexy-signed.pkg"

echo "🗂️ Подготовка payload..."
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/usr/local/nexy/resources"

cp -R "$APP_PATH" "$PKG_ROOT/usr/local/nexy/Nexy.app"
cp packaging/LaunchAgent/com.nexy.assistant.plist "$PKG_ROOT/usr/local/nexy/resources/"

echo "📦 Создание PKG..."
pkgbuild \
    --root "$PKG_ROOT" \
    --identifier "com.nexy.assistant.pkg" \
    --version "$VERSION" \
    --scripts scripts \
    "$RAW_PKG"

echo "📋 Создание distribution PKG..."
productbuild \
    --distribution packaging/distribution.xml \
    --resources packaging \
    --package-path dist \
    "$DIST_PKG"

echo "🔏 Подпись PKG..."
INSTALLER_IDENTITY="Developer ID Installer: Sergiy Zasorin ($TEAM_ID)"
productsign --sign "$INSTALLER_IDENTITY" "$DIST_PKG" "$SIGNED_PKG"

echo "✅ PKG создан: $SIGNED_PKG"

# ЭТАП 4: Создание DMG
echo ""
echo "4️⃣ СОЗДАНИЕ DMG"
echo "==============="

DMG_PATH="dist/Nexy.dmg"
TEMP_DMG="dist/Nexy-temp.dmg"
VOLUME_NAME="Nexy AI Assistant"

echo "💿 Создание DMG..."
APP_SIZE_KB=$(du -sk "$APP_PATH" | awk '{print $1}')
DMG_SIZE_MB=$(( APP_SIZE_KB/1024 + 200 ))

hdiutil create -volname "$VOLUME_NAME" -srcfolder "$APP_PATH" \
    -fs HFS+ -format UDRW -size "${DMG_SIZE_MB}m" "$TEMP_DMG"

MOUNT_DIR="/Volumes/$VOLUME_NAME"
hdiutil attach "$TEMP_DMG" -readwrite -noverify -noautoopen
ln -s /Applications "$MOUNT_DIR/Applications" || true
hdiutil detach "$MOUNT_DIR"

hdiutil convert "$TEMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH"
rm -f "$TEMP_DMG"

echo "✅ DMG создан: $DMG_PATH"

# ЭТАП 5: Копирование в основную папку
echo ""
echo "5️⃣ КОПИРОВАНИЕ АРТЕФАКТОВ"
echo "========================="

MAIN_DIR="/Users/sergiyzasorin/Desktop/Development/Nexy/client"
mkdir -p "$MAIN_DIR/dist"
cp "$BUILD_DIR/$DMG_PATH" "$MAIN_DIR/dist/"
cp "$BUILD_DIR/$SIGNED_PKG" "$MAIN_DIR/dist/"
cp -R "$APP_PATH" "$MAIN_DIR/dist/Nexy-final.app"

echo "📦 Копирование финальных артефактов..."

echo ""
echo "🎉 СБОРКА ЗАВЕРШЕНА УСПЕШНО!"
echo "============================"
echo ""
echo "📱 Приложение: dist/Nexy-final.app"
echo "📦 PKG: dist/Nexy-signed.pkg"
echo "💿 DMG: dist/Nexy.dmg"
echo ""
echo "📏 Размеры файлов:"
ls -lh "$MAIN_DIR/dist/Nexy-final.app"
ls -lh "$MAIN_DIR/dist/Nexy-signed.pkg"
ls -lh "$MAIN_DIR/dist/Nexy.dmg"

echo ""
echo "🔧 СЛЕДУЮЩИЕ ШАГИ:"
echo "1. Установи PKG: sudo installer -pkg dist/Nexy-signed.pkg -target /"
echo "2. Сбрось разрешения: ./packaging/reset_permissions.sh"
echo "3. Запусти приложение из ~/Applications/Nexy.app"
echo "4. Разреши доступ в системных диалогах"
echo ""
echo "📁 Временная папка сборки: $BUILD_DIR"

