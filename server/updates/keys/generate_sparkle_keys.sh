#!/bin/bash

# Generate Sparkle EdDSA Keys for Update Signing
# Генерация ключей EdDSA для подписания обновлений Sparkle

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

print_header "SPARKLE KEYS GENERATION"

# Проверяем, что OpenSSL доступен
if ! command -v openssl &> /dev/null; then
    print_error "OpenSSL не найден. Установите OpenSSL для генерации ключей."
    exit 1
fi

# Имена файлов ключей
PRIVATE_KEY_FILE="sparkle_private_key.pem"
PUBLIC_KEY_FILE="sparkle_public_key.pem"
CONFIG_FILE="sparkle_config.txt"

print_info "Генерация EdDSA ключей для Sparkle..."

# Генерируем приватный ключ Ed25519
openssl genpkey -algorithm Ed25519 -out "$PRIVATE_KEY_FILE"
print_success "Приватный ключ создан: $PRIVATE_KEY_FILE"

# Извлекаем публичный ключ
openssl pkey -in "$PRIVATE_KEY_FILE" -pubout -out "$PUBLIC_KEY_FILE"
print_success "Публичный ключ создан: $PUBLIC_KEY_FILE"

# Извлекаем публичный ключ в base64 для Sparkle
PUBLIC_KEY_BASE64=$(openssl pkey -in "$PRIVATE_KEY_FILE" -pubout -outform DER | tail -c 32 | base64)

print_success "Ключи сгенерированы успешно!"

# Создаем конфигурационный файл
cat > "$CONFIG_FILE" << EOF
# Sparkle Update Keys Configuration
# Конфигурация ключей для обновлений Sparkle

# Public Key (для Info.plist в приложении)
SUPublicEDKey=$PUBLIC_KEY_BASE64

# Private Key File (для подписания обновлений)
PRIVATE_KEY_FILE=$PRIVATE_KEY_FILE

# Public Key File
PUBLIC_KEY_FILE=$PUBLIC_KEY_FILE

# Команда для подписания файла:
# openssl pkeyutl -sign -inkey $PRIVATE_KEY_FILE -rawin -in <file> | base64

# Команда для проверки подписи:
# echo "<signature_base64>" | base64 -d | openssl pkeyutl -verify -pubin -inkey $PUBLIC_KEY_FILE -rawin -in <file>

# Пример использования в appcast.xml:
# sparkle:edSignature="<signature_base64>"

EOF

print_success "Конфигурация создана: $CONFIG_FILE"

# Устанавливаем безопасные права доступа
chmod 600 "$PRIVATE_KEY_FILE"
chmod 644 "$PUBLIC_KEY_FILE"
chmod 644 "$CONFIG_FILE"

print_info "Права доступа установлены:"
print_info "  $PRIVATE_KEY_FILE: 600 (только владелец)"
print_info "  $PUBLIC_KEY_FILE: 644 (читаемый всеми)"

print_header "CONFIGURATION"

echo ""
print_info "📝 Добавьте в client/nexy.spec:"
echo -e "${YELLOW}'SUPublicEDKey': '$PUBLIC_KEY_BASE64'${NC}"

echo ""
print_info "📝 Публичный ключ для копирования:"
echo -e "${GREEN}$PUBLIC_KEY_BASE64${NC}"

echo ""
print_info "🔐 Для подписания обновлений используйте:"
echo -e "${YELLOW}./sign_update.sh <file_to_sign>${NC}"

print_header "SECURITY WARNING"
print_warning "🔒 ВАЖНО: Сохраните приватный ключ в безопасном месте!"
print_warning "🔒 НЕ ПУБЛИКУЙТЕ приватный ключ в репозитории!"
print_warning "🔒 Сделайте резервную копию ключей!"

print_success "🎉 Ключи Sparkle сгенерированы успешно!"

