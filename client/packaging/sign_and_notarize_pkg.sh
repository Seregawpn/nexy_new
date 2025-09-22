#!/bin/bash
set -euo pipefail

echo "🔏 ПОДПИСЬ И НОТАРИЗАЦИЯ PKG"
echo "============================="

TEAM_ID="5NKLL2CLB9"
PKG_PATH="dist/Nexy.pkg"
SIGNED_PKG_PATH="dist/Nexy-signed.pkg"

# Проверяем наличие unsigned PKG
if [ ! -f "$PKG_PATH" ]; then
    echo "❌ PKG не найден: $PKG_PATH"
    echo "Сначала создайте PKG: ./packaging/create_pkg_unsigned.sh"
    exit 1
fi

# Проверяем сертификат инсталлятора
echo "🔍 Проверка сертификата инсталлятора..."
INSTALLER_IDENTITY=$(security find-identity -p codesigning -v | grep "Developer ID Installer.*$TEAM_ID" | head -1 | cut -d'"' -f2)

if [ -z "$INSTALLER_IDENTITY" ]; then
    echo "❌ Сертификат Developer ID Installer не найден"
    echo "Запустите: ./packaging/setup_installer_cert.sh"
    exit 1
fi

echo "✅ Сертификат найден: $INSTALLER_IDENTITY"

# Подписываем PKG
echo ""
echo "✍️ Подпись PKG..."
productsign --sign "$INSTALLER_IDENTITY" "$PKG_PATH" "$SIGNED_PKG_PATH"

echo "🔍 Проверка подписи PKG..."
pkgutil --check-signature "$SIGNED_PKG_PATH"

echo "✅ PKG подписан: $SIGNED_PKG_PATH"

# Нотаризация PKG
echo ""
echo "📤 Нотаризация PKG..."
xcrun notarytool submit "$SIGNED_PKG_PATH" \
    --keychain-profile nexy-notary \
    --wait

echo "📎 Степлинг PKG..."
xcrun stapler staple "$SIGNED_PKG_PATH"

echo "🔍 Валидация PKG..."
xcrun stapler validate "$SIGNED_PKG_PATH"

echo ""
echo "🎉 PKG ГОТОВ!"
echo "============="
echo "📦 Подписанный PKG: $SIGNED_PKG_PATH"
echo "📏 Размер: $(du -sh "$SIGNED_PKG_PATH" | awk '{print $1}')"
echo ""
echo "🔧 Установка:"
echo "   sudo installer -pkg $SIGNED_PKG_PATH -target /"
