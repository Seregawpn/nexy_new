#!/bin/bash
# Настройка нотаризации для Nexy AI Voice Assistant

echo "🔐 Настройка нотаризации для Nexy AI Voice Assistant"
echo "=================================================="

# Проверяем существование конфигурации
if [ -f "notarize_config.sh" ]; then
    echo "📋 Текущая конфигурация:"
    source notarize_config.sh
    echo "   Apple ID: $APPLE_ID"
    echo "   Team ID: $TEAM_ID"
    echo "   Bundle ID: $BUNDLE_ID"
    echo ""
fi

echo "📝 Инструкции по настройке App-Specific Password:"
echo ""
echo "1. Перейдите на https://appleid.apple.com"
echo "2. Войдите в свой Apple ID аккаунт"
echo "3. В разделе 'Sign-In and Security' найдите 'App-Specific Passwords'"
echo "4. Нажмите 'Generate an app-specific password'"
echo "5. Введите название: 'Nexy Notarization'"
echo "6. Скопируйте сгенерированный пароль"
echo ""

read -p "Введите App-Specific Password: " -s APP_PASSWORD
echo ""

if [ -z "$APP_PASSWORD" ]; then
    echo "❌ App-Specific Password не введен"
    exit 1
fi

# Обновляем конфигурацию
cat > notarize_config.sh << EOF
#!/bin/bash
# Конфигурация для нотаризации Nexy AI Voice Assistant

# Apple ID для нотаризации
export APPLE_ID="sergiyzasorin@gmail.com"

# App-Specific Password (создайте в appleid.apple.com)
export APP_PASSWORD="$APP_PASSWORD"

# Team ID
export TEAM_ID="5NKLL2CLB9"

# Bundle ID
export BUNDLE_ID="com.sergiyzasorin.nexy.voiceassistant"

echo "🔐 Конфигурация нотаризации:"
echo "   Apple ID: \$APPLE_ID"
echo "   Team ID: \$TEAM_ID"
echo "   Bundle ID: \$BUNDLE_ID"
echo "   App Password: \${APP_PASSWORD:0:4}****"
EOF

echo "✅ Конфигурация обновлена!"
echo ""

# Тестируем подключение к Apple
echo "🧪 Тестирование подключения к Apple..."
if xcrun notarytool history --apple-id "$APPLE_ID" --password "$APP_PASSWORD" --team-id "$TEAM_ID" >/dev/null 2>&1; then
    echo "✅ Подключение к Apple успешно!"
    echo "🎉 Нотаризация настроена и готова к использованию"
else
    echo "❌ Ошибка подключения к Apple"
    echo "   Проверьте правильность App-Specific Password"
    echo "   Убедитесь, что у вас есть активная подписка Apple Developer"
fi

echo ""
echo "🚀 Теперь можно запускать: ./build_production.sh"
