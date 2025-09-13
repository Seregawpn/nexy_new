#!/bin/bash
# Полная проверка готовности к упаковке

echo "🔍 Полная проверка готовности к упаковке Nexy AI Voice Assistant"
echo "=================================================================="

# Проверка сертификатов
echo "📱 Проверка сертификатов..."
if ! security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    echo "❌ Developer ID Application отсутствует"
    exit 1
fi

if ! security find-identity -v -p basic | grep -q "Developer ID Installer"; then
    echo "❌ Developer ID Installer отсутствует"
    exit 1
fi

echo "✅ Все сертификаты найдены"

# Проверка системных зависимостей
echo "🔧 Проверка системных зависимостей..."
if ! command -v SwitchAudioSource &> /dev/null; then
    echo "❌ SwitchAudioSource не найден. Установите: brew install switchaudio-osx"
    exit 1
fi

if [ ! -d "/usr/local/lib/Sparkle.framework" ]; then
    echo "⚠️ Sparkle Framework не найден (опционально для автообновлений)"
else
    echo "✅ Sparkle Framework найден"
fi

echo "✅ Все системные зависимости найдены"

# Проверка Python зависимостей
echo "🐍 Проверка Python зависимостей..."
python3 -c "
import sys
required_modules = [
    'speech_recognition', 'sounddevice', 'grpcio', 'numpy', 
    'pydub', 'PIL', 'mss', 'rich', 'pynput', 'yaml', 'aiohttp',
    'rumps', 'pystray'
]

missing = []
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)

if missing:
    print(f'❌ Отсутствуют модули: {missing}')
    sys.exit(1)
else:
    print('✅ Все Python модули найдены')
"

# Проверка файлов конфигурации
echo "📋 Проверка файлов конфигурации..."
required_files=(
    "nexy.spec"
    "entitlements.plist"
    "sign_sparkle.sh"
    "create_pkg.sh"
    "notarize.sh"
    "build_production.sh"
    "hook-speech_recognition.py"
    "notarize_config.sh"
    "check_certificates.sh"
    "setup_notarization.sh"
    "assets/icons/app.icns"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Файл отсутствует: $file"
        exit 1
    fi
done

echo "✅ Все файлы конфигурации найдены"

# Проверка FLAC в Speech Recognition
echo "🎵 Проверка FLAC в Speech Recognition..."
python3 -c "
import speech_recognition
import os
sr_path = os.path.dirname(speech_recognition.__file__)
flac_path = os.path.join(sr_path, 'flac-mac')
if os.path.exists(flac_path):
    print('✅ FLAC 1.5.0 найден в Speech Recognition')
else:
    print('❌ FLAC не найден в Speech Recognition')
    exit(1)
"

# Проверка конфигурации нотаризации
echo "🔐 Проверка конфигурации нотаризации..."
source notarize_config.sh
if [ "$APP_PASSWORD" = "YOUR_APP_SPECIFIC_PASSWORD" ]; then
    echo "❌ App-Specific Password не настроен"
    exit 1
fi

echo "✅ Конфигурация нотаризации готова"

# Тест подключения к Apple
echo "🍎 Тест подключения к Apple..."
if xcrun notarytool history --apple-id "$APPLE_ID" --password "$APP_PASSWORD" --team-id "$TEAM_ID" >/dev/null 2>&1; then
    echo "✅ Подключение к Apple работает"
else
    echo "❌ Ошибка подключения к Apple"
    exit 1
fi

echo ""
echo "🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!"
echo "🚀 Система готова к упаковке: ./build_production.sh"
