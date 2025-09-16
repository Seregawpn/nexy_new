# 📦 Input Processing - Руководство по упаковке и сертификации для macOS

## 🎯 Обзор

Данный документ содержит полные требования и инструкции для упаковки, подписания, сертификации и нотаризации модуля `input_processing` для macOS в соответствии с политиками Apple.

## 📋 Предварительные требования

### 1. **Apple Developer Account**
- ✅ Активный Apple Developer Program ($99/год)
- ✅ Сертификаты разработчика
- ✅ Provisioning Profiles
- ✅ App-Specific Password для нотаризации

### 2. **Инструменты разработки**
```bash
# Xcode Command Line Tools
xcode-select --install

# Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python зависимости
pip3 install pyinstaller
```

### 3. **Python окружение**
```bash
# Python 3.9+
python3 --version

# PyInstaller для создания bundle
pip3 install pyinstaller

# Зависимости для input_processing
pip3 install pynput>=1.7.6
pip3 install speechrecognition>=3.10.0
pip3 install pyaudio>=0.2.11
pip3 install sounddevice>=0.4.5
pip3 install numpy>=1.21.0
```

## 🔐 Требования безопасности

### 1. **Code Signing (Подписание кода)**

#### 1.1 Обязательные сертификаты
- **Developer ID Application** - для подписания исполняемых файлов
- **Developer ID Installer** - для подписания PKG пакетов
- **Apple Development** - для разработки и тестирования

#### 1.2 Hardened Runtime
```xml
<!-- Обязательные entitlements для Hardened Runtime -->
<key>com.apple.security.cs.allow-jit</key>
<true/>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>
<key>com.apple.security.cs.disable-executable-page-protection</key>
<true/>
<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

#### 1.3 Требования к подписанию
- Все исполняемые файлы должны быть подписаны
- Библиотеки (.dylib, .so) должны быть подписаны
- Использование timestamp для подписей
- Валидация подписей перед распространением

### 2. **Entitlements (Права доступа)**

#### 2.1 App Sandbox
```xml
<key>com.apple.security.app-sandbox</key>
<true/>
```
**Обоснование:** Требуется для работы в sandbox режиме

#### 2.2 Apple Events
```xml
<key>com.apple.security.automation.apple-events</key>
<true/>
<key>com.apple.security.temporary-exception.apple-events</key>
<true/>
```
**Обоснование:** Для доступа к системным событиям клавиатуры

#### 2.3 Файловая система
```xml
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
```
**Обоснование:** Для сохранения конфигурации и логов

#### 2.4 Сетевые соединения
```xml
<key>com.apple.security.network.client</key>
<true/>
```
**Обоснование:** Для отправки распознанной речи на сервер

#### 2.5 Аудио устройства
```xml
<key>com.apple.security.device.audio-input</key>
<true/>
<key>com.apple.security.device.audio-output</key>
<true/>
```
**Обоснование:** Для записи и воспроизведения аудио

#### 2.6 Временные исключения
```xml
<key>com.apple.security.temporary-exception.audio-unit-host</key>
<true/>
<key>com.apple.security.temporary-exception.microphone</key>
<true/>
<key>com.apple.security.temporary-exception.keyboard-access</key>
<true/>
```
**Обоснование:** Для доступа к микрофону и клавиатуре

### 3. **Privacy Requirements (Требования конфиденциальности)**

#### 3.1 Usage Descriptions
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Input Processing module needs microphone access to record and recognize speech commands.</string>

<key>NSSpeechRecognitionUsageDescription</key>
<string>Input Processing module needs speech recognition access to convert voice commands to text.</string>

<key>NSKeyboardUsageDescription</key>
<string>Input Processing module needs keyboard access to monitor spacebar presses for voice control.</string>

<key>NSAudioUsageDescription</key>
<string>Input Processing module needs audio access to process voice commands and audio feedback.</string>

<key>NSNetworkUsageDescription</key>
<string>Input Processing module needs network access to send recognized speech to processing servers.</string>
```

#### 3.2 Data Collection
- **Собираем** аудио данные для распознавания речи
- **Обрабатываем** текст команд локально
- **Передаем** только необходимые данные на сервер
- **Не сохраняем** личные данные пользователей
- **Прозрачность** в использовании микрофона и клавиатуры

## 🏛️ Notarization Requirements (Требования нотаризации)

### 1. **Обязательные проверки**

#### 1.1 Malware Scanning
- Приложение сканируется на наличие вредоносного ПО
- Все библиотеки проверяются на подозрительную активность
- Статический анализ кода на предмет уязвимостей

#### 1.2 Code Integrity
- Проверка целостности всех исполняемых файлов
- Валидация цифровых подписей
- Проверка соответствия Hardened Runtime

#### 1.3 API Usage
- Использование только разрешенных API
- Отсутствие приватных или deprecated API
- Соответствие App Store Guidelines

### 2. **Требования к отправке**

#### 2.1 Формат пакета
- **PKG** (Package) формат для установки
- Подписанный Developer ID Installer сертификатом
- Включение всех необходимых компонентов

#### 2.2 Метаданные
```xml
<key>CFBundleIdentifier</key>
<string>com.yourcompany.input-processing</string>
<key>CFBundleVersion</key>
<string>1.0.0</string>
<key>CFBundleShortVersionString</key>
<string>1.0.0</string>
<key>LSMinimumSystemVersion</key>
<string>10.15</string>
```

## 🔍 Gatekeeper Requirements

### 1. **Проверки безопасности**

#### 1.1 Quarantine Removal
- Приложение должно быть подписано Developer ID
- Нотаризация должна быть завершена успешно
- Тикет нотаризации должен быть прикреплен

#### 1.2 System Integration
- Корректная работа с клавиатурой
- Безопасное управление аудио
- Отсутствие попыток обхода системных ограничений

### 2. **Пользовательский опыт**

#### 2.1 Установка
- Простой процесс установки через PKG
- Запрос разрешений на микрофон и клавиатуру
- Автоматическая настройка после установки

#### 2.2 Запуск
- Мгновенный запуск без задержек
- Корректная работа с разрешениями
- Отсутствие предупреждений безопасности

## 📱 App Store Connect (если применимо)

### 1. **Метаданные приложения**

#### 1.1 Описание
```
Input Processing - модуль обработки ввода для голосового ассистента Nexy. 
Обеспечивает мониторинг клавиатуры (пробел), распознавание речи, 
обработку команд и интеграцию с системой голосового управления.
```

#### 1.2 Ключевые слова
- input
- processing
- keyboard
- speech
- recognition
- voice
- control
- macos

#### 1.3 Категория
- **Primary:** Developer Tools
- **Secondary:** Utilities

## 🧪 Тестирование

### 1. **Функциональное тестирование**

#### 1.1 Базовые функции
- [ ] Мониторинг клавиатуры (пробел)
- [ ] Распознавание речи
- [ ] Обработка коротких нажатий
- [ ] Обработка длинных нажатий
- [ ] Интеграция с аудио системой

#### 1.2 Интеграция с системой
- [ ] Работа с микрофоном
- [ ] Доступ к клавиатуре
- [ ] Обработка разрешений
- [ ] Системные уведомления

### 2. **Тестирование безопасности**

#### 2.1 Code Signing
- [ ] Все файлы подписаны корректно
- [ ] Валидация подписей проходит
- [ ] Hardened Runtime активен

#### 2.2 Notarization
- [ ] Пакет принят на нотаризацию
- [ ] Тикет прикреплен успешно
- [ ] Gatekeeper проверка пройдена

### 3. **Тестирование на разных системах**

#### 3.1 Версии macOS
- [ ] macOS 10.15 (Catalina)
- [ ] macOS 11.0 (Big Sur)
- [ ] macOS 12.0 (Monterey)
- [ ] macOS 13.0 (Ventura)
- [ ] macOS 14.0 (Sonoma)

#### 3.2 Аппаратное обеспечение
- [ ] Intel Mac
- [ ] Apple Silicon (M1/M2)
- [ ] Различные клавиатуры
- [ ] Различные микрофоны

## 📋 Чеклист готовности к сертификации

### Предварительные требования:
- [ ] Apple Developer Account активен
- [ ] Все необходимые сертификаты установлены
- [ ] App-Specific Password создан
- [ ] Team ID получен

### Разработка:
- [ ] Hardened Runtime включен
- [ ] Все entitlements настроены
- [ ] Privacy descriptions добавлены
- [ ] Code signing настроен

### Сборка:
- [ ] Приложение собирается без ошибок
- [ ] Все файлы подписаны корректно
- [ ] PKG пакет создан
- [ ] Метаданные заполнены

### Нотаризация:
- [ ] Пакет отправлен на нотаризацию
- [ ] Нотаризация завершена успешно
- [ ] Тикет прикреплен
- [ ] Gatekeeper проверка пройдена

### Тестирование:
- [ ] Функциональное тестирование пройдено
- [ ] Тестирование безопасности завершено
- [ ] Тестирование на разных системах
- [ ] Пользовательский опыт проверен

## 🚨 Частые проблемы и решения

### 1. **Ошибки подписания**
```bash
# Очистка кэша подписания
sudo rm -rf /var/db/receipts/com.apple.pkg.*
sudo rm -rf /Library/Receipts/com.apple.pkg.*
```

### 2. **Ошибки нотаризации**
```bash
# Проверка логов нотаризации
xcrun notarytool log --apple-id "$APPLE_ID" --password "$APP_PASSWORD" --team-id "$TEAM_ID"
```

### 3. **Gatekeeper блокировка**
```bash
# Временное отключение для тестирования
sudo spctl --master-disable
```

### 4. **Проблемы с entitlements**
- Проверьте синтаксис XML
- Убедитесь в корректности ключей
- Проверьте соответствие функциональности

### 5. **Проблемы с аудио**
```bash
# Проверка аудио устройств
system_profiler SPAudioDataType

# Тест микрофона
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

### 6. **Проблемы с клавиатурой**
```bash
# Проверка разрешений на клавиатуру
python3 -c "from pynput import keyboard; print('Keyboard access OK')"
```

## 🔧 Специфичные требования для Input Processing

### 1. **Аудио зависимости**
```bash
# Установка PortAudio
brew install portaudio

# Установка Python аудио библиотек
pip3 install pyaudio sounddevice

# Проверка аудио
python3 -c "import sounddevice; print(sounddevice.query_devices())"
```

### 2. **Клавиатурные зависимости**
```bash
# Установка pynput
pip3 install pynput

# Проверка клавиатуры
python3 -c "from pynput import keyboard; print('Keyboard access OK')"
```

### 3. **Речевые зависимости**
```bash
# Установка SpeechRecognition
pip3 install speechrecognition

# Проверка распознавания речи
python3 -c "import speech_recognition; print('Speech recognition OK')"
```

## 📞 Поддержка и ресурсы

### Apple Developer Resources:
- [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)

### Input Processing Resources:
- [pynput Documentation](https://pynput.readthedocs.io/)
- [SpeechRecognition Documentation](https://pypi.org/project/SpeechRecognition/)
- [sounddevice Documentation](https://python-sounddevice.readthedocs.io/)

### Полезные команды:
```bash
# Проверка подписи
codesign --verify --verbose "InputProcessing.app"

# Проверка entitlements
codesign -d --entitlements - "InputProcessing.app"

# Проверка Gatekeeper
spctl --assess --verbose "InputProcessing.app"

# Проверка нотаризации
xcrun stapler validate "InputProcessing.pkg"

# Проверка аудио
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Проверка клавиатуры
python3 -c "from pynput import keyboard; print('Keyboard OK')"

# Проверка речи
python3 -c "import speech_recognition; print('Speech OK')"
```

## 🎯 Специфичные нюансы для Input Processing

### 1. **Разрешения на аудио**
- Требуется `NSMicrophoneUsageDescription`
- Может потребоваться `NSAudioUsageDescription`
- Проверка доступности микрофона

### 2. **Разрешения на клавиатуру**
- Требуется `NSKeyboardUsageDescription`
- Проверка доступности клавиатуры
- Обработка системных ограничений

### 3. **Производительность**
- Асинхронная обработка событий
- Эффективное управление ресурсами
- Минимальное потребление CPU

### 4. **Безопасность**
- Безопасное управление аудио данными
- Валидация входных данных
- Защита от атак через клавиатуру

### 5. **Мониторинг**
- Логирование событий клавиатуры
- Метрики распознавания речи
- Обработка ошибок

## 📋 Специфичные entitlements для Input Processing

### Полный список entitlements:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- App Sandbox -->
    <key>com.apple.security.app-sandbox</key>
    <true/>
    
    <!-- Apple Events для системных событий -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    <key>com.apple.security.temporary-exception.apple-events</key>
    <true/>
    
    <!-- Файловый доступ для конфигурации -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Сетевой доступ для отправки данных -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Аудио устройства -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.audio-output</key>
    <true/>
    
    <!-- Временные исключения -->
    <key>com.apple.security.temporary-exception.audio-unit-host</key>
    <true/>
    <key>com.apple.security.temporary-exception.microphone</key>
    <true/>
    <key>com.apple.security.temporary-exception.keyboard-access</key>
    <true/>
    
    <!-- Hardened Runtime -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-executable-page-protection</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

## 🚀 Быстрый чеклист для Input Processing

### 1. **Проверка зависимостей**
```bash
# Проверка Python
python3 --version

# Проверка аудио
python3 -c "import sounddevice; print('Audio OK')"

# Проверка клавиатуры
python3 -c "from pynput import keyboard; print('Keyboard OK')"

# Проверка речи
python3 -c "import speech_recognition; print('Speech OK')"
```

### 2. **Проверка модуля**
```bash
# Проверка импорта
python3 -c "from input_processing import KeyboardMonitor, SpeechRecognizer; print('Module OK')"

# Тест клавиатуры
python3 -c "from input_processing import KeyboardMonitor, KeyboardConfig; monitor = KeyboardMonitor(KeyboardConfig()); print('Keyboard Monitor OK')"

# Тест речи
python3 -c "from input_processing import SpeechRecognizer, SpeechConfig; recognizer = SpeechRecognizer(SpeechConfig()); print('Speech Recognizer OK')"
```

### 3. **Проверка разрешений**
```bash
# Проверка микрофона
python3 -c "import sounddevice; print(sounddevice.query_devices())"

# Проверка клавиатуры
python3 -c "from pynput import keyboard; print('Keyboard access OK')"
```

### 4. **Проверка функциональности**
```bash
# Запуск теста
python3 test_spacebar_realtime.py
```

---

**Готово к созданию профессионального macOS приложения!** 🎉
