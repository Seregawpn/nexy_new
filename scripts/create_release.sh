#!/bin/bash

# Скрипт для создания релиза Nexy AI Assistant
# Использование: ./scripts/create_release.sh [version] [message]
# Пример: ./scripts/create_release.sh v3.5.0 "VoiceOver integration completed"

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${BLUE}[RELEASE]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Проверка аргументов
if [ $# -lt 2 ]; then
    error "Использование: $0 <version> <message>"
    echo "Пример: $0 v3.5.0 'VoiceOver integration completed'"
    exit 1
fi

VERSION=$1
MESSAGE=$2

# Проверка формата версии (semantic versioning)
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Неверный формат версии. Используйте: vX.Y.Z (например, v3.5.0)"
fi

log "Создание релиза $VERSION..."

# Переход в корень проекта
cd "$(dirname "$0")/.."

# Проверка, что мы в git репозитории
if [ ! -d ".git" ]; then
    error "Не найден git репозиторий"
fi

# Проверка, что нет несохраненных изменений
if [ -n "$(git status --porcelain)" ]; then
    error "Есть несохраненные изменения. Сначала закоммитьте их:"
    git status --short
fi

# Проверка, что тег не существует
if git tag -l | grep -q "^$VERSION$"; then
    error "Тег $VERSION уже существует"
fi

# Проверка, что мы на main ветке
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    warning "Вы не на main ветке (текущая: $CURRENT_BRANCH)"
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Создание тега
log "Создание тега $VERSION..."
git tag -a "$VERSION" -m "$MESSAGE"

# Отправка тега в GitHub
log "Отправка тега в GitHub..."
git push origin "$VERSION"

# Создание GitHub Release через GitHub CLI (если установлен)
if command -v gh &> /dev/null; then
    log "Создание GitHub Release..."
    
    # Создание release notes
    RELEASE_NOTES="## Что нового в $VERSION

$MESSAGE

### Изменения:
$(git log --pretty=format:"- %s" $(git describe --tags --abbrev=0 HEAD^)..HEAD)

### Установка:
1. Скачайте \`Nexy.pkg\` из Assets ниже
2. Установите через двойной клик
3. Разрешите необходимые разрешения в System Preferences

### Требования:
- macOS 12.0+
- Разрешения: Microphone, Screen Recording, Accessibility, VoiceOver"
    
    # Создание релиза
    gh release create "$VERSION" \
        --title "Nexy AI Assistant $VERSION" \
        --notes "$RELEASE_NOTES" \
        --latest
    
    success "GitHub Release $VERSION создан успешно!"
else
    warning "GitHub CLI не установлен. Создайте релиз вручную на GitHub.com"
    echo "URL: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^/]*\/[^/]*\)\.git/\1/')/releases/new?tag=$VERSION"
fi

# Обновление версии в конфигурации
log "Обновление версии в конфигурации..."
if [ -f "client/config/unified_config.yaml" ]; then
    # Обновление версии в конфиге (если есть поле version)
    sed -i.bak "s/version: .*/version: $VERSION/" client/config/unified_config.yaml 2>/dev/null || true
    rm -f client/config/unified_config.yaml.bak
fi

# Создание файла версии
echo "$VERSION" > VERSION
git add VERSION
git commit -m "chore: bump version to $VERSION" || true
git push origin main

success "Релиз $VERSION создан успешно!"
log "Тег: $VERSION"
log "Сообщение: $MESSAGE"
log "Следующий шаг: Создайте PKG файл и прикрепите к релизу"

echo
echo "📦 Для создания PKG файла выполните:"
echo "   ./packaging/build_final.sh"
echo
echo "🔗 Затем прикрепите PKG к релизу на GitHub"
