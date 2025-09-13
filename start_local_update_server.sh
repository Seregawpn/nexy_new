#!/bin/bash

# Start Local Update Server
# Запуск локального сервера обновлений для тестирования

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

print_header "LOCAL UPDATE SERVER"

# Проверяем, что мы в правильной директории
if [ ! -f "local_update_server.py" ]; then
    print_error "Скрипт должен запускаться из директории server/"
    exit 1
fi

# Проверяем, что PKG файл существует
PKG_FILE="updates/downloads/Nexy_AI_Voice_Assistant_v1.71.0.pkg"
if [ ! -f "$PKG_FILE" ]; then
    print_warning "PKG файл не найден: $PKG_FILE"
    print_info "Копируем PKG из клиентской директории..."
    
    if [ -f "../client/Nexy_AI_Voice_Assistant_v1.71.0.pkg" ]; then
        cp "../client/Nexy_AI_Voice_Assistant_v1.71.0.pkg" "$PKG_FILE"
        print_success "PKG файл скопирован"
    else
        print_error "PKG файл не найден в клиентской директории"
        exit 1
    fi
fi

# Проверяем, что appcast.xml существует
if [ ! -f "updates/appcast.xml" ]; then
    print_error "AppCast файл не найден: updates/appcast.xml"
    exit 1
fi

print_success "Все файлы готовы для тестирования"

echo ""
print_info "🌐 Локальный сервер обновлений будет доступен по адресу:"
print_info "   http://localhost:8080"
echo ""
print_info "📡 Endpoints:"
print_info "   • AppCast: http://localhost:8080/appcast.xml"
print_info "   • Update Check: http://localhost:8080/api/update/check?current=1.70.0"
print_info "   • PKG Download: http://localhost:8080/downloads/Nexy_AI_Voice_Assistant_v1.71.0.pkg"
echo ""
print_info "🔧 Для тестирования в приложении:"
print_info "   1. Запустите приложение Nexy"
print_info "   2. Приложение автоматически проверит обновления"
print_info "   3. Если найдено обновление, Sparkle предложит его установить"
echo ""
print_warning "⏹️  Нажмите Ctrl+C для остановки сервера"
echo ""

# Запускаем сервер
python3 local_update_server.py

