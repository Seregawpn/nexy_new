#!/bin/bash

# Скрипт для проверки разрешений VoiceOver и Accessibility
# Использование: ./scripts/check_voiceover_permissions.sh

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

echo "🔍 Проверка разрешений VoiceOver и Accessibility для Nexy"
echo "=================================================="

# Проверка 1: VoiceOver статус
log "1. Проверка статуса VoiceOver..."
VOICEOVER_STATUS=$(osascript -e 'tell application "System Events" to get name of every application process' 2>/dev/null | grep -i voiceover || echo "not_found")

if [[ "$VOICEOVER_STATUS" == "not_found" ]]; then
    warn "VoiceOver не запущен"
    info "Для тестирования VoiceOver интеграции включите VoiceOver (Cmd+F5)"
else
    log "✅ VoiceOver запущен: $VOICEOVER_STATUS"
fi

# Проверка 2: Accessibility разрешения
log "2. Проверка Accessibility разрешений..."
TCC_DB="$HOME/Library/Application Support/com.apple.TCC/TCC.db"

if [[ -f "$TCC_DB" ]]; then
    # Проверяем разрешения для Nexy
    ACCESSIBILITY_PERMISSIONS=$(sqlite3 "$TCC_DB" "SELECT client, auth_value FROM access WHERE service='kTCCServiceAccessibility' AND client LIKE '%Nexy%';" 2>/dev/null || echo "")
    
    if [[ -n "$ACCESSIBILITY_PERMISSIONS" ]]; then
        log "✅ Accessibility разрешения найдены для Nexy"
        echo "$ACCESSIBILITY_PERMISSIONS"
    else
        warn "Accessibility разрешения не найдены для Nexy"
        info "При первом запуске приложение запросит разрешения"
    fi
else
    warn "База данных TCC не найдена"
fi

# Проверка 3: Apple Events разрешения
log "3. Проверка Apple Events разрешений..."
APPLE_EVENTS_PERMISSIONS=$(sqlite3 "$TCC_DB" "SELECT client, auth_value FROM access WHERE service='kTCCServiceAppleEvents' AND client LIKE '%Nexy%';" 2>/dev/null || echo "")

if [[ -n "$APPLE_EVENTS_PERMISSIONS" ]]; then
    log "✅ Apple Events разрешения найдены для Nexy"
    echo "$APPLE_EVENTS_PERMISSIONS"
else
    warn "Apple Events разрешения не найдены для Nexy"
    info "Эти разрешения включаются автоматически при подписи приложения"
fi

# Проверка 4: Микрофон разрешения
log "4. Проверка разрешений микрофона..."
MICROPHONE_PERMISSIONS=$(sqlite3 "$TCC_DB" "SELECT client, auth_value FROM access WHERE service='kTCCServiceMicrophone' AND client LIKE '%Nexy%';" 2>/dev/null || echo "")

if [[ -n "$MICROPHONE_PERMISSIONS" ]]; then
    log "✅ Разрешения микрофона найдены для Nexy"
    echo "$MICROPHONE_PERMISSIONS"
else
    warn "Разрешения микрофона не найдены для Nexy"
    info "При первом запуске приложение запросит разрешения"
fi

# Проверка 5: Screen Recording разрешения
log "5. Проверка разрешений захвата экрана..."
SCREEN_RECORDING_PERMISSIONS=$(sqlite3 "$TCC_DB" "SELECT client, auth_value FROM access WHERE service='kTCCServiceScreenCapture' AND client LIKE '%Nexy%';" 2>/dev/null || echo "")

if [[ -n "$SCREEN_RECORDING_PERMISSIONS" ]]; then
    log "✅ Разрешения захвата экрана найдены для Nexy"
    echo "$SCREEN_RECORDING_PERMISSIONS"
else
    warn "Разрешения захвата экрана не найдены для Nexy"
    info "При первом запуске приложение запросит разрешения"
fi

# Проверка 6: Тест AppleScript команд
log "6. Тестирование AppleScript команд..."
if osascript -e 'tell application "System Events" to get name of every application process' >/dev/null 2>&1; then
    log "✅ AppleScript команды работают"
else
    error "❌ AppleScript команды не работают"
    info "Проверьте разрешения Accessibility в System Preferences"
fi

# Проверка 7: Тест VoiceOver управления
log "7. Тестирование VoiceOver управления..."
if [[ "$VOICEOVER_STATUS" != "not_found" ]]; then
    log "Тестирование отключения VoiceOver..."
    # ВНИМАНИЕ: Это отключит VoiceOver!
    read -p "Отключить VoiceOver для тестирования? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        osascript -e 'tell application "System Events" to key code 144 using {command down, function down}' >/dev/null 2>&1
        sleep 2
        log "Тестирование включения VoiceOver..."
        osascript -e 'tell application "System Events" to key code 144 using {command down, function down}' >/dev/null 2>&1
        log "✅ VoiceOver управление работает"
    else
        info "Пропущен тест VoiceOver управления"
    fi
else
    info "Пропущен тест VoiceOver управления (VoiceOver не запущен)"
fi

echo ""
echo "=================================================="
log "Проверка завершена!"

# Рекомендации
echo ""
echo "📋 Рекомендации:"
if [[ "$VOICEOVER_STATUS" == "not_found" ]]; then
    echo "• Включите VoiceOver для тестирования интеграции (Cmd+F5)"
fi

if [[ -z "$ACCESSIBILITY_PERMISSIONS" ]]; then
    echo "• При первом запуске Nexy разрешите доступ в System Preferences → Security & Privacy → Privacy → Accessibility"
fi

if [[ -z "$MICROPHONE_PERMISSIONS" ]]; then
    echo "• При первом запуске Nexy разрешите доступ к микрофону в System Preferences"
fi

if [[ -z "$SCREEN_RECORDING_PERMISSIONS" ]]; then
    echo "• При первом запуске Nexy разрешите захват экрана в System Preferences"
fi

echo ""
echo "🔗 Полезные ссылки:"
echo "• System Preferences → Security & Privacy → Privacy"
echo "• System Preferences → Accessibility → VoiceOver"
echo "• Документация: client/Docs/VOICEOVER_PERMISSIONS_GUIDE.md"
