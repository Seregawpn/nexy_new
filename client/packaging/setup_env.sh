#!/bin/bash
# Скрипт для настройки переменных окружения для staging pipeline

echo "🔧 Настройка переменных окружения для Nexy staging pipeline"

# Экспорт переменных окружения
export DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
export APPLE_NOTARY_PROFILE="NexyNotary"

# Дополнительные переменные
export BUNDLE_ID="com.nexy.assistant"
export APP_NAME="Nexy"
export VERSION="2.5.0"
export BUILD="20500"

echo "✅ Переменные окружения установлены:"
echo "   DEVELOPER_ID_APP: $DEVELOPER_ID_APP"
echo "   DEVELOPER_ID_INSTALLER: $DEVELOPER_ID_INSTALLER"
echo "   APPLE_NOTARY_PROFILE: $APPLE_NOTARY_PROFILE"
echo "   BUNDLE_ID: $BUNDLE_ID"
echo "   APP_NAME: $APP_NAME"
echo "   VERSION: $VERSION"
echo "   BUILD: $BUILD"

echo ""
echo "🚀 Теперь можно запускать:"
echo "   make all          # Полный пайплайн"
echo "   make doctor       # Проверка готовности"
echo "   make sign-app     # Только подпись"
echo ""

# Проверка готовности
echo "🔍 Проверка готовности..."
make doctor

