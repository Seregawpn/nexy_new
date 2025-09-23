#!/bin/bash
set -euo pipefail

echo "🧹 Очистка старых Bundle ID из системы macOS..."

IDS=(
  com.nexy.voiceassistant
  com.sergiyzasorin.nexy.voiceassistant
  com.nexy.assistant
)

echo "🔄 Сброс TCC записей..."
for id in "${IDS[@]}"; do
  for service in All Microphone ScreenCapture Camera ListenEvent Accessibility; do
    tccutil reset "$service" "$id" 2>/dev/null || true
  done
done

echo "🗂 Перестроение LaunchServices базы..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister \
  -kill -r -domain local -domain system -domain user 2>/dev/null || true

echo "🧽 Очистка кэшей/настроек..."
for id in com.nexy.voiceassistant com.sergiyzasorin.nexy.voiceassistant; do
  rm -rf "$HOME/Library/Caches/${id}"* 2>/dev/null || true
  rm -rf "$HOME/Library/Preferences/${id}"* 2>/dev/null || true
  rm -rf "$HOME/Library/LaunchAgents/${id}"* 2>/dev/null || true
done

echo "🛑 Остановка возможных старых процессов..."
pkill -f "com.nexy.voiceassistant" 2>/dev/null || true
pkill -f "com.sergiyzasorin.nexy.voiceassistant" 2>/dev/null || true

echo "✅ Очистка завершена"
echo "ℹ️ При первом запуске заново подтвердите системные разрешения для com.nexy.assistant"


