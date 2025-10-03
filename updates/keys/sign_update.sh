#!/bin/bash

# Sign Update File with Sparkle EdDSA
# Подписание файла обновления ключом EdDSA для Sparkle

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

if [ $# -ne 1 ]; then
    print_error "Использование: $0 <file_to_sign>"
    print_info "Пример: $0 /path/to/Nexy_1.71.0.pkg"
    exit 1
fi

FILE_TO_SIGN="$1"
PRIVATE_KEY_FILE="sparkle_private_key.pem"

# Проверяем, что файл существует
if [ ! -f "$FILE_TO_SIGN" ]; then
    print_error "Файл не найден: $FILE_TO_SIGN"
    exit 1
fi

# Проверяем, что приватный ключ существует
if [ ! -f "$PRIVATE_KEY_FILE" ]; then
    print_error "Приватный ключ не найден: $PRIVATE_KEY_FILE"
    print_info "Сначала запустите: ./generate_sparkle_keys.sh"
    exit 1
fi

print_info "Подписание файла: $(basename "$FILE_TO_SIGN")"

# Получаем размер файла
FILE_SIZE=$(stat -f%z "$FILE_TO_SIGN" 2>/dev/null || stat -c%s "$FILE_TO_SIGN" 2>/dev/null)
print_info "Размер файла: $FILE_SIZE байт"

# Создаем подпись
print_info "Создание EdDSA подписи..."
SIGNATURE=$(openssl pkeyutl -sign -inkey "$PRIVATE_KEY_FILE" -rawin -in "$FILE_TO_SIGN" | base64 | tr -d '\n')

if [ -z "$SIGNATURE" ]; then
    print_error "Не удалось создать подпись"
    exit 1
fi

print_success "Подпись создана успешно!"

# Получаем имя файла без пути
FILENAME=$(basename "$FILE_TO_SIGN")

print_info "📄 Информация для appcast.xml:"
echo ""
echo -e "${YELLOW}Файл:${NC} $FILENAME"
echo -e "${YELLOW}Размер:${NC} $FILE_SIZE"
echo -e "${YELLOW}EdDSA подпись:${NC}"
echo -e "${GREEN}$SIGNATURE${NC}"
echo ""

print_info "📝 XML для appcast.xml:"
echo ""
cat << EOF
<enclosure url="https://your-server.com/downloads/$FILENAME"
           sparkle:version="1.71.0"
           sparkle:shortVersionString="1.71.0"
           length="$FILE_SIZE"
           type="application/octet-stream"
           sparkle:edSignature="$SIGNATURE"/>
EOF

echo ""
print_success "🎉 Файл подписан успешно!"
print_info "💡 Скопируйте XML выше в ваш appcast.xml"

