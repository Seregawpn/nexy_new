#!/bin/bash

# Быстрый скрипт для создания релиза с PKG файлом
# Использование: ./scripts/quick_release.sh [version] [message]

set -e

# Цвета
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[QUICK-RELEASE]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка аргументов
if [ $# -lt 2 ]; then
    echo "Использование: $0 <version> <message>"
    echo "Пример: $0 v3.5.1 'Fix VoiceOver bug'"
    exit 1
fi

VERSION=$1
MESSAGE=$2

log "Создание быстрого релиза $VERSION..."

# Переход в корень проекта
cd "$(dirname "$0")/.."

# 1. Создание тега и релиза
log "Создание тега и GitHub релиза..."
./scripts/create_release.sh "$VERSION" "$MESSAGE"

# 2. Создание PKG файла
log "Создание PKG файла..."
if [ -f "./packaging/build_final.sh" ]; then
    ./packaging/build_final.sh
else
    warning "Скрипт сборки не найден. Создайте PKG вручную."
fi

# 3. Прикрепление PKG к релизу
if [ -f "dist/Nexy.pkg" ] && command -v gh &> /dev/null; then
    log "Прикрепление PKG к релизу..."
    gh release upload "$VERSION" "dist/Nexy.pkg" --clobber
    success "PKG файл прикреплен к релизу $VERSION"
else
    warning "PKG файл не найден или GitHub CLI не установлен."
    echo "Прикрепите PKG файл вручную к релизу на GitHub"
fi

success "Быстрый релиз $VERSION создан!"
log "Релиз: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\/[^/]*\)\.git/\1/')/releases/tag/$VERSION"
