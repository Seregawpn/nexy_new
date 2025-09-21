#!/bin/bash

# make_dmg.sh - Создание DMG файла для Nexy
# Использование: ./make_dmg.sh <path_to_app> <output_dmg>

APP_PATH="$1"
DMG_PATH="$2"

if [ -z "$APP_PATH" ] || [ -z "$DMG_PATH" ]; then
    echo "Использование: $0 <path_to_app> <output_dmg>"
    exit 1
fi

if [ ! -d "$APP_PATH" ]; then
    echo "Ошибка: .app файл не найден: $APP_PATH"
    exit 1
fi

echo "🔨 Создание DMG файла..."
echo "  APP: $APP_PATH"
echo "  DMG: $DMG_PATH"

# Создаем временную папку для DMG
TEMP_DMG_DIR=$(mktemp -d)
cp -R "$APP_PATH" "$TEMP_DMG_DIR/"

# Создаем DMG
hdiutil create -volname "Nexy" -srcfolder "$TEMP_DMG_DIR" -ov -format UDZO "$DMG_PATH"

# Очищаем временную папку
rm -rf "$TEMP_DMG_DIR"

echo "✅ DMG файл создан: $DMG_PATH"
