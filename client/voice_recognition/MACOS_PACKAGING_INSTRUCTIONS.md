# Инструкции по упаковке Voice Recognition для macOS

## Обзор

Модуль `voice_recognition` требует специальных разрешений и конфигурации для корректной работы в macOS приложении.

## Требования

### Системные требования
- **macOS**: 10.14+ (Mojave и выше)
- **Python**: 3.8+
- **Микрофон**: Доступный аудио вход
- **Права доступа**: Разрешение на использование микрофона

### Зависимости
```python
speech_recognition>=3.10.0
sounddevice>=0.4.6
numpy>=1.21.0
scipy>=1.7.0
librosa>=0.9.0
```

## Entitlements (Разрешения)

### Обязательные entitlements
```xml
<!-- voice_recognition.entitlements -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Основные разрешения -->
    <key>com.apple.security.app-sandbox</key>
    <true/>
    
    <!-- Микрофон -->
    <key>com.apple.security.device.microphone</key>
    <true/>
    
    <!-- Аудио устройства -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    
    <!-- Сетевой доступ для облачных API -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Файловый доступ для кэша -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Временные исключения -->
    <key>com.apple.security.temporary-exception.audio-unit-host</key>
    <true/>
    
    <!-- Автоматизация для системных событий -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
</dict>
</plist>
```

## Info.plist конфигурация

### Основные настройки
```xml
<!-- Info.plist для voice_recognition -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Основная информация -->
    <key>CFBundleIdentifier</key>
    <string>com.nexy.voiceassistant.voicerecognition</string>
    
    <key>CFBundleName</key>
    <string>Voice Recognition</string>
    
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    
    <!-- Минимальная версия macOS -->
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    
    <!-- Поддерживаемые архитектуры -->
    <key>LSArchitecturePriority</key>
    <array>
        <string>arm64</string>
        <string>x86_64</string>
    </array>
    
    <!-- Описание использования микрофона -->
    <key>NSMicrophoneUsageDescription</key>
    <string>Voice Recognition requires microphone access to process voice commands and speech input for the Nexy voice assistant.</string>
    
    <!-- Описание использования аудио -->
    <key>NSAudioUsageDescription</key>
    <string>Voice Recognition uses audio input to provide speech recognition capabilities for voice commands and natural language processing.</string>
    
    <!-- Категория приложения -->
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.productivity</string>
    
    <!-- Поддержка темной темы -->
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
    
    <!-- Фоновые задачи -->
    <key>UIBackgroundModes</key>
    <array>
        <string>audio</string>
        <string>background-processing</string>
    </array>
    
    <!-- Поддержка многопоточности -->
    <key>NSPrincipalClass</key>
    <string>NSApplication</string>
    
    <!-- Отключение App Nap -->
    <key>LSUIElement</key>
    <false/>
    
    <!-- Поддержка высокого разрешения -->
    <key>NSHighResolutionCapable</key>
    <true/>
    
    <!-- Поддержка Retina -->
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
```

## Процесс упаковки

### 1. Подготовка
- Убедитесь, что все зависимости установлены
- Проверьте, что микрофон доступен
- Настройте entitlements и Info.plist

### 2. Сборка
- Используйте PyInstaller для создания .app bundle
- Включите все необходимые файлы модуля
- Настройте скрытые импорты

### 3. Подпись
- Подпишите приложение с Developer ID
- Примените entitlements
- Проверьте подпись

### 4. Нотаризация
- Отправьте на нотаризацию Apple
- Дождитесь одобрения
- Прикрепите тикет нотаризации

### 5. Создание PKG
- Создайте PKG установщик
- Подпишите установщик
- Протестируйте установку

## Возможные проблемы

### Проблемы с разрешениями
- **Микрофон заблокирован**: Сбросьте разрешения в System Preferences
- **Entitlements не работают**: Проверьте правильность файла entitlements
- **Sandbox ошибки**: Убедитесь, что все необходимые разрешения включены

### Проблемы с производительностью
- **Высокое использование CPU**: Оптимизируйте конфигурацию распознавания
- **Утечки памяти**: Убедитесь в правильной очистке ресурсов
- **Медленное распознавание**: Проверьте настройки аудио

### Проблемы с подписью
- **Недействительная подпись**: Переподпишите приложение
- **Ошибки нотаризации**: Проверьте логи и исправьте проблемы
- **Gatekeeper блокирует**: Убедитесь, что приложение нотаризовано

## Тестирование

### Базовое тестирование
1. Проверьте доступность микрофона
2. Протестируйте распознавание речи
3. Убедитесь в корректной работе в sandbox

### Тестирование производительности
1. Измерьте время инициализации
2. Проверьте использование памяти
3. Протестируйте длительную работу

### Тестирование интеграции
1. Проверьте работу с другими модулями
2. Убедитесь в корректной обработке ошибок
3. Протестируйте все сценарии использования

## Заключение

Модуль `voice_recognition` требует тщательной настройки для корректной работы в macOS приложении. Следуйте данным инструкциям для успешной упаковки и распространения.
