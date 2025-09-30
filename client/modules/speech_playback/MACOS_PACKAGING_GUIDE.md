# 🍎 Speech Playback - Руководство по упаковке для macOS

## 📋 Обзор требований

Модуль `speech_playback` требует специальных разрешений и конфигурации для корректной работы в macOS приложении:
- **Audio permissions** - для воспроизведения звука
- **Core Audio integration** - для работы с аудио системой
- **Code signing** - для подписи приложения
- **Notarization** - для нотаризации Apple

## 🔐 Необходимые разрешения

### 1. Audio Permissions

#### Info.plist настройки:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Основные настройки приложения -->
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.nexy</string>
    
    <key>CFBundleName</key>
    <string>Nexy AI Assistant</string>
    
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    
    <!-- Аудио разрешения -->
    <key>NSMicrophoneUsageDescription</key>
    <string>This app needs microphone access to process voice commands and provide audio responses.</string>
    
    <key>NSSpeechRecognitionUsageDescription</key>
    <string>This app uses speech recognition to understand your voice commands and provide intelligent responses.</string>
    
    <!-- Дополнительные разрешения для speech_playback -->
    <key>NSAudioSessionUsageDescription</key>
    <string>This app needs audio session access to play speech responses and audio content.</string>
    
    <!-- Требования к macOS -->
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    
    <!-- Поддержка Core Audio -->
    <key>UIBackgroundModes</key>
    <array>
        <string>audio</string>
    </array>
</dict>
</plist>
```

### 2. Entitlements файл

#### speech_playback.entitlements:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Основные entitlements -->
    <key>com.apple.security.app-sandbox</key>
    <true/>
    
    <key>com.apple.security.files.user-selected.read-only</key>
    <true/>
    
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Аудио entitlements -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    
    <key>com.apple.security.device.audio-output</key>
    <true/>
    
    <!-- Сетевые разрешения для Azure TTS -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <key>com.apple.security.network.server</key>
    <false/>
    
    <!-- Разрешения для Core Audio -->
    <key>com.apple.security.audio-unit-host</key>
    <true/>
    
    <!-- Разрешения для работы с файлами -->
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    
    <!-- Разрешения для временных файлов -->
    <key>com.apple.security.temporary-exception.files.absolute-path.read-write</key>
    <array>
        <string>/tmp/</string>
        <string>/var/tmp/</string>
    </array>
</dict>
</plist>
```

## 🏗️ Сборка приложения

### 1. Структура проекта

```
Nexy.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── nexy
│   ├── Resources/
│   │   ├── speech_playback/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   ├── macos/
│   │   │   └── utils/
│   │   └── other_modules/
│   └── Frameworks/
│       ├── Python.framework
│       └── other_frameworks/
```

### 2. Build script (build_macos.sh)

```bash
#!/bin/bash

# Конфигурация
APP_NAME="Nexy"
BUNDLE_ID="com.yourcompany.nexy"
VERSION="1.0.0"
BUILD_DIR="build"
APP_DIR="$BUILD_DIR/$APP_NAME.app"

echo "🍎 Сборка macOS приложения для $APP_NAME"

# Очистка предыдущей сборки
rm -rf "$BUILD_DIR"
mkdir -p "$APP_DIR/Contents/MacOS"
mkdir -p "$APP_DIR/Contents/Resources"
mkdir -p "$APP_DIR/Contents/Frameworks"

# Копирование Python приложения
echo "📦 Копирование Python приложения..."
cp -r client/* "$APP_DIR/Contents/Resources/"

# Копирование Info.plist
echo "📋 Копирование Info.plist..."
cp "Info.plist" "$APP_DIR/Contents/"

# Создание исполняемого файла
echo "🔧 Создание исполняемого файла..."
cat > "$APP_DIR/Contents/MacOS/nexy" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/../Resources"
exec python3 -m nexy.main "$@"
EOF

chmod +x "$APP_DIR/Contents/MacOS/nexy"

# Копирование Python framework
echo "🐍 Копирование Python framework..."
if [ -d "/Library/Frameworks/Python.framework" ]; then
    cp -r "/Library/Frameworks/Python.framework" "$APP_DIR/Contents/Frameworks/"
else
    echo "⚠️ Python.framework не найден. Установите Python через python.org"
    exit 1
fi

# Копирование зависимостей
echo "📚 Установка зависимостей..."
cd "$APP_DIR/Contents/Resources"
pip3 install --target . -r requirements.txt

echo "✅ Сборка завершена: $APP_DIR"
```

### 3. Requirements файл

#### requirements.txt:
```
# Core dependencies
numpy>=1.21.0
sounddevice>=0.4.0
pydub>=0.25.0

# Azure TTS
azure-cognitiveservices-speech>=1.45.0

# Async support
asyncio-mqtt>=0.11.0

# macOS specific
pyobjc-framework-CoreAudio>=9.0
pyobjc-framework-AudioToolbox>=9.0
```

## 🔏 Подписание кода

### 1. Получение сертификата

```bash
# Создание запроса на сертификат
openssl req -new -newkey rsa:2048 -nodes -keyout nexy.key -out nexy.csr

# Загрузка в Apple Developer Portal
# Скачивание сертификата: nexy.cer
# Установка в Keychain
```

### 2. Подписание приложения

```bash
#!/bin/bash

# Конфигурация подписания
APP_NAME="Nexy"
BUNDLE_ID="com.yourcompany.nexy"
CERTIFICATE="Developer ID Application: Your Company (TEAM_ID)"
ENTITLEMENTS="speech_playback.entitlements"

echo "🔏 Подписание приложения $APP_NAME"

# Подписание всех исполняемых файлов
echo "📝 Подписание Python framework..."
codesign --force --sign "$CERTIFICATE" --entitlements "$ENTITLEMENTS" \
    "$APP_NAME.app/Contents/Frameworks/Python.framework"

# Подписание основного приложения
echo "📝 Подписание основного приложения..."
codesign --force --sign "$CERTIFICATE" --entitlements "$ENTITLEMENTS" \
    "$APP_NAME.app"

# Проверка подписи
echo "✅ Проверка подписи..."
codesign --verify --verbose "$APP_NAME.app"
spctl --assess --verbose "$APP_NAME.app"

echo "✅ Подписание завершено"
```

### 3. Создание PKG пакета

```bash
#!/bin/bash

# Конфигурация
APP_NAME="Nexy"
BUNDLE_ID="com.yourcompany.nexy"
VERSION="1.0.0"
PKG_NAME="Nexy_AI_Assistant_${VERSION}.pkg"

echo "📦 Создание PKG пакета"

# Создание временной структуры
mkdir -p "pkg_build/Applications"
cp -r "$APP_NAME.app" "pkg_build/Applications/"

# Создание distribution.xml
cat > "distribution.xml" << EOF
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Nexy AI Assistant</title>
    <organization>com.yourcompany</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false"/>
    <choices-outline>
        <line choice="default">
            <line choice="bundle"/>
        </line>
    </choices-outline>
    <choice id="default"/>
    <choice id="bundle" visible="false">
        <pkg-ref id="$BUNDLE_ID"/>
    </choice>
    <pkg-ref id="$BUNDLE_ID" version="$VERSION" onConclusion="none">Nexy.pkg</pkg-ref>
</installer-gui-script>
EOF

# Создание PKG
pkgbuild --root "pkg_build" --identifier "$BUNDLE_ID" --version "$VERSION" \
    --install-location "/Applications" "Nexy.pkg"

productbuild --distribution "distribution.xml" --package-path "." "$PKG_NAME"

# Подписание PKG
codesign --sign "$CERTIFICATE" "$PKG_NAME"

echo "✅ PKG пакет создан: $PKG_NAME"
```

## 🏛️ Нотаризация

### 1. Подготовка к нотаризации

```bash
#!/bin/bash

# Конфигурация
APP_NAME="Nexy"
PKG_NAME="Nexy_AI_Assistant_1.0.0.pkg"
APPLE_ID="your-apple-id@example.com"
APP_PASSWORD="your-app-specific-password"
TEAM_ID="5NKLL2CLB9"

echo "🏛️ Подготовка к нотаризации"

# Создание zip архива для нотаризации
ditto -c -k --keepParent "$APP_NAME.app" "$APP_NAME.zip"

# Отправка на нотаризацию
echo "📤 Отправка на нотаризацию..."
xcrun notarytool submit "$APP_NAME.zip" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

# Получение тикета
TICKET=$(xcrun notarytool submit "$APP_NAME.zip" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --output-format json | jq -r '.id')

echo "🎫 Тикет нотаризации: $TICKET"

# Проверка статуса
xcrun notarytool info "$TICKET" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID"

# Скрепление тикета
echo "📌 Скрепление тикета..."
xcrun stapler staple "$APP_NAME.app"
xcrun stapler staple "$PKG_NAME"

echo "✅ Нотаризация завершена"
```

### 2. Проверка нотаризации

```bash
#!/bin/bash

APP_NAME="Nexy"
PKG_NAME="Nexy_AI_Assistant_1.0.0.pkg"

echo "🔍 Проверка нотаризации"

# Проверка приложения
echo "📱 Проверка приложения..."
spctl --assess --verbose --type execute "$APP_NAME.app"

# Проверка PKG
echo "📦 Проверка PKG..."
spctl --assess --verbose --type install "$PKG_NAME"

# Проверка скрепления
echo "📌 Проверка скрепления..."
xcrun stapler validate "$APP_NAME.app"
xcrun stapler validate "$PKG_NAME"

echo "✅ Все проверки пройдены"
```

## ⚠️ Возможные проблемы и решения

### 1. Проблемы с разрешениями

#### ❌ Ошибка: "Audio permission denied"
```bash
# ✅ Решение: Добавьте в Info.plist
<key>NSMicrophoneUsageDescription</key>
<string>This app needs microphone access for voice commands.</string>
```

#### ❌ Ошибка: "Core Audio not available"
```bash
# ✅ Решение: Проверьте entitlements
<key>com.apple.security.device.audio-output</key>
<true/>
```

### 2. Проблемы с подписанием

#### ❌ Ошибка: "Code signing failed"
```bash
# ✅ Решение: Проверьте сертификат
security find-identity -v -p codesigning
```

#### ❌ Ошибка: "Entitlements not found"
```bash
# ✅ Решение: Убедитесь, что файл entitlements существует
codesign --entitlements speech_playback.entitlements --sign "CERTIFICATE" app.app
```

### 3. Проблемы с нотаризацией

#### ❌ Ошибка: "Notarization failed"
```bash
# ✅ Решение: Проверьте логи
xcrun notarytool log "$TICKET" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID"
```

#### ❌ Ошибка: "Stapling failed"
```bash
# ✅ Решение: Убедитесь, что нотаризация прошла успешно
xcrun notarytool info "$TICKET" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID"
```

## 🚀 Автоматизация сборки

### 1. Полный build script

```bash
#!/bin/bash

# Конфигурация
APP_NAME="Nexy"
BUNDLE_ID="com.yourcompany.nexy"
VERSION="1.0.0"
CERTIFICATE="Developer ID Application: Your Company (TEAM_ID)"
APPLE_ID="your-apple-id@example.com"
APP_PASSWORD="your-app-specific-password"
TEAM_ID="5NKLL2CLB9"

echo "🚀 Полная сборка и упаковка $APP_NAME"

# 1. Сборка приложения
echo "📦 Этап 1: Сборка приложения"
./build_macos.sh

# 2. Подписание
echo "🔏 Этап 2: Подписание"
./sign_app.sh

# 3. Создание PKG
echo "📦 Этап 3: Создание PKG"
./create_pkg.sh

# 4. Нотаризация
echo "🏛️ Этап 4: Нотаризация"
./notarize.sh

# 5. Проверка
echo "✅ Этап 5: Проверка"
./verify.sh

echo "🎉 Сборка завершена успешно!"
```

### 2. CI/CD интеграция

#### GitHub Actions workflow:
```yaml
name: Build and Notarize macOS App

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pyinstaller
    
    - name: Build app
      run: ./build_macos.sh
    
    - name: Sign app
      env:
        CERTIFICATE: ${{ secrets.CERTIFICATE }}
        ENTITLEMENTS: speech_playback.entitlements
      run: ./sign_app.sh
    
    - name: Notarize app
      env:
        APPLE_ID: ${{ secrets.APPLE_ID }}
        APP_PASSWORD: ${{ secrets.APP_PASSWORD }}
        TEAM_ID: ${{ secrets.TEAM_ID }}
      run: ./notarize.sh
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: nexy-macos-app
        path: |
          Nexy.app
          Nexy_AI_Assistant_*.pkg
```

## 📋 Чек-лист для релиза

### Перед сборкой:
- [ ] Обновлен `Info.plist` с правильными разрешениями
- [ ] Создан `entitlements.plist` с необходимыми правами
- [ ] Проверены все зависимости в `requirements.txt`
- [ ] Обновлен номер версии

### После сборки:
- [ ] Приложение запускается без ошибок
- [ ] Аудио воспроизводится корректно
- [ ] Все разрешения запрашиваются правильно
- [ ] Подписание прошло успешно

### После нотаризации:
- [ ] Приложение проходит Gatekeeper
- [ ] PKG устанавливается без предупреждений
- [ ] Все функции работают после установки
- [ ] Логи не содержат критических ошибок

## 🔧 Дополнительные настройки

### 1. Отладка в Xcode
```bash
# Включение отладки Core Audio
export AVAudioSessionCategory=Playback
export AVAudioSessionMode=Default
```

### 2. Мониторинг производительности
```bash
# Профилирование аудио
instruments -t "Audio" -D trace.trace Nexy.app
```

### 3. Тестирование на разных версиях macOS
```bash
# Тестирование на macOS 10.15+
xcrun simctl list devices | grep "macOS"
```

---

**Важно:** Всегда тестируйте приложение на чистой системе перед релизом, чтобы убедиться, что все зависимости и разрешения работают корректно.
