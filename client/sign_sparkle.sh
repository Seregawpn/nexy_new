#!/bin/bash
# Автоматическая подпись Sparkle Framework после сборки PyInstaller

set -e

APP_PATH="dist/Nexy.app"
SPARKLE_FRAMEWORK="$APP_PATH/Contents/Frameworks/Sparkle.framework"

echo "🔐 Подпись Sparkle Framework..."

# Проверка наличия Sparkle Framework
if [ ! -d "$SPARKLE_FRAMEWORK" ]; then
    echo "ℹ️ Sparkle Framework не найден в приложении. Пропускаем подпись."
    exit 0
fi

# Подпись Sparkle Framework
echo "🔐 Подписание Sparkle Framework..."
codesign --force --verify --verbose --sign "Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)" \
    --options runtime \
    "$SPARKLE_FRAMEWORK"

# Подпись всего .app bundle
echo "🔐 Подписание всего .app bundle..."
codesign --force --verify --verbose --sign "Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)" \
    --options runtime \
    --entitlements entitlements.plist \
    "$APP_PATH"

echo "✅ Sparkle Framework подписан успешно!"

