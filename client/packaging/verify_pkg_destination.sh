#!/bin/bash

# Скрипт для проверки назначения PKG файла
# Использование: verify_pkg_destination.sh Nexy-2.5.0.pkg

PKG_FILE="$1"

if [ -z "$PKG_FILE" ]; then
    echo "❌ Ошибка: не указан PKG файл"
    echo "Использование: $0 <pkg_file>"
    exit 1
fi

if [ ! -f "$PKG_FILE" ]; then
    echo "❌ Ошибка: PKG файл не найден: $PKG_FILE"
    exit 1
fi

echo "🔍 Проверка назначения PKG: $PKG_FILE"

# Создаем временную директорию для распаковки
TEMP_DIR=$(mktemp -d)
echo "📁 Временная директория: $TEMP_DIR"

# Распаковываем PKG
echo "📦 Распаковка PKG..."
pkgutil --expand "$PKG_FILE" "$TEMP_DIR/expanded"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при распаковке PKG"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Ищем файлы с информацией о назначении
echo "🔍 Поиск информации о назначении..."

# Проверяем Distribution файл
DIST_FILE="$TEMP_DIR/expanded/Distribution"
if [ -f "$DIST_FILE" ]; then
    echo "📄 Анализ Distribution файла..."
    if grep -q "/Applications" "$DIST_FILE"; then
        echo "✅ Найдено назначение /Applications в Distribution"
    else
        echo "⚠️  Назначение /Applications не найдено в Distribution"
    fi
    
    # Ищем конкретные пути
    echo "📍 Найденные пути назначения:"
    grep -o 'installLocation="[^"]*"' "$DIST_FILE" || echo "Пути назначения не найдены"
fi

# Проверяем Payload
PAYLOAD_FILE="$TEMP_DIR/expanded/Payload"
if [ -f "$PAYLOAD_FILE" ]; then
    echo "📦 Анализ Payload..."
    PAYLOAD_DIR="$TEMP_DIR/payload"
    mkdir -p "$PAYLOAD_DIR"
    
    # Распаковываем Payload (это gzip + cpio)
    if command -v gunzip >/dev/null 2>&1 && command -v cpio >/dev/null 2>&1; then
        gunzip -c "$PAYLOAD_FILE" | cpio -i -d -D "$PAYLOAD_DIR" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            echo "✅ Payload успешно распакован"
            
            # Ищем .app файлы
            APP_FILES=$(find "$PAYLOAD_DIR" -name "*.app" -type d)
            if [ -n "$APP_FILES" ]; then
                echo "📱 Найденные .app файлы:"
                echo "$APP_FILES"
                
                # Проверяем пути
                echo "$APP_FILES" | while read -r app_path; do
                    if [[ "$app_path" == */Applications/* ]]; then
                        echo "✅ $app_path - правильный путь (/Applications)"
                    else
                        echo "⚠️  $app_path - неожиданный путь"
                    fi
                done
            else
                echo "⚠️  .app файлы не найдены в Payload"
            fi
        else
            echo "⚠️  Не удалось распаковать Payload"
        fi
    else
        echo "⚠️  gunzip или cpio не найдены, пропускаем анализ Payload"
    fi
fi

# Очистка
rm -rf "$TEMP_DIR"

echo "✅ Проверка завершена"
