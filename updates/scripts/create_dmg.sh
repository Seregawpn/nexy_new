#!/bin/bash
# Скрипт для создания DMG файла из .app

set -e  # Выход при ошибке

# Параметры
APP_PATH="$1"
DMG_PATH="$2"
VOLUME_NAME="$3"

if [ $# -lt 3 ]; then
    echo "Использование: $0 <путь_к_app> <путь_к_dmg> <имя_тома>"
    echo "Пример: $0 dist/Nexy.app artifacts/Nexy-2.6.0.dmg \"Nexy 2.6.0\""
    exit 1
fi

# Проверяем существование .app
if [ ! -d "$APP_PATH" ]; then
    echo "❌ Приложение не найдено: $APP_PATH"
    exit 1
fi

# Создаем директорию для DMG если нужно
mkdir -p "$(dirname "$DMG_PATH")"

echo "🔧 Создание DMG из $APP_PATH..."

# Удаляем старый DMG если есть
if [ -f "$DMG_PATH" ]; then
    echo "🗑️ Удаление старого DMG..."
    rm -f "$DMG_PATH"
fi

# Создаем временную директорию
TEMP_DIR=$(mktemp -d)
echo "📁 Временная директория: $TEMP_DIR"

# Копируем .app в временную директорию
echo "📋 Копирование приложения..."
cp -R "$APP_PATH" "$TEMP_DIR/"

# Создаем DMG
echo "🔨 Создание DMG..."
hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$TEMP_DIR" \
    -ov \
    -format UDZO \
    -fs HFS+ \
    "$DMG_PATH"

# Очищаем временную директорию
echo "🧹 Очистка..."
rm -rf "$TEMP_DIR"

# Проверяем результат
if [ -f "$DMG_PATH" ]; then
    DMG_SIZE=$(du -h "$DMG_PATH" | cut -f1)
    echo "✅ DMG создан успешно: $DMG_PATH ($DMG_SIZE)"
    
    # Показываем информацию о DMG
    echo "📊 Информация о DMG:"
    hdiutil imageinfo "$DMG_PATH" | grep -E "(Format|Checksum|Format-Description)"
    
else
    echo "❌ Ошибка создания DMG"
    exit 1
fi

echo "🎉 Готово!"
