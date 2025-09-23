#!/bin/bash
set -euo pipefail

echo "🔐 НАСТРОЙКА СЕРТИФИКАТА INSTALLER"
echo "=================================="

TEAM_ID="5NKLL2CLB9"
APPLE_ID="seregawpn@gmail.com"

echo "📋 Инструкция по получению Developer ID Installer:"
echo ""
echo "1️⃣ Войдите в Apple Developer Portal:"
echo "   https://developer.apple.com/account/resources/certificates/list"
echo ""
echo "2️⃣ Создайте новый сертификат:"
echo "   - Тип: Developer ID Installer"
echo "   - Team ID: $TEAM_ID"
echo "   - Скачайте .cer файл"
echo ""
echo "3️⃣ Установите сертификат в Keychain:"
echo "   - Дважды кликните на .cer файл"
echo "   - Или: security import certificate.cer -k ~/Library/Keychains/login.keychain"
echo ""
echo "4️⃣ Проверьте установку:"
echo "   security find-identity -p codesigning -v | grep -i installer"
echo ""
echo "5️⃣ После установки запустите:"
echo "   ./packaging/sign_and_notarize_pkg.sh"
echo ""

# Проверяем текущие сертификаты
echo "🔍 Текущие сертификаты:"
security find-identity -p codesigning -v | grep -E "(Application|Installer)" || echo "   Сертификаты не найдены"




