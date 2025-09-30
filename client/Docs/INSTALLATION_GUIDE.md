# 📦 Installation Guide - Руководство по установке Nexy

## 🎯 Обзор

Это руководство поможет вам установить и настроить Nexy AI Assistant на macOS с полной поддержкой VoiceOver интеграции.

## 🔐 Необходимые разрешения

### **1. Микрофон**
- **Назначение:** Запись голосовых команд
- **Как получить:** System Preferences → Security & Privacy → Privacy → Microphone
- **Автоматически:** Запрашивается при первом запуске

### **2. Захват экрана**
- **Назначение:** Автоматический захват экрана при обработке команд
- **Как получить:** System Preferences → Security & Privacy → Privacy → Screen Recording
- **Автоматически:** Запрашивается при первом запуске

### **3. Доступность (Accessibility)**
- **Назначение:** Управление VoiceOver для пользователей с нарушениями зрения
- **Как получить:** System Preferences → Security & Privacy → Privacy → Accessibility
- **Автоматически:** Запрашивается при первом запуске

### **4. Уведомления**
- **Назначение:** Системные уведомления о статусе приложения
- **Как получить:** System Preferences → Security & Privacy → Privacy → Notifications
- **Автоматически:** Запрашивается при первом запуске

## 🚀 Установка

### **Вариант 1: Установка из PKG (рекомендуется)**

1. **Скачайте PKG файл**
   - Перейдите на [Releases](https://github.com/Seregawpn/nexy_new/releases)
   - Скачайте последнюю версию `Nexy-x.x.x.pkg`

2. **Установите приложение**
   ```bash
   # Двойной клик по PKG файлу или через терминал:
   sudo installer -pkg Nexy-x.x.x.pkg -target /
   ```

3. **Проверьте установку**
   ```bash
   ls -la /Applications/Nexy.app
   ```

### **Вариант 2: Установка из исходного кода**

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/Seregawpn/nexy_new.git
   cd nexy_new
   ```

2. **Установите зависимости**
   ```bash
   cd client
   pip install -r requirements.txt
   ```

3. **Запустите приложение**
   ```bash
   python main.py
   ```

## ⚙️ Настройка разрешений

### **Автоматическая настройка:**
При первом запуске приложение автоматически запросит все необходимые разрешения.

### **Ручная настройка:**
Если разрешения не были предоставлены автоматически:

1. **Откройте System Preferences**
   - Apple Menu → System Preferences
   - Или через Spotlight: Cmd+Space → "System Preferences"

2. **Перейдите в Security & Privacy**
   - Security & Privacy → Privacy

3. **Настройте разрешения:**
   - **Microphone:** Добавьте Nexy в список разрешенных приложений
   - **Screen Recording:** Добавьте Nexy в список разрешенных приложений
   - **Accessibility:** Добавьте Nexy в список разрешенных приложений
   - **Notifications:** Включите уведомления для Nexy

## ♿ Настройка VoiceOver (для пользователей с нарушениями зрения)

### **Включение VoiceOver:**
1. **System Preferences → Accessibility → VoiceOver**
2. **Включите VoiceOver** или используйте Cmd+F5
3. **Настройте параметры** по вашему усмотрению

### **Интеграция с Nexy:**
- Nexy автоматически обнаружит включенный VoiceOver
- При записи команд VoiceOver будет временно отключен
- После завершения обработки VoiceOver восстановится

## 🔧 Первый запуск

### **1. Запуск приложения**
```bash
# Если установлено через PKG:
open /Applications/Nexy.app

# Если установлено из исходного кода:
cd client && python main.py
```

### **2. Проверка статуса**
- В меню-баре должна появиться иконка Nexy
- Иконка будет серой (SLEEPING режим)
- Приветственное сообщение воспроизведется автоматически

### **3. Тестирование функций**
- **Нажмите и удерживайте пробел** - иконка станет синей (LISTENING)
- **Отпустите пробел** - иконка станет оранжевой (PROCESSING)
- **Дождитесь ответа** - иконка вернется к серому (SLEEPING)

## 🔍 Диагностика проблем

### **Проблема: Приложение не запускается**
```bash
# Проверьте логи:
tail -f /tmp/nexy_test.log

# Проверьте разрешения:
ls -la /Applications/Nexy.app
```

### **Проблема: Микрофон не работает**
1. Проверьте разрешения в System Preferences
2. Убедитесь, что микрофон подключен и работает
3. Перезапустите приложение

### **Проблема: VoiceOver не отключается**
1. Проверьте разрешения Accessibility
2. Убедитесь, что VoiceOver включен
3. Перезапустите приложение

### **Проблема: Захват экрана не работает**
1. Проверьте разрешения Screen Recording
2. Убедитесь, что приложение добавлено в список разрешенных
3. Перезапустите приложение

## 🛠️ Дополнительные настройки

### **Конфигурация приложения:**
```bash
# Редактирование конфигурации:
nano /Applications/Nexy.app/Contents/Resources/config/unified_config.yaml
```

### **Настройка VoiceOver интеграции:**
```yaml
voiceover_control:
  enabled: true
  duck_modes: ["listening", "processing"]
  release_modes: ["sleeping"]
  engage_on_keyboard_events: true
  mode: "stop"
```

## 🆘 Поддержка

### **При возникновении проблем:**
1. Проверьте [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Изучите [VoiceOver Permissions Guide](VOICEOVER_PERMISSIONS_GUIDE.md)
3. Создайте [Issue](https://github.com/Seregawpn/nexy_new/issues)

### **Полезные команды:**
```bash
# Сброс разрешений (осторожно!):
./packaging/reset_permissions.sh

# Проверка статуса приложения:
ps aux | grep Nexy

# Просмотр логов:
tail -f /tmp/nexy_test.log
```

## 📚 Дополнительные ресурсы

- [Architecture Overview](ARCHITECTURE_OVERVIEW.md)
- [Accessibility Features](ACCESSIBILITY_FEATURES.md)
- [VoiceOver Permissions Guide](VOICEOVER_PERMISSIONS_GUIDE.md)
- [Packaging Guide](PACKAGING_FINAL_GUIDE.md)

---

**Готово!** Nexy AI Assistant установлен и настроен. Наслаждайтесь голосовым управлением с полной поддержкой доступности! 🎉
