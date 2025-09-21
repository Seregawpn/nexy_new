#!/bin/bash
# tools/packaging/uninstall_launch_agent.sh
# Скрипт удаления LaunchAgent для Nexy

set -e

# Конфигурация
BUNDLE_ID="com.nexy.assistant"
PLIST_FILE="$HOME/Library/LaunchAgents/${BUNDLE_ID}.plist"

echo "🧹 Удаление LaunchAgent для Nexy..."

# Останавливаем и выгружаем LaunchAgent
launchctl bootout "gui/$UID/$BUNDLE_ID" 2>/dev/null || {
    echo "⚠️ LaunchAgent не был загружен"
}

# Удаляем plist файл
if [[ -f "$PLIST_FILE" ]]; then
    rm -f "$PLIST_FILE"
    echo "✅ Plist файл удален: $PLIST_FILE"
else
    echo "⚠️ Plist файл не найден: $PLIST_FILE"
fi

echo "🎉 LaunchAgent удален успешно!"
