#!/bin/bash
# Полная автоматизированная сборка Nexy AI Voice Assistant

set -e

echo "🚀 ПОЛНАЯ СБОРКА NEXY AI VOICE ASSISTANT"
echo "========================================"

# Этап 1: Предварительная проверка
echo ""
echo "📋 ЭТАП 1: Предварительная проверка"
echo "-----------------------------------"
./verify_packaging.sh
echo "✅ Предварительная проверка завершена"

# Этап 2: Установка зависимостей
echo ""
echo "📋 ЭТАП 2: Установка зависимостей"
echo "---------------------------------"
if ! command -v SwitchAudioSource &> /dev/null; then
    echo "📦 Установка SwitchAudioSource..."
    brew install switchaudio-osx
else
    echo "✅ SwitchAudioSource уже установлен"
fi

if [ ! -d "/usr/local/lib/Sparkle.framework" ]; then
    echo "📦 Установка Sparkle Framework..."
    brew install sparkle || echo "⚠️ Sparkle Framework не установлен (опционально)"
else
    echo "✅ Sparkle Framework уже установлен"
fi

# Этап 3: Сборка приложения
echo ""
echo "📋 ЭТАП 3: Сборка приложения"
echo "----------------------------"
echo "🧹 Очистка предыдущих сборок..."
rm -rf build/ dist/

echo "🔨 Сборка через PyInstaller..."
python3 -m PyInstaller nexy.spec --clean --noconfirm

if [ ! -d "dist/Nexy.app" ]; then
    echo "❌ Ошибка сборки приложения"
    exit 1
fi
echo "✅ Приложение собрано успешно"

# Этап 4: Подпись Sparkle Framework (если включен)
echo ""
echo "📋 ЭТАП 4: Подпись Sparkle Framework"
echo "-----------------------------------"
./sign_sparkle.sh
echo "✅ Sparkle Framework подписан"

# Этап 5: Создание PKG
echo ""
echo "📋 ЭТАП 5: Создание PKG установщика"
echo "-----------------------------------"
./create_pkg.sh

if [ ! -f "Nexy_AI_Voice_Assistant_v1.71.0.pkg" ]; then
    echo "❌ Ошибка создания PKG"
    exit 1
fi
echo "✅ PKG создан успешно"

# Этап 6: Нотаризация
echo ""
echo "📋 ЭТАП 6: Нотаризация PKG"
echo "--------------------------"
./notarize.sh Nexy_AI_Voice_Assistant_v1.71.0.pkg
echo "✅ PKG нотаризован успешно"

# Этап 7: Финальная проверка
echo ""
echo "📋 ЭТАП 7: Финальная проверка"
echo "-----------------------------"
echo "🔍 Проверка подписи PKG..."
codesign --verify --verbose Nexy_AI_Voice_Assistant_v1.71.0.pkg

echo "📊 Информация о PKG:"
du -h Nexy_AI_Voice_Assistant_v1.71.0.pkg
pkgutil --check-signature Nexy_AI_Voice_Assistant_v1.71.0.pkg

echo ""
echo "🎉 СБОРКА ЗАВЕРШЕНА УСПЕШНО!"
echo "============================="
echo "📦 Готовый PKG: Nexy_AI_Voice_Assistant_v1.71.0.pkg"
echo "📱 Приложение: dist/Nexy.app"
echo ""
echo "📋 Информация о продукте:"
echo "   • Версия: 1.71.0"
echo "   • Bundle ID: com.sergiyzasorin.nexy.voiceassistant"
echo "   • Подпись: Developer ID Application/Installer"
echo "   • Нотаризация: ✅ Подтверждена Apple"
echo "   • Размер: $(du -h Nexy_AI_Voice_Assistant_v1.71.0.pkg | cut -f1)"
echo ""
echo "🚀 PKG готов к распространению!"
