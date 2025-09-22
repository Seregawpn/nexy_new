#!/bin/bash
set -euo pipefail

echo "🚀 ПОЛНАЯ СБОРКА NEXY AI ASSISTANT"
echo "=================================="
echo "Версия: 1.71.0 с исправленными иконками"
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

# Проверяем notarytool
echo "🔍 Проверка notarytool..."
if ! xcrun notarytool history --keychain-profile nexy-notary >/dev/null 2>&1; then
    echo "❌ Профиль notarytool не найден: nexy-notary"
    echo "Настройте профиль: xcrun notarytool store-credentials nexy-notary"
    exit 1
fi

echo "✅ Все предварительные проверки пройдены"
echo ""

# ЭТАП 1: Сборка приложения
echo "1️⃣ СБОРКА ПРИЛОЖЕНИЯ"
echo "===================="

BUILD_DIR="/tmp/nexy_production_$(date +%s)"
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

echo "✍️ Подпись БЕЗ Hardened Runtime..."
/usr/bin/codesign --force --timestamp \
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

productbuild \
    --distribution packaging/distribution.xml \
    --resources packaging \
    --package-path dist \
    "$DIST_PKG"

echo "🔏 Подпись PKG..."
INSTALLER_IDENTITY="Developer ID Installer: Sergiy Zasorin ($TEAM_ID)"
productsign --sign "$INSTALLER_IDENTITY" "$DIST_PKG" "$SIGNED_PKG"

echo "✅ PKG создан и подписан: $SIGNED_PKG"

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

# ЭТАП 5: Нотаризация DMG
echo ""
echo "5️⃣ НОТАРИЗАЦИЯ DMG"
echo "=================="

echo "📤 Отправка на нотаризацию..."
xcrun notarytool submit "$DMG_PATH" \
    --keychain-profile nexy-notary \
    --wait

echo "📎 Степлинг..."
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"

echo "✅ DMG нотаризован"

# ЭТАП 6: Генерация манифеста
echo ""
echo "6️⃣ ГЕНЕРАЦИЯ МАНИФЕСТА"
echo "======================"

if [ -f "private_key.pem" ]; then
    echo "🔑 Генерация с Ed25519 подписью..."
    python3 packaging/generate_manifest.py "$DMG_PATH" "$VERSION" "$BUILD" "private_key.pem"
else
    echo "⚠️ Ed25519 ключ не найден, генерация без подписи..."
    python3 packaging/generate_manifest.py "$DMG_PATH" "$VERSION" "$BUILD"
fi

echo "✅ Манифест создан: dist/manifest.json"

# ЭТАП 7: Копирование в основную папку
echo ""
echo "7️⃣ КОПИРОВАНИЕ АРТЕФАКТОВ"
echo "========================="

MAIN_DIR="/Users/sergiyzasorin/Desktop/Development/Nexy/client"
cd "$MAIN_DIR"

echo "📦 Копирование финальных артефактов..."
cp "$BUILD_DIR/$SIGNED_PKG" "dist/"
cp "$BUILD_DIR/$DMG_PATH" "dist/"
cp "$BUILD_DIR/dist/manifest.json" "dist/"
cp -R "$APP_PATH" "dist/Nexy-final.app"

echo ""
echo "🎉 СБОРКА ЗАВЕРШЕНА УСПЕШНО!"
echo "============================"
echo ""
echo "📦 PKG инсталлятор: dist/Nexy-signed.pkg"
echo "💿 DMG нотаризованный: dist/Nexy.dmg"
echo "📋 Манифест: dist/manifest.json"
echo "📱 Приложение: dist/Nexy-final.app"
echo ""
echo "📏 Размеры файлов:"
ls -lh dist/Nexy-signed.pkg dist/Nexy.dmg dist/manifest.json

echo ""
echo "🧪 СЛЕДУЮЩИЙ ШАГ: Тестирование"
echo "sudo installer -pkg dist/Nexy-signed.pkg -target /"
echo ""
echo "🎯 ВАЖНО: Проверьте цветные иконки в меню-баре!"
echo "📁 Временная папка сборки: $BUILD_DIR"

