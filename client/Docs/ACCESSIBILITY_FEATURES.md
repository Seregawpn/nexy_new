# ♿ Accessibility Features - Функции доступности Nexy

## 🎯 Обзор

Nexy AI Assistant разработан с учетом принципов доступности и включает специальные функции для пользователей с нарушениями зрения.

## 🌟 Основные функции доступности

### **1. VoiceOver Integration**
- **Умное управление VoiceOver** - автоматическое отключение/включение во время работы
- **Сохранение состояния** - запоминает, был ли VoiceOver включен изначально
- **Безопасное восстановление** - возвращает VoiceOver в исходное состояние

### **2. Аудио-первый интерфейс**
- **Голосовое управление** - полный контроль через голосовые команды
- **Аудио обратная связь** - звуковые сигналы для всех действий
- **Естественная речь** - качественное воспроизведение ответов

### **3. Клавиатурная навигация**
- **Push-to-Talk** - простое управление пробелом
- **Горячие клавиши** - быстрый доступ к функциям
- **Клавиатурные прерывания** - мгновенная остановка операций

## 🔧 Техническая реализация

### **VoiceOver Control Module**
```
client/modules/voiceover_control/
├── core/
│   ├── controller.py          # Основной контроллер
│   ├── settings.py           # Настройки VoiceOver
│   └── types.py              # Типы данных
├── macos/
│   └── applescript_bridge.py # AppleScript интеграция
└── README.md                 # Документация модуля
```

### **VoiceOver Ducking Integration**
```
client/integration/integrations/
└── voiceover_ducking_integration.py
```

## 🎮 Пользовательский опыт

### **Для пользователей с нарушениями зрения:**

1. **Запуск приложения:**
   - VoiceOver автоматически отключается при начале записи
   - Воспроизводится приветственное сообщение
   - Приложение готово к использованию

2. **Работа с приложением:**
   - Удерживайте пробел для записи
   - Отпустите для обработки
   - Получите голосовой ответ
   - VoiceOver автоматически восстанавливается

3. **Завершение работы:**
   - VoiceOver возвращается в исходное состояние
   - Все настройки сохранены

## ⚙️ Конфигурация

### **Настройки VoiceOver в unified_config.yaml:**
```yaml
voiceover_control:
  enabled: true
  duck_modes: ["listening", "processing"]
  release_modes: ["sleeping"]
  engage_on_keyboard_events: true
  mode: "stop"
```

### **Параметры управления:**
- `duck_modes` - режимы, в которых VoiceOver отключается
- `release_modes` - режимы, в которых VoiceOver восстанавливается
- `engage_on_keyboard_events` - реагировать на нажатия клавиш
- `mode` - метод управления (stop/toggle)

## 🔍 Диагностика и отладка

### **Проверка статуса VoiceOver:**
```python
from modules.voiceover_control.core.controller import VoiceOverController

controller = VoiceOverController()
status = controller.get_voiceover_status()
print(f"VoiceOver running: {status['voiceover_running']}")
```

### **Логирование:**
```bash
# Просмотр логов VoiceOver интеграции
grep "VoiceOver" /tmp/nexy_test.log
```

## 🧪 Тестирование

### **Автоматические тесты:**
```bash
# Запуск тестов VoiceOver модуля
cd client/modules/voiceover_control
python -m pytest tests/
```

### **Ручное тестирование:**
1. Включите VoiceOver (Cmd+F5)
2. Запустите Nexy
3. Проверьте, что VoiceOver отключается при записи
4. Убедитесь, что VoiceOver восстанавливается после завершения

## 📱 Совместимость

### **Поддерживаемые версии macOS:**
- macOS 10.15 (Catalina) и новее
- macOS 11.0 (Big Sur) и новее
- macOS 12.0 (Monterey) и новее
- macOS 13.0 (Ventura) и новее
- macOS 14.0 (Sonoma) и новее

### **Совместимость с другими технологиями:**
- **VoiceOver** - полная поддержка
- **Zoom** - совместимо
- **Switch Control** - совместимо
- **Dwell Control** - совместимо

## 🚀 Будущие улучшения

### **Планируемые функции:**
- Поддержка других screen readers
- Настраиваемые звуковые сигналы
- Голосовые команды для настройки
- Интеграция с системными настройками доступности

### **Исследования:**
- Поддержка Windows Narrator (для будущих версий)
- Интеграция с мобильными screen readers
- Улучшенная навигация для пользователей с двигательными нарушениями

## 📚 Дополнительные ресурсы

### **Документация Apple:**
- [VoiceOver User Guide](https://support.apple.com/guide/voiceover/)
- [Accessibility Programming Guide](https://developer.apple.com/accessibility/)
- [Human Interface Guidelines - Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility/overview/)

### **Стандарты доступности:**
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Section 508 Standards](https://www.section508.gov/)
- [Apple Accessibility Guidelines](https://developer.apple.com/accessibility/)

## 🆘 Поддержка

### **При проблемах с доступностью:**
1. Проверьте разрешения в System Preferences → Security & Privacy → Privacy → Accessibility
2. Убедитесь, что VoiceOver включен в System Preferences → Accessibility → VoiceOver
3. Перезапустите приложение
4. Проверьте логи в Console.app

### **Обратная связь:**
- Сообщите о проблемах через GitHub Issues
- Предложите улучшения через GitHub Discussions
- Участвуйте в тестировании новых функций доступности
