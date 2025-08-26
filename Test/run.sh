#!/bin/bash

# Скрипт для запуска Gemini Live API ассистента

echo "🚀 Запуск Gemini Live API ассистента..."

# Проверяем наличие API ключа
if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ ОШИБКА: Не установлен GEMINI_API_KEY"
    echo "Установите переменную окружения:"
    echo "export GEMINI_API_KEY='your_api_key_here'"
    echo ""
    echo "Или добавьте в ~/.bashrc или ~/.zshrc:"
    echo "echo 'export GEMINI_API_KEY=\"your_api_key_here\"' >> ~/.bashrc"
    echo "source ~/.bashrc"
    exit 1
fi

echo "✅ API ключ найден"
echo "📸 Режим: скриншоты экрана"
echo ""

# Запускаем приложение
python main.py
