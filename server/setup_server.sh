#!/bin/bash
# setup_server.sh

set -e

echo "🔧 НАСТРОЙКА СЕРВЕРА С СИСТЕМОЙ ОБНОВЛЕНИЙ"
echo "=========================================="

# Создаем структуру директорий
echo "📁 Создание структуры директорий..."
mkdir -p updates/downloads
mkdir -p updates/keys

# Проверяем наличие AppCast XML
if [ -f "updates/appcast.xml" ]; then
    echo "✅ AppCast XML файл уже существует"
else
    echo "❌ AppCast XML файл не найден"
    echo "   Создайте файл updates/appcast.xml"
fi

# Проверяем наличие тестового DMG
if [ -f "updates/downloads/Nexy_1.71.0.dmg" ]; then
    echo "✅ Тестовый DMG файл уже существует"
else
    echo "❌ Тестовый DMG файл не найден"
    echo "   Создайте файл updates/downloads/Nexy_1.71.0.dmg"
fi

# Генерируем ключи для подписи (если не существуют)
if [ ! -f "updates/keys/ed25519_private.pem" ]; then
    echo "🔐 Генерация ключей для подписи..."
    cd updates/keys
    openssl genpkey -algorithm ed25519 -out ed25519_private.pem
    openssl pkey -in ed25519_private.pem -pubout -out ed25519_public.pem
    cd ../..
    echo "✅ Ключи сгенерированы"
else
    echo "✅ Ключи уже существуют"
fi

echo ""
echo "✅ Сервер настроен!"
echo "📁 Структура:"
echo "   - updates/appcast.xml"
echo "   - updates/downloads/Nexy_1.71.0.dmg"
echo "   - updates/keys/ed25519_private.pem"
echo "   - updates/keys/ed25519_public.pem"
echo ""
echo "🚀 Для запуска сервера:"
echo "   python3 main.py"
echo ""
echo "📡 Endpoints после запуска:"
echo "   - HTTP: http://localhost:80"
echo "   - gRPC: localhost:50051"
echo "   - Updates: http://localhost:8080"
echo "   - AppCast: http://localhost:8080/appcast.xml"

