#!/bin/bash

# 📋 Nexy AI Assistant - Просмотр всех релизов
# Использование: ./scripts/list_releases.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Переход в корень проекта
cd "$(dirname "$0")/.."

log "📋 Все релизы Nexy AI Assistant:"
echo ""

# Показываем Git теги
log "🏷️  Git теги (версии):"
git tag -l | sort -V | tail -10

echo ""
log "🌐 GitHub Releases:"
if command -v gh &> /dev/null; then
    gh release list --limit 10
else
    warn "GitHub CLI (gh) не установлен. Посмотрите релизы вручную:"
    warn "https://github.com/Seregawpn/nexy_new/releases"
fi

echo ""
log "📊 Статистика:"
total_tags=$(git tag -l | wc -l)
latest_tag=$(git tag -l | sort -V | tail -1)
echo "   Всего релизов: $total_tags"
echo "   Последний релиз: $latest_tag"

echo ""
log "🔗 Полезные ссылки:"
echo "   • Все релизы: https://github.com/Seregawpn/nexy_new/releases"
if [ -n "$latest_tag" ]; then
    echo "   • Скачать последний: https://github.com/Seregawpn/nexy_new/archive/refs/tags/$latest_tag.tar.gz"
fi
echo "   • Создать новый релиз: ./scripts/create_version_release.sh v1.x.0 'Описание'"

echo ""
log "🔄 Команды для работы с версиями:"
echo "   • Переключиться на версию: git checkout v1.0.0"
echo "   • Вернуться к последней: git checkout main"
echo "   • Скачать архив версии: curl -L https://github.com/Seregawpn/nexy_new/archive/refs/tags/v1.0.0.tar.gz"
echo "   • Посмотреть изменения: git show v1.0.0"
