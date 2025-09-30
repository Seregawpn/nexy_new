#!/bin/bash

# Скрипт для создания новой версии в отдельной папке
# Использование: ./scripts/create_version_release.sh [версия] [описание]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода сообщений
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка аргументов
if [ $# -lt 1 ]; then
    error "Использование: $0 <версия> [описание]"
    error "Пример: $0 v1.1.0 'Новые функции'"
    exit 1
fi

VERSION=$1
DESCRIPTION=${2:-"Новая версия $VERSION"}

# Проверка формата версии
if [[ ! $VERSION =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Неверный формат версии. Используйте: v1.0.0"
    exit 1
fi

log "Создание релиза версии: $VERSION"
log "Описание: $DESCRIPTION"

# Переход в корень проекта
cd "$(dirname "$0")/.."

# Проверка статуса Git
if [ -n "$(git status --porcelain)" ]; then
    warn "Есть незафиксированные изменения. Коммитим их..."
    git add .
    git commit -m "feat: подготовка к релизу $VERSION

$DESCRIPTION"
fi

# Создание тега
log "Создание тега $VERSION..."
git tag -a "$VERSION" -m "$DESCRIPTION

Версия: $VERSION
Дата: $(date)
Описание: $DESCRIPTION"

# Создание папки для версии
VERSION_DIR="releases/$VERSION"
log "Создание папки версии: $VERSION_DIR"
mkdir -p "$VERSION_DIR"

# Копирование файлов в папку версии
log "Копирование файлов в папку версии..."
cp -r client/ "$VERSION_DIR/"
cp -r server/ "$VERSION_DIR/"
cp -r docs/ "$VERSION_DIR/" 2>/dev/null || true
cp -r scripts/ "$VERSION_DIR/" 2>/dev/null || true
cp README.md "$VERSION_DIR/" 2>/dev/null || true
cp .gitignore "$VERSION_DIR/" 2>/dev/null || true

# Создание файла версии
cat > "$VERSION_DIR/VERSION" << EOF
VERSION=$VERSION
DATE=$(date)
DESCRIPTION=$DESCRIPTION
GIT_COMMIT=$(git rev-parse HEAD)
GIT_TAG=$VERSION
EOF

# Создание README для версии
cat > "$VERSION_DIR/README_VERSION.md" << EOF
# Nexy $VERSION

**Дата релиза:** $(date)
**Git тег:** $VERSION
**Git коммит:** $(git rev-parse HEAD)

## Описание
$DESCRIPTION

## Установка
См. основную документацию в папке docs/

## Изменения
- См. git log для детального списка изменений
- Тег: \`git show $VERSION\`

## Архив
Эта папка содержит полную копию кода на момент релиза $VERSION
EOF

# Создание архива версии
log "Создание архива версии..."
cd releases/
tar -czf "${VERSION}.tar.gz" "$VERSION/"
zip -r "${VERSION}.zip" "$VERSION/"
cd ..

# Отправка в GitHub
log "Отправка в GitHub..."
git push origin main
git push origin "$VERSION"

# Создание GitHub Release (если установлен gh CLI)
if command -v gh &> /dev/null; then
    log "Создание GitHub Release..."
    gh release create "$VERSION" \
        "releases/${VERSION}.tar.gz" \
        "releases/${VERSION}.zip" \
        --title "Nexy $VERSION" \
        --notes "$DESCRIPTION

## Архивы
- \`${VERSION}.tar.gz\` - исходный код (tar.gz)
- \`${VERSION}.zip\` - исходный код (zip)

## Установка
См. документацию в папке docs/ для инструкций по установке.

## Изменения
См. git log для детального списка изменений."
else
    warn "GitHub CLI (gh) не установлен. Создайте релиз вручную:"
    warn "https://github.com/Seregawpn/nexy_new/releases/new"
    warn "Тег: $VERSION"
    warn "Файлы: releases/${VERSION}.tar.gz, releases/${VERSION}.zip"
fi

# Итоговая информация
log "✅ Релиз $VERSION создан успешно!"
log "📁 Папка версии: $VERSION_DIR"
log "📦 Архивы: releases/${VERSION}.tar.gz, releases/${VERSION}.zip"
log "🏷️  Git тег: $VERSION"
log "🌐 GitHub: https://github.com/Seregawpn/nexy_new/releases/tag/$VERSION"

echo ""
log "Структура релизов:"
tree releases/ -L 2 2>/dev/null || ls -la releases/

echo ""
log "Для создания следующей версии:"
log "./scripts/create_version_release.sh v1.2.0 'Описание новой версии'"
