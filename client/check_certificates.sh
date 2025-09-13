#!/bin/bash
# Проверка сертификатов для подписи кода и нотаризации

echo "🔍 Проверка сертификатов для Nexy AI Voice Assistant"
echo "=================================================="

# Проверка Developer ID Application
echo "📱 Developer ID Application (для подписи .app):"
if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    security find-identity -v -p codesigning | grep "Developer ID Application"
    echo "✅ Developer ID Application найден"
else
    echo "❌ Developer ID Application НЕ найден"
    echo "   Создайте в Apple Developer Portal:"
    echo "   https://developer.apple.com/account/resources/certificates/list"
fi

echo ""

# Проверка Developer ID Installer
echo "📦 Developer ID Installer (для подписи .pkg):"
if security find-identity -v -p basic | grep -q "Developer ID Installer"; then
    security find-identity -v -p basic | grep "Developer ID Installer"
    echo "✅ Developer ID Installer найден"
else
    echo "❌ Developer ID Installer НЕ найден"
    echo "   Создайте в Apple Developer Portal:"
    echo "   https://developer.apple.com/account/resources/certificates/list"
fi

echo ""

# Проверка конфигурации нотаризации
echo "🔐 Конфигурация нотаризации:"
if [ -f "notarize_config.sh" ]; then
    source notarize_config.sh
    echo "   Apple ID: $APPLE_ID"
    echo "   Team ID: $TEAM_ID"
    echo "   Bundle ID: $BUNDLE_ID"
    
    if [ "$APP_PASSWORD" = "YOUR_APP_SPECIFIC_PASSWORD" ]; then
        echo "   App Password: ❌ НЕ НАСТРОЕН"
        echo "   Создайте App-Specific Password в https://appleid.apple.com"
    else
        echo "   App Password: ✅ НАСТРОЕН"
    fi
else
    echo "❌ Файл notarize_config.sh не найден"
fi

echo ""
echo "🎯 Готовность к сборке:"

# Проверка всех компонентов
ALL_READY=true

if ! security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    echo "❌ Developer ID Application отсутствует"
    ALL_READY=false
fi

if ! security find-identity -v -p basic | grep -q "Developer ID Installer"; then
    echo "❌ Developer ID Installer отсутствует"
    ALL_READY=false
fi

if [ ! -f "notarize_config.sh" ] || [ "$APP_PASSWORD" = "YOUR_APP_SPECIFIC_PASSWORD" ]; then
    echo "❌ Конфигурация нотаризации не завершена"
    ALL_READY=false
fi

if [ "$ALL_READY" = true ]; then
    echo "✅ ВСЕ СЕРТИФИКАТЫ ГОТОВЫ!"
    echo "🚀 Можно запускать: ./build_production.sh"
else
    echo "⚠️ НЕКОТОРЫЕ СЕРТИФИКАТЫ ОТСУТСТВУЮТ"
    echo "🔧 Настройте недостающие компоненты перед сборкой"
fi
