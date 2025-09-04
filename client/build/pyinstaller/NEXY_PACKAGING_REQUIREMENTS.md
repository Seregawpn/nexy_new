# 📦 Требования для упаковки Nexy app через PyInstaller

## 🎯 Обзор проекта

**Nexy** - это AI Voice Assistant для людей с нарушениями зрения, работающий на macOS.

**Цель:** Создать автономное macOS приложение (.app) для распространения вне App Store с полной поддержкой нотаризации Apple.

---

## 🔧 Системные требования

### **Операционная система:**
- ✅ **macOS 12.0+** (Monterey и выше)
- ✅ **Только Apple Silicon** (M1/M2/M3) 
- ❌ **Intel x86_64 НЕ поддерживается**
- ✅ **ARM64 архитектура** (нативная)

### **Инструменты разработки:**
- ✅ **Python 3.12+** с ARM64 архитектурой
- ✅ **PyInstaller 6.15+** для macOS
- ✅ **Homebrew** для системных зависимостей
- ✅ **Xcode Command Line Tools** для компиляции
- ✅ **Git** для контроля версий

---

## 🐍 Python зависимости

### **Основные библиотеки (requirements.txt):**
```bash
# Аудио и медиа
sounddevice==0.4.6          # Вместо PyAudio (совместимость с PyInstaller)
pydub                        # Для FLAC поддержки и аудио обработки
speech_recognition           # Распознавание речи

# UI и взаимодействие
pynput                       # Обработка клавиатуры и мыши
Pillow                       # Обработка изображений
pygame                       # Аудио интерфейс

# Сетевое взаимодействие
grpcio                       # gRPC клиент
grpcio-tools                # gRPC инструменты
protobuf                     # Сериализация данных

# Системные
psutil                       # Системная информация
numpy                        # Численные вычисления
rich                         # Красивый вывод в консоль
```

### **Системные зависимости (Homebrew):**
```bash
# Аудио кодеки
brew install flac            # FLAC поддержка (обязательно)
brew install ffmpeg          # Медиа обработка
brew install portaudio       # Аудио I/O
brew install libsndfile      # Звуковые файлы
brew install sox             # Аудио утилиты
```

---

## ⚙️ Конфигурация PyInstaller

### **app.spec файл - ключевые настройки:**

```python
# Архитектура (ОБЯЗАТЕЛЬНО)
target_arch="arm64"          # Только ARM64 для Apple Silicon

# Entitlements
entitlements_file="build/pyinstaller/entitlements.plist"

# Исключения проблемных файлов
excludes=[
    "speech_recognition.flac-mac",  # Старый Intel бинарник
    "torch.utils.tensorboard"       # Неиспользуемые модули
]

# Скрытые импорты
hiddenimports=[
    "pydub",
    "pydub.audio_segment", 
    "pydub.utils",
    "Quartz",                       # macOS API
    "objc"                          # Objective-C мосты
]

# Данные для включения
datas=[
    ("/opt/homebrew/bin/flac", "."),  # Системный ARM64 FLAC
    ("config/", "config/"),           # Конфигурация
    ("assets/", "assets/"),           # Ресурсы
    ("streaming.proto", "."),         # gRPC протофайл
    ("utils/", "utils/")              # Утилиты
]

# Иконка
icon="assets/icons/app_icon.icns"
```

---

## 🔐 Entitlements (entitlements.plist)

### **Обязательные разрешения:**

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Hardened Runtime - ОБЯЗАТЕЛЬНО для нотаризации -->
    <key>com.apple.security.cs.hardened-runtime</key>
    <true/>
    
    <!-- JIT и исполнение -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    
    <!-- Сетевой доступ -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- Файловая система -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    
    <!-- Аудио и видео -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
    
    <!-- Доступность -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    
    <!-- Запись экрана -->
    <key>com.apple.security.device.microphone</key>
    <true/>
    
    <!-- TCC разрешения -->
    <key>com.apple.security.tcc.allow</key>
    <array>
        <string>kTCCServiceAccessibility</string>
        <string>kTCCServiceScreenCapture</string>
        <string>kTCCServiceMicrophone</string>
        <string>kTCCServiceAppleEvents</string>
    </array>
    
    <!-- Отключение песочницы -->
    <key>com.apple.security.app-sandbox</key>
    <false/>
    
    <!-- ARM64 специфичные -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
</dict>
</plist>
```

---

## 📱 Info.plist настройки

### **Обязательные ключи:**

```xml
<!-- Основная информация -->
<key>CFBundleName</key>
<string>Nexy</string>

<key>CFBundleDisplayName</key>
<string>AI Voice Assistant for People with Visual Impairments</string>

<key>CFBundleVersion</key>
<string>1.71.0</string>

<key>CFBundleShortVersionString</key>
<string>1.71.0</string>

<key>CFBundleIdentifier</key>
<string>com.nexy.assistant</string>

<!-- Архитектура - Apple Silicon ONLY -->
<key>LSArchitecturePriority</key>
<array><string>arm64</string></array>

<key>LSRequiresNativeExecution</key>
<true/>

<key>LSMinimumSystemVersion</key>
<string>12.0.0</string>

<!-- Разрешения -->
<key>NSMicrophoneUsageDescription</key>
<string>Nexy needs access to your microphone to hear your commands.</string>

<key>NSScreenCaptureUsageDescription</key>
<string>Nexy needs screen recording access to capture content or control the screen based on your commands.</string>

<key>NSAppleEventsUsageDescription</key>
<string>Nexy needs to control other apps to execute your commands.</string>

<key>NSAccessibilityUsageDescription</key>
<string>Nexy needs accessibility permissions to assist you with controlling your computer.</string>

<!-- Категория приложения -->
<key>LSApplicationCategoryType</key>
<string>public.app-category.productivity</string>

<!-- Сетевой доступ -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>
```

---

## 🔑 Подпись и нотаризация

### **Требуемые сертификаты:**

1. **Developer ID Application** - для подписи .app файла
2. **Developer ID Installer** - для подписи .pkg файла
3. **Apple ID** с app-specific password - для нотаризации

### **Процесс подписи:**

```bash
# 1. Подпись .app файла
codesign --force --deep --timestamp --options runtime \
  --sign "Developer ID Application: Your Name (TEAM_ID)" \
  Nexy.app

# 2. Подпись .pkg файла
productsign --sign "Developer ID Installer: Your Name (TEAM_ID)" \
  Nexy_unsigned.pkg Nexy_signed.pkg

# 3. Проверка подписи
codesign -dv --verbose=4 Nexy.app
pkgutil --check-signature Nexy_signed.pkg
```

---

## 🎯 Требования для нотаризации Apple

### **Обязательные технические требования:**

#### **1. Hardened Runtime (КРИТИЧНО):**
```xml
<!-- entitlements.plist - ОБЯЗАТЕЛЬНО -->
<key>com.apple.security.cs.hardened-runtime</key>
<true/>
```

#### **2. Совместимость с macOS:**
- ✅ **SDK версия:** 10.9 или выше (не старше!)
- ✅ **Архитектура:** ARM64 только (для Apple Silicon)
- ✅ **macOS версия:** 12.0+ (Monterey и выше)

#### **3. Правильная подпись:**
- ✅ **Developer ID Application** сертификат
- ✅ **Timestamp** (--timestamp флаг)
- ✅ **Deep signing** (--deep флаг)
- ✅ **Runtime options** (--options runtime)

### **Процесс нотаризации:**

#### **Шаг 1: Настройка Apple ID:**
```bash
# Настройка учетных данных
./setup_apple_id.sh

# Проверка настройки
xcrun notarytool info --help
```

#### **Шаг 2: Отправка на нотаризацию:**
```bash
# Отправка PKG на нотаризацию
./notarize_pkg.sh

# Или вручную:
xcrun notarytool submit Nexy_signed.pkg \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID"
```

#### **Шаг 3: Проверка статуса:**
```bash
# Получение UUID из ответа и проверка статуса
xcrun notarytool info [UUID] \
  --apple-id "your@email.com" \
  --password "app-specific-password" \
  --team-id "TEAM_ID"
```

#### **Шаг 4: Привязка тикета (если успешно):**
```bash
# Привязка тикета к .app файлу
xcrun stapler staple Nexy.app
```

### **Что проверяет Apple при нотаризации:**

#### **🔍 Технические проверки:**
1. **Архитектура** - только ARM64, без Intel x86_64
2. **Hardened Runtime** - обязательно включен
3. **Подпись** - валидная Developer ID с timestamp
4. **SDK версия** - не старше 10.9
5. **Зависимости** - все библиотеки подписаны
6. **Entitlements** - корректно настроены

#### **🔍 Безопасность:**
1. **Отсутствие вредоносного кода**
2. **Правильные разрешения** (минимально необходимые)
3. **Соблюдение sandbox политик** (если включен)
4. **Корректная обработка TCC** (Transparency, Consent, Control)

### **Частые причины отказа в нотаризации:**

#### **❌ Критические ошибки:**
1. **"The executable does not have the hardened runtime enabled"**
   - **Решение:** Добавить `com.apple.security.cs.hardened-runtime` в entitlements.plist

2. **"The binary uses an SDK older than the 10.9 SDK"**
   - **Решение:** Заменить проблемные бинарники (например, flac-mac Intel) на ARM64 версии

3. **"The binary is not signed with a valid Developer ID certificate"**
   - **Решение:** Использовать правильный Developer ID Application сертификат

4. **"The signature does not include a secure timestamp"**
   - **Решение:** Добавить `--timestamp` флаг при подписи

#### **❌ Проблемы с архитектурой:**
1. **"Architecture x86_64 not supported"**
   - **Решение:** Убедиться, что все зависимости ARM64, исключить Intel бинарники

2. **"Mixed architectures detected"**
   - **Решение:** Проверить все включенные файлы на архитектуру

### **Проверки перед отправкой на нотаризацию:**

#### **🔍 Предварительная валидация:**
```bash
# 1. Проверка архитектуры
file build/pyinstaller/dist/Nexy.app/Contents/MacOS/Nexy

# 2. Проверка подписи
codesign -dv --verbose=4 build/pyinstaller/dist/Nexy.app

# 3. Проверка entitlements
codesign -d --entitlements :- build/pyinstaller/dist/Nexy.app

# 4. Проверка зависимостей
otool -L build/pyinstaller/dist/Nexy.app/Contents/MacOS/Nexy

# 5. Проверка SDK версии
otool -l build/pyinstaller/dist/Nexy.app/Contents/MacOS/Nexy | grep -A 5 "LC_VERSION_MIN_MACOS"
```

#### **🔍 Проверка PKG:**
```bash
# Проверка подписи PKG
pkgutil --check-signature Nexy_signed.pkg

# Проверка содержимого PKG
pkgutil --expand Nexy_signed.pkg /tmp/expanded_pkg
ls -la /tmp/expanded_pkg/
```

### **После успешной нотаризации:**

#### **✅ Привязка тикета:**
```bash
# Привязка тикета к .app файлу
xcrun stapler staple Nexy.app

# Проверка привязки
xcrun stapler validate Nexy.app
```

#### **✅ Финальная проверка:**
```bash
# Проверка подписи с тикетом
codesign -dv --verbose=4 Nexy.app

# Проверка нотаризации
spctl --assess --type exec Nexy.app
```

### **Требования к Apple ID:**
- ✅ **Двухфакторная аутентификация** включена
- ✅ **App-specific password** создан для notarytool
- ✅ **Developer Program** членство активно
- ✅ **Team ID** указан правильно

### **Временные рамки:**
- **Обычная нотаризация:** 5-15 минут
- **При проблемах:** до 24 часов
- **Повторная отправка:** после исправления ошибок

---

## 🚀 Процесс сборки

### **Последовательность действий:**

```bash
# 1. Проверка системы
python check_architecture.py

# 2. Сборка приложения
./build_script.sh

# 3. Создание PKG
./create_pkg.sh

# 4. Подпись PKG
./sign_pkg.sh

# 5. Нотаризация
./notarize_pkg.sh
```

### **Проверка результата:**

```bash
# Проверка архитектуры
file build/pyinstaller/dist/Nexy.app/Contents/MacOS/Nexy

# Проверка размера
du -sh build/pyinstaller/dist/Nexy.app

# Проверка структуры
ls -la build/pyinstaller/dist/Nexy.app/Contents/
```

---

## 📝 Логирование и отладка

### **Конфигурация логирования:**

```yaml
# logging_config.yaml
version: 1
formatters:
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  simple:
    format: '%(levelname)s - %(message)s'

handlers:
  file:
    class: logging.handlers.RotatingFileHandler
    filename: ~/Library/Logs/Nexy/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    formatter: detailed
    level: DEBUG
  
  error_file:
    class: logging.handlers.RotatingFileHandler
    filename: ~/Library/Logs/Nexy/error.log
    maxBytes: 10485760  # 10MB
    backupCount: 3
    formatter: detailed
    level: ERROR
  
  console:
    class: logging.StreamHandler
    formatter: simple
    level: INFO

loggers:
  nexy:
    level: DEBUG
    handlers: [file, error_file, console]
    propagate: false
  
  nexy.audio:
    level: DEBUG
    handlers: [file, error_file]
    propagate: false
  
  nexy.grpc:
    level: INFO
    handlers: [file, error_file]
    propagate: false
```

### **Пути логирования в .app:**
```python
# logging_setup.py
import os
import sys

def get_log_path():
    if getattr(sys, 'frozen', False):
        # В .app bundle
        return os.path.expanduser("~/Library/Logs/Nexy/")
    else:
        # В разработке
        return "logs/"

# Создание директорий
log_dir = get_log_path()
os.makedirs(log_dir, exist_ok=True)
```

---

## 🧪 Тестирование и валидация

### **Тесты перед упаковкой:**

```bash
# 1. Тест архитектуры
python check_architecture.py

# 2. Тест FLAC функциональности
python test_flac.py

# 3. Тест основных модулей
python -c "import sounddevice; print('✅ sounddevice работает')"
python -c "import speech_recognition; print('✅ speech_recognition работает')"
python -c "import Quartz; print('✅ Quartz работает')"

# 4. Тест конфигурации
python -c "import yaml; yaml.safe_load(open('config/app_config.yaml')); print('✅ Конфигурация валидна')"
```

### **Валидация .app bundle:**
```bash
# Проверка архитектуры
file build/pyinstaller/dist/Nexy.app/Contents/MacOS/Nexy

# Проверка зависимостей
otool -L build/pyinstaller/dist/Nexy.app/Contents/MacOS/Nexy

# Проверка подписи
codesign -dv --verbose=4 build/pyinstaller/dist/Nexy.app

# Проверка entitlements
codesign -d --entitlements :- build/pyinstaller/dist/Nexy.app
```

### **Тестирование на чистой системе:**
```bash
# 1. Установка на тестовый Mac
sudo installer -pkg Nexy_AI_Voice_Assistant_v1.71.pkg -target /

# 2. Проверка запуска
open /Applications/Nexy.app

# 3. Проверка разрешений
System Preferences > Security & Privacy > General

# 4. Проверка логирования
tail -f ~/Library/Logs/Nexy/app.log
```

---

## 🔒 Безопасность и приватность

### **Обязательные меры безопасности:**

```xml
<!-- Entitlements для безопасности -->
<key>com.apple.security.cs.hardened-runtime</key>
<true/>

<key>com.apple.security.cs.allow-jit</key>
<true/>

<key>com.apple.security.cs.disable-library-validation</key>
<true/>
```

### **Обработка персональных данных:**
```python
# Безопасное хранение конфигурации
import keyring

def store_credentials(service, username, password):
    keyring.set_password(service, username, password)

def get_credentials(service, username):
    return keyring.get_password(service, username)

# Шифрование чувствительных данных
from cryptography.fernet import Fernet

def encrypt_data(data, key):
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(encrypted_data, key):
    f = Fernet(key)
    return f.decrypt(encrypted_data).decode()
```

### **Политика приватности:**
- ✅ **Локальное хранение** всех данных
- ✅ **Шифрование** чувствительной информации
- ✅ **Отсутствие** телеметрии
- ✅ **Прозрачность** в использовании данных

---

## ♿ Доступность для слепых пользователей

### **VoiceOver интеграция:**
```python
# Поддержка VoiceOver
import subprocess

def announce_to_voiceover(message):
    """Озвучивает сообщение через VoiceOver"""
    subprocess.run([
        'osascript', '-e', 
        f'say "{message}" using "Victoria"'
    ])

def set_voiceover_focus(element_name):
    """Устанавливает фокус VoiceOver на элемент"""
    subprocess.run([
        'osascript', '-e',
        f'tell application "System Events" to set value of text field "{element_name}" to ""'
    ])
```

### **Горячие клавиши:**
```python
# Глобальные горячие клавиши
from pynput import keyboard

def setup_hotkeys():
    with keyboard.GlobalHotKeys({
        '<cmd>+<shift>+n': start_nexy,           # Cmd+Shift+N - запуск
        '<cmd>+<shift>+m': toggle_microphone,     # Cmd+Shift+M - микрофон
        '<cmd>+<shift>+s': stop_nexy,             # Cmd+Shift+S - остановка
        '<cmd>+<shift>+h': help_nexy,             # Cmd+Shift+H - помощь
    }):
        keyboard_listener.join()
```

### **Аудио обратная связь:**
```python
# Звуковые сигналы для обратной связи
import sounddevice as sd
import numpy as np

def play_beep(frequency=1000, duration=0.1):
    """Воспроизводит звуковой сигнал"""
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * frequency * t)
    sd.play(signal, sample_rate)
    sd.wait()

def play_success_sound():
    """Звук успешного выполнения"""
    play_beep(800, 0.1)
    play_beep(1000, 0.1)

def play_error_sound():
    """Звук ошибки"""
    play_beep(400, 0.2)
```

---

## 🚀 Автозапуск и фоновый режим

### **Настройка автозапуска:**

```xml
<!-- Info.plist для фонового режима -->
<key>LSUIElement</key>
<true/>

<key>LSBackgroundOnly</key>
<false/>

<key>NSSupportsAutomaticTermination</key>
<false/>

<key>NSSupportsSuddenTermination</key>
<false/>
```

### **LaunchAgent для автозапуска:**
```xml
<!-- ~/Library/LaunchAgents/com.nexy.assistant.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.nexy.assistant</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Nexy.app/Contents/MacOS/Nexy</string>
    </array>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <true/>
    
    <key>StandardOutPath</key>
    <string>/tmp/nexy.log</string>
    
    <key>StandardErrorPath</key>
    <string>/tmp/nexy.error.log</string>
</dict>
</plist>
```

### **Установка автозапуска:**
```bash
# Копирование LaunchAgent
cp com.nexy.assistant.plist ~/Library/LaunchAgents/

# Загрузка LaunchAgent
launchctl load ~/Library/LaunchAgents/com.nexy.assistant.plist

# Проверка статуса
launchctl list | grep nexy
```

### **Управление фоновым процессом:**
```python
# Проверка статуса процесса
def is_nexy_running():
    """Проверяет, запущен ли Nexy"""
    try:
        result = subprocess.run([
            'pgrep', '-f', 'Nexy'
        ], capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

# Перезапуск процесса
def restart_nexy():
    """Перезапускает Nexy"""
    subprocess.run(['launchctl', 'unload', '~/Library/LaunchAgents/com.nexy.assistant.plist'])
    subprocess.run(['launchctl', 'load', '~/Library/LaunchAgents/com.nexy.assistant.plist'])
```

---

## ⚠️ Критические моменты

### **Что НЕ допускается:**
- ❌ **Intel x86_64** архитектура
- ❌ **macOS 11.0** и ниже
- ❌ **PyAudio** (заменен на sounddevice)
- ❌ **Старые SDK** (должен быть 10.9+)
- ❌ **Отсутствие Hardened Runtime**
- ❌ **Проблемные бинарники** (flac-mac Intel)

### **Что обязательно:**
- ✅ **ARM64** архитектура
- ✅ **Hardened Runtime** включен
- ✅ **Все entitlements** настроены
- ✅ **Usage descriptions** для разрешений
- ✅ **Системный FLAC** вместо встроенного
- ✅ **Правильная подпись** Developer ID сертификатами

---

## 📊 Ожидаемые результаты

### **Характеристики готового приложения:**
- **Размер:** ~240MB (.pkg), ~687MB (.app)
- **Архитектура:** ARM64 только
- **Совместимость:** macOS 12.0+ (M1/M2/M3)
- **Статус:** Готов для распространения вне App Store
- **Нотаризация:** ACCEPTED от Apple

### **Структура файлов:**
```
Nexy.app/
├── Contents/
│   ├── MacOS/Nexy          # Исполняемый файл ARM64
│   ├── Frameworks/          # Зависимости
│   ├── Resources/           # Ресурсы
│   ├── Info.plist           # Метаданные
│   └── _CodeSignature/      # Подпись
```

---

## 🛠️ Устранение проблем

### **Частые ошибки:**

1. **"The binary uses an SDK older than the 10.9 SDK"**
   - Решение: Заменить проблемный flac-mac на системный ARM64 FLAC

2. **"The executable does not have the hardened runtime enabled"**
   - Решение: Добавить `com.apple.security.cs.hardened-runtime` в entitlements

3. **"Request message contains a target_token"**
   - Решение: Настроить правильные TCC разрешения

4. **"Architecture x86_64 not supported"**
   - Решение: Убедиться, что все зависимости ARM64

5. **"Logs not showing up"**
   - Решение: Проверить пути логирования и права доступа

6. **"App not starting automatically"**
   - Решение: Настроить LaunchAgent и проверить права

---

## 📚 Дополнительные ресурсы

### **Документация:**
- [PyInstaller macOS Guide](https://pyinstaller.org/en/stable/usage.html#macos)
- [Apple Developer Notarization](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [macOS Entitlements](https://developer.apple.com/documentation/bundleresources/entitlements)
- [macOS Accessibility](https://developer.apple.com/documentation/appkit/nsaccessibility)
- [LaunchAgent Guide](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html)

### **Полезные команды:**
```bash
# Проверка архитектуры
uname -m
python3 -c "import platform; print(platform.machine())"

# Проверка macOS версии
sw_vers -productVersion

# Проверка Rosetta 2
softwareupdate --list-rosetta

# Проверка подписи
codesign -dv --verbose=4 Nexy.app

# Проверка логирования
tail -f ~/Library/Logs/Nexy/app.log

# Управление автозапуском
launchctl list | grep nexy
launchctl load ~/Library/LaunchAgents/com.nexy.assistant.plist
```

---

## 🎯 Заключение

Соблюдение всех требований обеспечивает:
- ✅ **Успешную сборку** через PyInstaller
- ✅ **Правильную подпись** Developer ID сертификатами  
- ✅ **Успешную нотаризацию** от Apple
- ✅ **Распространение** вне App Store
- ✅ **Совместимость** с современными macOS системами
- ✅ **Полную доступность** для слепых пользователей
- ✅ **Надежное логирование** и отладку
- ✅ **Безопасность** и приватность данных
- ✅ **Автозапуск** и фоновый режим работы

**Внимание:** Все требования критически важны для успешной упаковки и нотаризации!

**Дополнительно:** Особое внимание уделено доступности для слепых пользователей, так как это основная целевая аудитория приложения.
