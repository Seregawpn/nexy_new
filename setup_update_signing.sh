#!/bin/bash

# Complete Update Signing Setup
# Полная настройка подписания обновлений для Sparkle

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

print_header "SPARKLE UPDATE SIGNING SETUP"

# Шаг 1: Генерация ключей
print_info "Шаг 1: Генерация ключей Sparkle..."
cd ../server/updates/keys
./generate_sparkle_keys.sh

# Читаем сгенерированный публичный ключ
if [ -f "sparkle_config.txt" ]; then
    PUBLIC_KEY=$(grep "SUPublicEDKey=" sparkle_config.txt | cut -d'=' -f2)
    print_success "Публичный ключ получен: ${PUBLIC_KEY:0:20}..."
else
    print_error "Не удалось найти конфигурацию ключей"
    exit 1
fi

cd ../../..

# Шаг 2: Обновление nexy.spec
print_info "Шаг 2: Обновление client/nexy.spec..."
cd client

# Создаем backup
cp nexy.spec nexy.spec.backup

# Заменяем заглушку на реальный ключ
sed -i.bak "s/'SUPublicEDKey': 'YOUR_ED_KEY'/'SUPublicEDKey': '$PUBLIC_KEY'/g" nexy.spec

# Обновляем URL сервера
read -p "🌐 Введите URL вашего сервера (например, https://your-server.com): " SERVER_URL
if [ -n "$SERVER_URL" ]; then
    sed -i.bak "s|'SUFeedURL': 'https://your-server.com/appcast.xml'|'SUFeedURL': '$SERVER_URL/appcast.xml'|g" nexy.spec
    print_success "URL сервера обновлен: $SERVER_URL/appcast.xml"
fi

print_success "nexy.spec обновлен с реальным публичным ключом"

# Шаг 3: Подписание текущего PKG
print_info "Шаг 3: Подписание текущего PKG файла..."

# Ищем последний PKG файл
LATEST_PKG=$(ls -t Nexy_AI_Voice_Assistant_v*.pkg 2>/dev/null | head -1)

if [ -n "$LATEST_PKG" ]; then
    print_info "Найден PKG файл: $LATEST_PKG"
    
    # Подписываем PKG
    cd ../server/updates/keys
    ./sign_update.sh "../../../client/$LATEST_PKG"
    
    print_success "PKG файл подписан!"
    
    # Сохраняем информацию для обновления appcast.xml
    SIGNATURE_INFO_FILE="latest_signature.txt"
    echo "# Информация о последней подписи" > "$SIGNATURE_INFO_FILE"
    echo "FILE=$LATEST_PKG" >> "$SIGNATURE_INFO_FILE"
    echo "SIGNED_AT=$(date)" >> "$SIGNATURE_INFO_FILE"
    
    print_info "📄 Информация о подписи сохранена в: $SIGNATURE_INFO_FILE"
    
    cd ../../../client
else
    print_warning "PKG файл не найден. Сначала создайте PKG с помощью ./create_pkg.sh"
fi

# Шаг 4: Создание демонстрационного appcast.xml
print_info "Шаг 4: Создание обновленного appcast.xml..."
cd ../server/updates

DEMO_APPCAST="appcast_template.xml"
cat > "$DEMO_APPCAST" << EOF
<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle">
    <channel>
        <title>Nexy AI Voice Assistant Updates</title>
        <description>Автоматические обновления для Nexy AI Voice Assistant</description>
        <language>ru</language>
        <link>$SERVER_URL/</link>
        <lastBuildDate>$(date -u +"%a, %d %b %Y %H:%M:%S +0000")</lastBuildDate>
        
        <item>
            <title>Nexy AI Voice Assistant v1.71.0</title>
            <description>
                <![CDATA[
                <h2>Что нового в версии 1.71.0:</h2>
                <ul>
                    <li>✨ Добавлена система автообновлений через Sparkle</li>
                    <li>🔐 Полная интеграция с macOS Gatekeeper</li>
                    <li>♿ Улучшена поддержка accessibility</li>
                    <li>🐛 Исправлены мелкие ошибки</li>
                    <li>⚡ Оптимизирована производительность</li>
                </ul>
                <p><strong>Важно:</strong> Это обновление устанавливается автоматически для вашего удобства.</p>
                ]]>
            </description>
            <pubDate>$(date -u +"%a, %d %b %Y %H:%M:%S +0000")</pubDate>
            <!-- ЗАМЕНИТЕ НА РЕАЛЬНУЮ ПОДПИСЬ ИЗ sign_update.sh -->
            <enclosure url="$SERVER_URL/downloads/Nexy_AI_Voice_Assistant_v1.71.0.pkg"
                       sparkle:version="1.71.0"
                       sparkle:shortVersionString="1.71.0"
                       length="61438331"
                       type="application/octet-stream"
                       sparkle:edSignature="REPLACE_WITH_REAL_SIGNATURE"/>
        </item>
    </channel>
</rss>
EOF

print_success "Шаблон appcast.xml создан: $DEMO_APPCAST"

cd ../../client

print_header "SETUP COMPLETED"

print_success "🎉 Настройка подписания обновлений завершена!"

echo ""
print_info "📋 Что было сделано:"
echo "   ✅ Сгенерированы ключи EdDSA для Sparkle"
echo "   ✅ Обновлен nexy.spec с реальным публичным ключом"
echo "   ✅ Подписан текущий PKG файл (если найден)"
echo "   ✅ Создан шаблон appcast.xml"

echo ""
print_info "📝 Следующие шаги:"
echo "   1. Пересоберите приложение: python3 -m PyInstaller nexy.spec --clean"
echo "   2. Создайте новый PKG: ./create_pkg.sh"
echo "   3. Подпишите PKG: cd ../server/updates/keys && ./sign_update.sh ../../../client/YOUR_PKG"
echo "   4. Обновите appcast.xml с реальной подписью"
echo "   5. Загрузите файлы на сервер"

echo ""
print_warning "🔒 БЕЗОПАСНОСТЬ:"
echo "   • Приватный ключ в: ../server/updates/keys/sparkle_private_key.pem"
echo "   • НЕ публикуйте приватный ключ в репозитории!"
echo "   • Сделайте резервную копию ключей!"

print_success "Готово к распространению обновлений!"

