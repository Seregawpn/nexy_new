#!/bin/bash

# 🚀 Nexy AI Assistant - Создание релиза (упрощенная версия)
# Использование: ./scripts/create_version_release.sh [версия] [описание]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

log "🚀 Создание релиза: $VERSION"
log "📝 Описание: $DESCRIPTION"

# Переход в корень проекта
cd "$(dirname "$0")/.."

# Проверка статуса Git
if [ -n "$(git status --porcelain)" ]; then
    warn "Есть незафиксированные изменения. Коммитим их..."
    git add .
    git commit -m "feat: подготовка к релизу $VERSION

$DESCRIPTION"
    log "✅ Изменения зафиксированы"
fi

# Проверка, что тег не существует
if git tag -l | grep -q "^$VERSION$"; then
    error "Тег $VERSION уже существует!"
    exit 1
fi

# Создание тега
log "🏷️  Создание тега $VERSION..."
git tag -a "$VERSION" -m "$DESCRIPTION

Версия: $VERSION
Дата: $(date)
Описание: $DESCRIPTION"
log "✅ Тег создан"

# Создание временных архивов для GitHub Release
log "📦 Создание архивов для релиза..."
TEMP_DIR="/tmp/nexy_release_$$"
mkdir -p "$TEMP_DIR"

# Создаем архив полного исходного кода
tar -czf "$TEMP_DIR/Nexy-${VERSION}-source.tar.gz" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='client/dist' \
    --exclude='client/build' \
    --exclude='server/__pycache__' \
    --exclude='releases' \
    .

# Создаем архив только клиента
tar -czf "$TEMP_DIR/Nexy-${VERSION}-client.tar.gz" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='client/dist' \
    --exclude='client/build' \
    client/

# Создаем архив только сервера
tar -czf "$TEMP_DIR/Nexy-${VERSION}-server.tar.gz" \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='server/__pycache__' \
    server/

log "✅ Архивы созданы"

# Отправка в GitHub
log "🌐 Отправка в GitHub..."
git push origin main
git push origin "$VERSION"

# Создание GitHub Release
if command -v gh &> /dev/null; then
    log "🚀 Создание GitHub Release..."
    
    # Получаем changelog
    PREV_TAG=$(git describe --tags --abbrev=0 HEAD^ 2>/dev/null || echo "")
    if [ -n "$PREV_TAG" ]; then
        CHANGELOG=$(git log --pretty=format:"- %s" $PREV_TAG..HEAD)
    else
        CHANGELOG=$(git log --pretty=format:"- %s" --reverse)
    fi
    
    # Создаем полное описание
    FULL_DESCRIPTION="$DESCRIPTION

## 📋 Изменения
$CHANGELOG

## 📦 Архивы
- \`Nexy-${VERSION}-source.tar.gz\` - полный исходный код
- \`Nexy-${VERSION}-client.tar.gz\` - только клиентская часть (macOS)
- \`Nexy-${VERSION}-server.tar.gz\` - только серверная часть (Python)

## 🚀 Установка

### Полная установка
1. Скачайте \`Nexy-${VERSION}-source.tar.gz\`
2. Распакуйте: \`tar -xzf Nexy-${VERSION}-source.tar.gz\`
3. Следуйте инструкциям в README.md

### Только клиент (macOS)
1. Скачайте \`Nexy-${VERSION}-client.tar.gz\`
2. Распакуйте: \`tar -xzf Nexy-${VERSION}-client.tar.gz\`
3. Перейдите в папку client: \`cd client\`
4. Установите зависимости: \`pip install -r requirements.txt\`
5. Запустите: \`python main.py\`

### Только сервер
1. Скачайте \`Nexy-${VERSION}-server.tar.gz\`
2. Распакуйте: \`tar -xzf Nexy-${VERSION}-server.tar.gz\`
3. Перейдите в папку server: \`cd server\`
4. Установите зависимости: \`pip install -r requirements.txt\`
5. Запустите: \`python main.py\`

## 🔧 Системные требования
- **Клиент:** macOS 10.15+ (Catalina или новее)
- **Сервер:** Python 3.11+
- **Разрешения:** микрофон, захват экрана, уведомления

## 📞 Поддержка
При возникновении проблем создайте issue в репозитории."

    gh release create "$VERSION" \
        "$TEMP_DIR/Nexy-${VERSION}-source.tar.gz" \
        "$TEMP_DIR/Nexy-${VERSION}-client.tar.gz" \
        "$TEMP_DIR/Nexy-${VERSION}-server.tar.gz" \
        --title "Nexy $VERSION" \
        --notes "$FULL_DESCRIPTION"
    
    log "✅ GitHub Release создан"
else
    warn "GitHub CLI (gh) не установлен. Создайте релиз вручную:"
    warn "https://github.com/Seregawpn/nexy_new/releases/new"
    warn "Тег: $VERSION"
    warn "Файлы: $TEMP_DIR/Nexy-${VERSION}-*.tar.gz"
fi

# Очистка временных файлов
rm -rf "$TEMP_DIR"

# Итоговая информация
echo ""
log "🎉 Релиз $VERSION создан успешно!"
echo ""
info "🏷️  Git тег: $VERSION"
info "🌐 GitHub Release: https://github.com/Seregawpn/nexy_new/releases/tag/$VERSION"
info "📋 Git тег: https://github.com/Seregawpn/nexy_new/tree/$VERSION"

echo ""
log "📊 Доступ к версии:"
log "• Скачать архив: https://github.com/Seregawpn/nexy_new/archive/refs/tags/$VERSION.tar.gz"
log "• Переключиться на версию: git checkout $VERSION"
log "• Вернуться к последней: git checkout main"

echo ""
log "🔄 Для создания следующей версии:"
log "./scripts/create_version_release.sh v1.2.0 'Описание новой версии'"
