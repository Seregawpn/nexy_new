#!/bin/bash

# Скрипт сборки macOS приложения "Голосовой Ассистент"
# Автор: AI Assistant
# Дата: $(date)

set -e  # Останавливаем выполнение при ошибке

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    print_error "Скрипт должен запускаться из директории client/"
    exit 1
fi

print_info "🚀 Начинаю сборку macOS приложения (ARM64 ONLY)..."

# Проверяем архитектуру системы
print_info "🔍 Проверяю архитектуру системы..."
if [[ $(uname -m) != "arm64" ]]; then
    print_error "❌ НЕПОДДЕРЖИВАЕМАЯ АРХИТЕКТУРА!"
    print_error "Это приложение работает ТОЛЬКО на Apple Silicon (M1/M2)"
    print_error "Intel Mac НЕ поддерживается"
    exit 1
fi
print_success "✅ ARM64 архитектура подтверждена"

# Проверяем наличие PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    print_error "PyInstaller не установлен. Устанавливаю..."
    pip install pyinstaller
fi

print_success "PyInstaller найден"

# Проверяем наличие spec файла
SPEC_FILE="build/pyinstaller/app.spec"
if [ ! -f "$SPEC_FILE" ]; then
    print_error "Spec файл не найден: $SPEC_FILE"
    exit 1
fi

print_success "Spec файл найден"

# Очищаем предыдущие сборки
print_info "🧹 Очищаю предыдущие сборки..."
rm -rf build/pyinstaller/dist
rm -rf build/pyinstaller/build

# Создаем директории для сборки
mkdir -p build/pyinstaller/dist
mkdir -p build/pyinstaller/build

print_success "Директории для сборки созданы"

# Запускаем сборку
print_info "🔨 Запускаю PyInstaller..."
pyinstaller "$SPEC_FILE" --distpath build/pyinstaller/dist --workpath build/pyinstaller/build

# Проверяем результат сборки
APP_PATH="build/pyinstaller/dist/Nexy.app"
if [ -d "$APP_PATH" ]; then
    print_success "Приложение успешно собрано!"
    
    # Показываем информацию о размере
    APP_SIZE=$(du -sh "$APP_PATH" | cut -f1)
    print_info "Размер приложения: $APP_SIZE"
    
    # Показываем структуру
    print_info "Структура .app файла:"
    tree "$APP_PATH" -L 3 2>/dev/null || ls -la "$APP_PATH"
    
    print_success "🎉 Сборка завершена успешно!"
    print_info "Приложение находится в: $APP_PATH"
    
else
    print_error "Ошибка сборки! .app файл не создан"
    exit 1
fi

# Проверяем права доступа
print_info "🔐 Проверяю права доступа..."
chmod +x "$APP_PATH/Contents/MacOS/VoiceAssistant"

print_success "Права доступа настроены"

# Создаем архив для распространения
print_info "📦 Создаю архив для распространения..."
cd build/pyinstaller/dist
tar -czf Nexy_macOS.tar.gz Nexy.app
cd ../../..

ARCHIVE_PATH="build/pyinstaller/dist/Nexy_macOS.tar.gz"
if [ -f "$ARCHIVE_PATH" ]; then
    ARCHIVE_SIZE=$(du -sh "$ARCHIVE_PATH" | cut -f1)
    print_success "Архив создан: $ARCHIVE_PATH ($ARCHIVE_SIZE)"
else
    print_warning "Не удалось создать архив"
fi

print_info "🎯 Сборка завершена!"
print_info "📁 Файлы находятся в: build/pyinstaller/dist/"
print_info "📱 Приложение: Nexy.app"
print_info "📦 Архив: Nexy_macOS.tar.gz"

# Инструкции по установке
echo ""
print_info "📋 ИНСТРУКЦИИ ПО УСТАНОВКЕ:"
echo "1. Распакуйте архив VoiceAssistant_macOS.tar.gz"
echo "2. Перетащите VoiceAssistant.app в папку Applications"
echo "3. Запустите приложение из Applications"
echo "4. Разрешите доступ к микрофону и экрану при запросе"
echo "5. Настройте автозапуск в System Preferences > Users & Groups > Login Items"
echo ""
print_warning "⚠️  ВАЖНО: Приложение требует разрешения на микрофон и экран!"
print_warning "⚠️  ВАЖНО: Для автозапуска добавьте в Login Items вручную!"


