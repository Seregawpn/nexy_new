#!/bin/bash
set -e

APP_NAME="Nexy"
APP_VERSION="1.71.0"
PKG_NAME="Nexy_AI_Voice_Assistant_v${APP_VERSION}.pkg"
BUNDLE_ID="com.sergiyzasorin.nexy.voiceassistant"
DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"

echo "📦 Создание PKG установщика..."

# Создание временной директории
TEMP_DIR=$(mktemp -d)
PKG_ROOT="$TEMP_DIR/pkgroot"
APP_DIR="$PKG_ROOT/Applications"
LAUNCH_AGENTS_DIR="$PKG_ROOT/Library/LaunchAgents"

mkdir -p "$APP_DIR"
mkdir -p "$LAUNCH_AGENTS_DIR"

# Копирование приложения
cp -R "dist/Nexy.app" "$APP_DIR/"

# Копирование LaunchAgent файлов
if [ -f "pkg_root/Library/LaunchAgents/com.sergiyzasorin.nexy.voiceassistant.plist" ]; then
    cp "pkg_root/Library/LaunchAgents/com.sergiyzasorin.nexy.voiceassistant.plist" "$LAUNCH_AGENTS_DIR/"
    echo "✅ LaunchAgent plist скопирован"
fi

if [ -f "pkg_root/Library/LaunchAgents/nexy_launcher.sh" ]; then
    cp "pkg_root/Library/LaunchAgents/nexy_launcher.sh" "$LAUNCH_AGENTS_DIR/"
    chmod +x "$LAUNCH_AGENTS_DIR/nexy_launcher.sh"
    echo "✅ LaunchAgent скрипт скопирован"
fi

# Очистка расширенных атрибутов
xattr -cr "$APP_DIR/Nexy.app"

# Код-подпись приложения
echo "🔐 Подписание приложения..."
if codesign --force --verify --verbose --sign "$DEVELOPER_ID_APP" \
    --options runtime \
    --entitlements entitlements.plist \
    "$APP_DIR/Nexy.app"; then
    echo "✅ Приложение подписано успешно"
else
    echo "❌ Ошибка подписания приложения"
    exit 1
fi

# Создание PKG
echo "📦 Создание PKG..."
if pkgbuild --root "$PKG_ROOT" \
    --identifier "$BUNDLE_ID" \
    --version "$APP_VERSION" \
    --install-location "/" \
    --sign "$DEVELOPER_ID_INSTALLER" \
    "$PKG_NAME"; then
    echo "✅ PKG создан успешно"
else
    echo "❌ Ошибка создания PKG"
    exit 1
fi

# Очистка
rm -rf "$TEMP_DIR"

echo "✅ PKG создан: $PKG_NAME"
echo "ℹ️ Убедитесь, что пользователи установили зависимости: brew install switchaudio-osx sparkle"
