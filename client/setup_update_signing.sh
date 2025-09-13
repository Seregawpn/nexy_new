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

cd ../../../client

# Шаг 2: Обновление nexy.spec
print_info "Шаг 2: Обновление nexy.spec..."

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

print_header "SETUP COMPLETED"

print_success "🎉 Настройка подписания обновлений завершена!"

echo ""
print_info "📋 Что было сделано:"
echo "   ✅ Сгенерированы ключи EdDSA для Sparkle"
echo "   ✅ Обновлен nexy.spec с реальным публичным ключом"

echo ""
print_info "📝 Следующие шаги:"
echo "   1. Пересоберите приложение: python3 -m PyInstaller nexy.spec --clean"
echo "   2. Создайте новый PKG: ./create_pkg.sh"
echo "   3. Подпишите PKG: cd ../server/updates/keys && ./sign_update.sh ../../../client/YOUR_PKG"
echo "   4. Обновите appcast.xml с реальной подписью"

echo ""
print_warning "🔒 БЕЗОПАСНОСТЬ:"
echo "   • Приватный ключ в: ../server/updates/keys/sparkle_private_key.pem"
echo "   • НЕ публикуйте приватный ключ в репозитории!"

print_success "Готово к распространению обновлений!"

