#!/bin/bash
# tools/packaging/install_launch_agent.sh
# Скрипт установки LaunchAgent для Nexy

set -e

# Конфигурация
BUNDLE_ID="com.nexy.assistant"
PLIST_FILE="$HOME/Library/LaunchAgents/${BUNDLE_ID}.plist"
SOURCE_PLIST="$(dirname "$0")/com.nexy.assistant.plist"

echo "🚀 Установка LaunchAgent для Nexy..."

# Проверяем что исходный plist файл существует
if [[ ! -f "$SOURCE_PLIST" ]]; then
    echo "❌ Ошибка: файл $SOURCE_PLIST не найден"
    exit 1
fi

# Создаем директорию LaunchAgents если не существует
mkdir -p "$(dirname "$PLIST_FILE")"

# Копируем plist файл
cp "$SOURCE_PLIST" "$PLIST_FILE"
echo "✅ Plist файл скопирован в $PLIST_FILE"

# Загружаем LaunchAgent
launchctl bootstrap "gui/$UID" "$PLIST_FILE" 2>/dev/null || {
    echo "⚠️ LaunchAgent уже загружен, перезагружаем..."
    launchctl bootout "gui/$UID/$BUNDLE_ID" 2>/dev/null || true
    launchctl bootstrap "gui/$UID" "$PLIST_FILE"
}

echo "✅ LaunchAgent установлен и активирован"

# Проверяем статус
if launchctl print "gui/$UID/$BUNDLE_ID" >/dev/null 2>&1; then
    echo "✅ LaunchAgent загружен успешно"
else
    echo "❌ Ошибка: LaunchAgent не загружен"
    exit 1
fi

echo "🎉 Установка завершена!"
echo "📝 Логи: /tmp/nexy.log и /tmp/nexy.error.log"
echo "🔍 Проверка статуса: launchctl print gui/\$UID/$BUNDLE_ID"
