# ✅ Input Processing - Быстрый чеклист для упаковки macOS

## 🚀 Быстрая сборка Input Processing модуля

### 📋 Предварительные требования

#### 1. Apple Developer Account
- [ ] Активный Apple Developer Program ($99/год)
- [ ] Сертификат "Developer ID Application"
- [ ] Сертификат "Developer ID Installer"
- [ ] App-Specific Password для нотаризации

#### 2. Системные требования
- [ ] macOS 10.15+ (Catalina или новее)
- [ ] Xcode Command Line Tools
- [ ] Homebrew установлен
- [ ] Python 3.9+ установлен

#### 3. Зависимости
```bash
# Установка зависимостей
brew install portaudio
pip3 install pyinstaller
pip3 install pynput>=1.7.6
pip3 install speechrecognition>=3.10.0
pip3 install pyaudio>=0.2.11
pip3 install sounddevice>=0.4.5
pip3 install numpy>=1.21.0
```

### 🔧 Шаг 1: Подготовка

#### 1.1 Структура проекта
```
input_processing_build/
├── src/input_processing/        # Исходный код
├── build/                       # Сборка
├── dist/                        # Готовые пакеты
├── scripts/                     # Скрипты сборки
├── certificates/                # Сертификаты
└── entitlements/                # Права доступа
```

#### 1.2 Создание директорий
```bash
mkdir -p input_processing_build/{src,build,dist,scripts,entitlements,certificates}
```

### 🔐 Шаг 2: Сертификаты

#### 2.1 Проверка сертификатов
```bash
# Список доступных сертификатов
security find-identity -v -p codesigning

# Ожидаемый результат:
# 1) ABC123... "Developer ID Application: Your Name (TEAM_ID)"
# 2) DEF123... "Developer ID Installer: Your Name (TEAM_ID)"
```

#### 2.2 Если сертификатов нет:
1. Открыть Keychain Access
2. Certificate Assistant > Request a Certificate From a Certificate Authority
3. Загрузить CSR в Apple Developer Portal
4. Скачать и установить сертификаты

### 📝 Шаг 3: Конфигурация

#### 3.1 Entitlements (entitlements/input_processing.entitlements)
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

#### 3.2 Info.plist
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>Input Processing</string>
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.input-processing</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>InputProcessing</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
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
</dict>
</plist>
```

### 🏗️ Шаг 4: Сборка

#### 4.1 PyInstaller .spec файл
```python
# input_processing.spec
a = Analysis(
    ['src/input_processing/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/input_processing/core', 'input_processing/core'),
        ('src/input_processing/keyboard', 'input_processing/keyboard'),
        ('src/input_processing/speech', 'input_processing/speech'),
        ('src/input_processing/config', 'input_processing/config'),
    ],
    hiddenimports=[
        'pynput',
        'pynput.keyboard',
        'pynput.mouse',
        'speech_recognition',
        'speech_recognition.recognizers',
        'speech_recognition.recognizers.google',
        'speech_recognition.recognizers.sphinx',
        'speech_recognition.recognizers.wit',
        'speech_recognition.recognizers.azure',
        'speech_recognition.recognizers.bing',
        'speech_recognition.recognizers.api',
        'pyaudio',
        'sounddevice',
        'numpy',
        'numpy.core',
        'numpy.core._methods',
        'numpy.lib.format',
        'threading',
        'asyncio',
        'concurrent.futures',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InputProcessing',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements/input_processing.entitlements',
)
```

#### 4.2 Команда сборки
```bash
# Сборка приложения
pyinstaller input_processing.spec --clean --noconfirm
```

### ✍️ Шаг 5: Подписание

#### 5.1 Подписание приложения
```bash
# Переменные (замените на свои)
APP_PATH="dist/InputProcessing.app"
ENTITLEMENTS="entitlements/input_processing.entitlements"
IDENTITY="Developer ID Application: Your Name (TEAM_ID)"

# Подписание всех библиотек
find "$APP_PATH" -name "*.so" -exec codesign --force --sign "$IDENTITY" {} \;
find "$APP_PATH" -name "*.dylib" -exec codesign --force --sign "$IDENTITY" {} \;

# Подписание основного приложения
codesign --force \
    --sign "$IDENTITY" \
    --entitlements "$ENTITLEMENTS" \
    --options runtime \
    --timestamp \
    "$APP_PATH"

# Проверка подписи
codesign --verify --verbose "$APP_PATH"
spctl --assess --verbose "$APP_PATH"
```

### 📦 Шаг 6: Создание PKG

#### 6.1 Скрипт установки (scripts/postinstall.sh)
```bash
#!/bin/bash
set -e

APP_DIR="/Applications/Input Processing"
mkdir -p "$APP_DIR"
cp -R "InputProcessing.app" "$APP_DIR/"
chmod -R 755 "$APP_DIR"
chown -R root:admin "$APP_DIR"
ln -sf "$APP_DIR/InputProcessing.app/Contents/MacOS/InputProcessing" /usr/local/bin/input-processing
```

#### 6.2 Создание PKG
```bash
# Создание PKG пакета
pkgbuild \
    --root "dist" \
    --identifier "com.yourcompany.input-processing" \
    --version "1.0.0" \
    --install-location "/Applications" \
    --scripts "scripts" \
    "InputProcessing-1.0.0.pkg"
```

### 🔒 Шаг 7: Подписание PKG

#### 7.1 Подписание установочного пакета
```bash
# Переменные
PKG_FILE="InputProcessing-1.0.0.pkg"
INSTALLER_IDENTITY="Developer ID Installer: Your Name (TEAM_ID)"

# Подписание PKG
productsign \
    --sign "$INSTALLER_IDENTITY" \
    "$PKG_FILE" \
    "InputProcessing-1.0.0-signed.pkg"

# Проверка подписи
pkgutil --check-signature "InputProcessing-1.0.0-signed.pkg"
```

### 🏛️ Шаг 8: Нотаризация

#### 8.1 Отправка на нотаризацию
```bash
# Переменные (замените на свои)
PKG_FILE="InputProcessing-1.0.0-signed.pkg"
APPLE_ID="your-apple-id@example.com"
APP_PASSWORD="your-app-specific-password"
TEAM_ID="5NKLL2CLB9"

# Нотаризация
xcrun notarytool submit "$PKG_FILE" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

# Прикрепление тикета
xcrun stapler staple "$PKG_FILE"
```

#### 8.2 Проверка нотаризации
```bash
# Проверка статуса
xcrun stapler validate "$PKG_FILE"

# Проверка Gatekeeper
spctl --assess --type install "$PKG_FILE"
```

### 🚀 Шаг 9: Автоматизация

#### 9.1 Полный скрипт сборки (scripts/full_build.sh)
```bash
#!/bin/bash
set -e

echo "🚀 Полная сборка Input Processing модуля..."

# Переменные (настройте под себя)
APPLE_ID="your-apple-id@example.com"
APP_PASSWORD="your-app-specific-password"
TEAM_ID="5NKLL2CLB9"
APP_IDENTITY="Developer ID Application: Your Name ($TEAM_ID)"
INSTALLER_IDENTITY="Developer ID Installer: Your Name ($TEAM_ID)"

# 1. Проверка зависимостей
echo "🔧 Проверка зависимостей..."
python3 -c "import pynput, speech_recognition, sounddevice, numpy; print('✅ Все зависимости установлены')"

# 2. Сборка
echo "🔨 Сборка..."
pyinstaller input_processing.spec --clean --noconfirm

# 3. Подписание приложения
echo "✍️ Подписание приложения..."
APP_PATH="dist/InputProcessing.app"
ENTITLEMENTS="entitlements/input_processing.entitlements"

find "$APP_PATH" -name "*.so" -exec codesign --force --sign "$APP_IDENTITY" {} \;
find "$APP_PATH" -name "*.dylib" -exec codesign --force --sign "$APP_IDENTITY" {} \;

codesign --force \
    --sign "$APP_IDENTITY" \
    --entitlements "$ENTITLEMENTS" \
    --options runtime \
    --timestamp \
    "$APP_PATH"

# 4. Создание PKG
echo "📦 Создание PKG..."
pkgbuild \
    --root "dist" \
    --identifier "com.yourcompany.input-processing" \
    --version "1.0.0" \
    --install-location "/Applications" \
    --scripts "scripts" \
    "InputProcessing-1.0.0.pkg"

# 5. Подписание PKG
echo "✍️ Подписание PKG..."
productsign \
    --sign "$INSTALLER_IDENTITY" \
    "InputProcessing-1.0.0.pkg" \
    "InputProcessing-1.0.0-signed.pkg"

# 6. Нотаризация
echo "🏛️ Нотаризация..."
xcrun notarytool submit "InputProcessing-1.0.0-signed.pkg" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

xcrun stapler staple "InputProcessing-1.0.0-signed.pkg"

# 7. Проверка
echo "🔍 Проверка..."
xcrun stapler validate "InputProcessing-1.0.0-signed.pkg"
spctl --assess --type install "InputProcessing-1.0.0-signed.pkg"

echo "🎉 Готово! Пакет: InputProcessing-1.0.0-signed.pkg"
```

### ✅ Финальная проверка

#### Чеклист готовности:
- [ ] Приложение собирается без ошибок
- [ ] Все зависимости установлены
- [ ] Подписание прошло успешно
- [ ] PKG создан и подписан
- [ ] Нотаризация завершена
- [ ] Gatekeeper проверка пройдена
- [ ] Пакет можно установить на чистой системе

#### Тестирование:
```bash
# Установка пакета
sudo installer -pkg "InputProcessing-1.0.0-signed.pkg" -target /

# Проверка установки
ls -la "/Applications/Input Processing/"

# Запуск приложения
"/Applications/Input Processing/InputProcessing.app/Contents/MacOS/InputProcessing"
```

### 🔧 Специфичные команды для Input Processing

#### Проверка зависимостей:
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

#### Проверка модуля:
```bash
# Проверка импорта
python3 -c "from input_processing import KeyboardMonitor, SpeechRecognizer; print('Module OK')"

# Тест клавиатуры
python3 -c "from input_processing import KeyboardMonitor, KeyboardConfig; monitor = KeyboardMonitor(KeyboardConfig()); print('Keyboard Monitor OK')"

# Тест речи
python3 -c "from input_processing import SpeechRecognizer, SpeechConfig; recognizer = SpeechRecognizer(SpeechConfig()); print('Speech Recognizer OK')"
```

#### Проверка функциональности:
```bash
# Запуск теста
python3 test_spacebar_realtime.py
```

---

**Готово к созданию профессионального macOS приложения!** 🎉
