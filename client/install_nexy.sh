#!/bin/bash

# Скрипт для установки Nexy в ~/Applications/Nexy.app

echo "🚀 Установка Nexy AI Assistant в ~/Applications/Nexy.app"

# Создаем папку Applications если её нет
mkdir -p ~/Applications

# Удаляем старое приложение если есть
rm -rf ~/Applications/Nexy.app

# Копируем приложение из временной папки
if [ -d "/tmp/NexyCleanFinal.app" ]; then
    echo "📦 Копируем приложение из /tmp/NexyCleanFinal.app..."
    cp -R /tmp/NexyCleanFinal.app ~/Applications/Nexy.app
    echo "✅ Приложение установлено в ~/Applications/Nexy.app"
    
    # Проверяем подпись
    echo "🔍 Проверяем подпись..."
    if codesign --verify --deep --strict ~/Applications/Nexy.app; then
        echo "✅ Подпись корректна"
    else
        echo "⚠️  Проблема с подписью"
    fi
    
    # Запускаем приложение
    echo "🚀 Запускаем приложение..."
    open ~/Applications/Nexy.app
    
    echo "🎉 Установка завершена!"
    echo "📍 Приложение находится в: ~/Applications/Nexy.app"
else
    echo "❌ Ошибка: /tmp/NexyCleanFinal.app не найден"
    echo "Сначала запустите: cd packaging && ./build_final.sh"
    exit 1
fi
