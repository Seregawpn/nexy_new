#!/bin/bash
set -euo pipefail

echo "🚀 СБОРКА NEXY AI ASSISTANT (DMG ONLY)"
echo "====================================="
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

# Проверяем только сертификат приложения
echo "🔍 Проверка сертификатов..."
if ! security find-identity -p codesigning -v | grep -q "Developer ID Application.*$TEAM_ID"; then
    echo "❌ Сертификат приложения не найден"
    security find-identity -p codesigning -v
    exit 1
fi

echo "✅ Сертификат приложения найден"

# ЭТАП 1: Сборка приложения
echo ""
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

echo "✍️ Подпись С Hardened Runtime для нотаризации..."
/usr/bin/codesign --force --timestamp \
    --options runtime \
    --entitlements packaging/entitlements.plist \
    --sign "$APP_IDENTITY" \
    "$APP_PATH"

echo "🔍 Проверка подписи..."
/usr/bin/codesign --verify --strict --deep "$APP_PATH"

echo "✅ Приложение подписано"

# ЭТАП 3: Создание DMG
echo ""
echo "3️⃣ СОЗДАНИЕ DMG"
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

# ЭТАП 4: Копирование в основную папку
echo ""
echo "4️⃣ КОПИРОВАНИЕ АРТЕФАКТОВ"
echo "========================="

MAIN_DIR="/Users/sergiyzasorin/Desktop/Development/Nexy/client"
cd "$MAIN_DIR"

echo "📦 Копирование финальных артефактов..."
cp "$BUILD_DIR/$DMG_PATH" "dist/"
cp -R "$APP_PATH" "dist/Nexy-final.app"

echo ""
echo "🎉 СБОРКА ЗАВЕРШЕНА УСПЕШНО!"
echo "============================"
echo ""
echo "💿 DMG: dist/Nexy.dmg"
echo "📱 Приложение: dist/Nexy-final.app"
echo ""
echo "📏 Размеры файлов:"
ls -lh dist/Nexy.dmg
echo ""
echo "🎯 СЛЕДУЮЩИЙ ШАГ: Тестирование"
echo "Откройте dist/Nexy.dmg и перетащите приложение в Applications"
echo ""
echo "📁 Временная папка сборки: $BUILD_DIR"
