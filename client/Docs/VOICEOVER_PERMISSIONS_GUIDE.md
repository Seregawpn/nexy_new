# ♿ VoiceOver Permissions Guide - Руководство по разрешениям VoiceOver

## 🎯 Обзор

Nexy AI Assistant включает интеграцию с VoiceOver для пользователей с нарушениями зрения. Это требует специальных разрешений macOS.

## 🔐 Необходимые разрешения

### **1. Accessibility (Доступность)**
- **Что делает:** Позволяет приложению управлять VoiceOver
- **Как получить:** System Preferences → Security & Privacy → Privacy → Accessibility
- **Автоматически:** Приложение запросит разрешение при первом запуске

### **2. Apple Events (AppleScript)**
- **Что делает:** Позволяет выполнять AppleScript команды для управления VoiceOver
- **Включено в:** `entitlements.plist` → `com.apple.security.automation.apple-events`
- **Автоматически:** Разрешается при подписи приложения

## 🛠️ Технические детали

### **VoiceOver управление:**
```bash
# Включение/выключение VoiceOver
osascript -e 'tell application "System Events" to key code 144 using {command down, function down}'
```

### **Проверка статуса VoiceOver:**
```bash
# Проверка запущенных процессов
osascript -e 'tell application "System Events" to get name of every application process'
```

## 📦 Упаковка и подпись

### **entitlements.plist включает:**
```xml
<!-- Apple Events для VoiceOver управления -->
<key>com.apple.security.automation.apple-events</key><true/>
```

### **TCC (Transparency, Consent, and Control):**
- Приложение автоматически запросит разрешения при первом запуске
- Пользователь должен разрешить доступ в System Preferences

## 🚀 Установка и настройка

### **Для пользователей:**
1. Установите приложение через PKG
2. При первом запуске разрешите Accessibility в System Preferences
3. VoiceOver интеграция будет работать автоматически

### **Для разработчиков:**
1. Убедитесь, что `entitlements.plist` содержит Apple Events
2. Подпишите приложение с Hardened Runtime
3. Протестируйте на чистой системе

## 🔍 Диагностика

### **Проверка разрешений:**
```bash
# Проверка Accessibility разрешений
sqlite3 ~/Library/Application\ Support/com.apple.TCC/TCC.db "SELECT * FROM access WHERE service='kTCCServiceAccessibility';"
```

### **Тестирование VoiceOver:**
```bash
# Проверка статуса VoiceOver
osascript -e 'tell application "System Events" to get name of every application process' | grep -i voiceover
```

## ⚠️ Важные замечания

### **Безопасность:**
- VoiceOver управление требует высокого уровня доверия
- Пользователи должны явно разрешить доступ
- Приложение не может принудительно включить VoiceOver

### **Совместимость:**
- Работает на macOS 10.15+ (Catalina и новее)
- Требует включенную функцию Accessibility
- Совместимо с системными настройками VoiceOver

### **Ограничения:**
- Не может читать содержимое VoiceOver
- Может только включать/выключать VoiceOver
- Зависит от системных разрешений пользователя

## 📚 Связанные документы

- `client/Docs/ARCHITECTURE_OVERVIEW.md` - архитектура VoiceOver интеграции
- `client/Docs/PACKAGING_FINAL_GUIDE.md` - упаковка с VoiceOver разрешениями
- `client/modules/voiceover_control/` - техническая реализация

## 🆘 Поддержка

При проблемах с VoiceOver интеграцией:
1. Проверьте разрешения в System Preferences
2. Перезапустите приложение
3. Проверьте логи в Console.app
4. Обратитесь к технической документации
