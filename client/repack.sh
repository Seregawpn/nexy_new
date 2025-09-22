#!/bin/bash
set -euo pipefail

echo "🎯 NEXY AI ASSISTANT - ПЕРЕУПАКОВКА"
echo "=================================="

# Переходим в директорию проекта
cd "$(dirname "$0")"
echo "📁 Рабочая директория: $(pwd)"

# Очищаем старые сборки
echo "🧹 Очистка старых сборок..."
rm -rf dist/ build/ *.pkg *.dmg *.app
echo "✅ Очистка завершена"

# Проверяем архитектуру
echo "🔍 Проверка архитектуры..."
if [ "$(uname -m)" != "arm64" ]; then
    echo "❌ Требуется Apple Silicon (arm64)"
    exit 1
fi
echo "✅ Архитектура: arm64"

# Проверяем PyInstaller
echo "🔍 Проверка PyInstaller..."
if ! command -v pyinstaller &> /dev/null; then
    echo "❌ PyInstaller не найден"
    exit 1
fi
echo "✅ PyInstaller: $(pyinstaller --version)"

# Проверяем сертификаты
echo "🔍 Проверка сертификатов..."
if ! security find-identity -p codesigning -v | grep -q "Developer ID Application"; then
    echo "❌ Сертификат приложения не найден"
    exit 1
fi
if ! security find-identity -p codesigning -v | grep -q "Developer ID Installer"; then
    echo "❌ Сертификат инсталлятора не найден"
    exit 1
fi
echo "✅ Сертификаты найдены"

# Делаем скрипты исполняемыми
echo "🔧 Настройка скриптов..."
chmod +x packaging/build_all.sh
chmod +x scripts/postinstall
echo "✅ Скрипты настроены"

# Запускаем сборку
echo "🚀 Запуск сборки..."
./packaging/build_all.sh

echo "🎉 ПЕРЕУПАКОВКА ЗАВЕРШЕНА!"
echo "📦 Проверьте папку dist/ для артефактов"


