#!/bin/bash
set -euo pipefail

echo "📦 СОЗДАНИЕ PKG (БЕЗ ПОДПИСИ)"
echo "=============================="

VERSION="1.71.0"
BUILD="171"

# Проверяем наличие приложения
if [ ! -d "dist/Nexy-final.app" ]; then
    echo "❌ Приложение не найдено: dist/Nexy-final.app"
    exit 1
fi

echo "✅ Приложение найдено: dist/Nexy-final.app"

# Создаем структуру для PKG
echo "🗂️ Подготовка payload..."
PKG_ROOT="build/payload"
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/usr/local/nexy/resources"

# Копируем приложение
cp -R "dist/Nexy-final.app" "$PKG_ROOT/usr/local/nexy/Nexy.app"
cp packaging/LaunchAgent/com.nexy.assistant.plist "$PKG_ROOT/usr/local/nexy/resources/"

echo "📦 Создание PKG..."
RAW_PKG="dist/Nexy-raw.pkg"
pkgbuild \
    --root "$PKG_ROOT" \
    --identifier "com.nexy.assistant.pkg" \
    --version "$VERSION" \
    --scripts scripts \
    "$RAW_PKG"

echo "📋 Создание distribution PKG..."
DIST_PKG="dist/Nexy.pkg"
productbuild \
    --distribution packaging/distribution.xml \
    --resources packaging \
    --package-path dist \
    "$DIST_PKG"

echo "✅ PKG создан: $DIST_PKG"
echo "📏 Размер: $(ls -lh "$DIST_PKG" | awk '{print $5}')"

echo ""
echo "⚠️  ВНИМАНИЕ: PKG не подписан!"
echo "Для подписи нужен сертификат Developer ID Installer"
echo "Текущий PKG можно использовать для тестирования"




