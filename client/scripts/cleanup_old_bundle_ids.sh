#!/bin/bash

# Скрипт для очистки старых Bundle ID из системы macOS
# Исправляет ошибки TCC с com.nexy.voiceassistant

echo "🧹 Очистка старых Bundle ID из системы macOS..."

# Очищаем TCC базу данных для старых Bundle ID
echo "📋 Очистка TCC базы данных..."
tccutil reset Microphone com.nexy.voiceassistant 2>/dev/null || true
tccutil reset ScreenCapture com.nexy.voiceassistant 2>/dev/null || true
tccutil reset Accessibility com.nexy.voiceassistant 2>/dev/null || true
tccutil reset ListenEvent com.nexy.voiceassistant 2>/dev/null || true

tccutil reset Microphone com.sergiyzasorin.nexy.voiceassistant 2>/dev/null || true
tccutil reset ScreenCapture com.sergiyzasorin.nexy.voiceassistant 2>/dev/null || true
tccutil reset Accessibility com.sergiyzasorin.nexy.voiceassistant 2>/dev/null || true
tccutil reset ListenEvent com.sergiyzasorin.nexy.voiceassistant 2>/dev/null || true

# Очищаем LaunchServices базу данных
echo "🔍 Очистка LaunchServices базы данных..."
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -kill -r -domain local -domain system -domain user 2>/dev/null || true

# Очищаем кэш приложений
echo "🗑️ Очистка кэша приложений..."
rm -rf ~/Library/Caches/com.nexy.voiceassistant* 2>/dev/null || true
rm -rf ~/Library/Caches/com.sergiyzasorin.nexy.voiceassistant* 2>/dev/null || true

# Очищаем настройки приложений
echo "⚙️ Очистка настроек приложений..."
rm -rf ~/Library/Preferences/com.nexy.voiceassistant* 2>/dev/null || true
rm -rf ~/Library/Preferences/com.sergiyzasorin.nexy.voiceassistant* 2>/dev/null || true

# Очищаем LaunchAgents
echo "🚀 Очистка LaunchAgents..."
rm -rf ~/Library/LaunchAgents/com.nexy.voiceassistant* 2>/dev/null || true
rm -rf ~/Library/LaunchAgents/com.sergiyzasorin.nexy.voiceassistant* 2>/dev/null || true

# Останавливаем и удаляем старые процессы
echo "🛑 Остановка старых процессов..."
pkill -f "com.nexy.voiceassistant" 2>/dev/null || true
pkill -f "com.sergiyzasorin.nexy.voiceassistant" 2>/dev/null || true

# Очищаем TCC для правильного Bundle ID
echo "✅ Настройка правильного Bundle ID..."
tccutil reset Microphone com.nexy.assistant 2>/dev/null || true
tccutil reset ScreenCapture com.nexy.assistant 2>/dev/null || true
tccutil reset Accessibility com.nexy.assistant 2>/dev/null || true
tccutil reset ListenEvent com.nexy.assistant 2>/dev/null || true

echo "✅ Очистка завершена!"
echo "📝 Теперь можно пересобрать и переустановить приложение с правильным Bundle ID"
