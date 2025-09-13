#!/bin/bash
# check_ready.sh - Проверка готовности к сборке

set -e

echo "🔍 Проверка готовности к производственной сборке"
echo "=================================================="

# Проверка зависимостей
echo "📦 Проверка зависимостей..."
MISSING_DEPS=0

if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller не установлен"
    MISSING_DEPS=1
else
    echo "✅ PyInstaller установлен"
fi

if ! command -v codesign &> /dev/null; then
    echo "❌ codesign не найден"
    MISSING_DEPS=1
else
    echo "✅ codesign найден"
fi

if ! command -v productsign &> /dev/null; then
    echo "❌ productsign не найден"
    MISSING_DEPS=1
else
    echo "✅ productsign найден"
fi

if ! command -v xcrun &> /dev/null; then
    echo "❌ xcrun не найден"
    MISSING_DEPS=1
else
    echo "✅ xcrun найден"
fi

# Проверка сертификатов
echo ""
echo "🔐 Проверка сертификатов..."
CERT_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
CERT_PKG="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"

if ! security find-identity -v -p codesigning | grep -q "$CERT_APP"; then
    echo "❌ Сертификат приложения не найден: $CERT_APP"
    MISSING_DEPS=1
else
    echo "✅ Сертификат приложения найден"
fi

if ! security find-identity -v -p basic | grep -q "$CERT_PKG"; then
    echo "❌ Сертификат установщика не найден: $CERT_PKG"
    MISSING_DEPS=1
else
    echo "✅ Сертификат установщика найден"
fi

# Проверка файлов
echo ""
echo "📁 Проверка файлов..."
if [ ! -f "nexy.spec" ]; then
    echo "❌ nexy.spec не найден"
    MISSING_DEPS=1
else
    echo "✅ nexy.spec найден"
fi

if [ ! -f "entitlements_app.plist" ]; then
    echo "❌ entitlements_app.plist не найден"
    MISSING_DEPS=1
else
    echo "✅ entitlements_app.plist найден"
fi

if [ ! -f "entitlements_pkg.plist" ]; then
    echo "❌ entitlements_pkg.plist не найден"
    MISSING_DEPS=1
else
    echo "✅ entitlements_pkg.plist найден"
fi

# Проверка nexy.spec
echo ""
echo "⚙️  Проверка nexy.spec..."
if ! grep -q 'codesign_identity="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"' nexy.spec; then
    echo "❌ codesign_identity не настроен в nexy.spec"
    MISSING_DEPS=1
else
    echo "✅ codesign_identity настроен"
fi

if ! grep -q "entitlements_file='entitlements_app.plist'" nexy.spec; then
    echo "❌ entitlements_file не настроен в nexy.spec"
    MISSING_DEPS=1
else
    echo "✅ entitlements_file настроен"
fi

if ! grep -q "codesign_options=\['runtime', 'timestamp'\]" nexy.spec; then
    echo "❌ codesign_options не настроен в nexy.spec"
    MISSING_DEPS=1
else
    echo "✅ codesign_options настроен"
fi

# Итоговый результат
echo ""
echo "=================================================="
if [ $MISSING_DEPS -eq 0 ]; then
    echo "✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!"
    echo "🚀 Готов к производственной сборке"
    echo "💡 Запустите: ./build_production.sh"
else
    echo "❌ НАЙДЕНЫ ПРОБЛЕМЫ!"
    echo "🔧 Исправьте ошибки перед сборкой"
    exit 1
fi

