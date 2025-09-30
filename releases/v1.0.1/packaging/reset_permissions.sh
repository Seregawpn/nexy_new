#!/bin/bash
set -euo pipefail

echo "🔄 Сброс TCC разрешений для Nexy AI Assistant"
echo "=============================================="

BUNDLE_ID="com.nexy.assistant"

echo "📋 Сбрасываем разрешения для bundle ID: $BUNDLE_ID"

# Сбрасываем все разрешения
echo "1️⃣ Сброс Microphone..."
tccutil reset Microphone "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "2️⃣ Сброс Screen Recording..."
tccutil reset ScreenCapture "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "3️⃣ Сброс Accessibility..."
tccutil reset Accessibility "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "4️⃣ Сброс Input Monitoring..."
tccutil reset ListenEvent "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "5️⃣ Сброс Apple Events..."
tccutil reset AppleEvents "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo ""
echo "✅ TCC разрешения сброшены"
echo ""
echo "📝 Следующие шаги:"
echo "1. Запустите приложение из /Applications/Nexy.app"
echo "2. Разрешите доступ к микрофону в системном диалоге"
echo "3. В настройках macOS включите:"
echo "   - Конфиденциальность → Доступность → Nexy"
echo "   - Конфиденциальность → Запись экрана → Nexy"
echo "   - Конфиденциальность → Ввод с клавиатуры → Nexy"
echo ""
echo "🔗 Быстрые ссылки на настройки:"
echo "   open \"x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone\""
echo "   open \"x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility\""
echo "   open \"x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture\""
echo "   open \"x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent\""



