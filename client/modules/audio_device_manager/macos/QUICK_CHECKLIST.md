# ✅ macOS Packaging - Быстрый чеклист

## 🚀 Быстрая сборка Audio Device Manager

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
brew install switchaudio-osx
pip3 install pyinstaller
pip3 install pyobjc-framework-CoreAudio
pip3 install pyobjc-framework-Foundation
pip3 install pyobjc-framework-AppKit
```

### 🔧 Шаг 1: Подготовка

#### 1.1 Структура проекта
```
audio_device_manager_build/
├── src/audio_device_manager/     # Исходный код
├── build/                        # Временные файлы сборки
├── dist/                         # Готовое приложение
├── scripts/                      # Скрипты сборки
├── entitlements/                 # Права доступа
└── certificates/                 # Сертификаты
```

#### 1.2 Создание директорий
```bash
mkdir -p audio_device_manager_build/{src,build,dist,scripts,entitlements,certificates}
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

#### 3.1 Entitlements (entitlements/audio_device_manager.entitlements)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.audio-output</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
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
    <string>Audio Device Manager</string>
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.audio-device-manager</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleExecutable</key>
    <string>AudioDeviceManager</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>Audio Device Manager needs microphone access to manage audio devices.</string>
</dict>
</plist>
```

### 🏗️ Шаг 4: Сборка

#### 4.1 PyInstaller .spec файл
```python
# audio_device_manager.spec
a = Analysis(
    ['src/audio_device_manager/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/audio_device_manager/core', 'audio_device_manager/core'),
        ('src/audio_device_manager/config', 'audio_device_manager/config'),
        ('src/audio_device_manager/macos', 'audio_device_manager/macos'),
    ],
    hiddenimports=['PyObjC', 'CoreAudio', 'Foundation', 'AppKit'],
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
    name='AudioDeviceManager',
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
    entitlements_file='entitlements/audio_device_manager.entitlements',
)
```

#### 4.2 Команда сборки
```bash
# Сборка приложения
pyinstaller audio_device_manager.spec --clean --noconfirm
```

### ✍️ Шаг 5: Подписание

#### 5.1 Подписание приложения
```bash
# Переменные (замените на свои)
APP_PATH="dist/AudioDeviceManager.app"
ENTITLEMENTS="entitlements/audio_device_manager.entitlements"
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

APP_DIR="/Applications/Audio Device Manager"
mkdir -p "$APP_DIR"
cp -R "AudioDeviceManager.app" "$APP_DIR/"
chmod -R 755 "$APP_DIR"
chown -R root:admin "$APP_DIR"
ln -sf "$APP_DIR/AudioDeviceManager.app/Contents/MacOS/AudioDeviceManager" /usr/local/bin/audio-device-manager
```

#### 6.2 Создание PKG
```bash
# Создание PKG пакета
pkgbuild \
    --root "dist" \
    --identifier "com.yourcompany.audio-device-manager" \
    --version "1.0.0" \
    --install-location "/Applications" \
    --scripts "scripts" \
    "AudioDeviceManager-1.0.0.pkg"
```

### 🔒 Шаг 7: Подписание PKG

#### 7.1 Подписание установочного пакета
```bash
# Переменные
PKG_FILE="AudioDeviceManager-1.0.0.pkg"
INSTALLER_IDENTITY="Developer ID Installer: Your Name (TEAM_ID)"

# Подписание PKG
productsign \
    --sign "$INSTALLER_IDENTITY" \
    "$PKG_FILE" \
    "AudioDeviceManager-1.0.0-signed.pkg"

# Проверка подписи
pkgutil --check-signature "AudioDeviceManager-1.0.0-signed.pkg"
```

### 🏛️ Шаг 8: Нотаризация

#### 8.1 Отправка на нотаризацию
```bash
# Переменные (замените на свои)
PKG_FILE="AudioDeviceManager-1.0.0-signed.pkg"
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

echo "🚀 Полная сборка Audio Device Manager..."

# Переменные (настройте под себя)
APPLE_ID="your-apple-id@example.com"
APP_PASSWORD="your-app-specific-password"
TEAM_ID="5NKLL2CLB9"
APP_IDENTITY="Developer ID Application: Your Name ($TEAM_ID)"
INSTALLER_IDENTITY="Developer ID Installer: Your Name ($TEAM_ID)"

# 1. Сборка
echo "🔨 Сборка..."
pyinstaller audio_device_manager.spec --clean --noconfirm

# 2. Подписание приложения
echo "✍️ Подписание приложения..."
APP_PATH="dist/AudioDeviceManager.app"
ENTITLEMENTS="entitlements/audio_device_manager.entitlements"

find "$APP_PATH" -name "*.so" -exec codesign --force --sign "$APP_IDENTITY" {} \;
find "$APP_PATH" -name "*.dylib" -exec codesign --force --sign "$APP_IDENTITY" {} \;

codesign --force \
    --sign "$APP_IDENTITY" \
    --entitlements "$ENTITLEMENTS" \
    --options runtime \
    --timestamp \
    "$APP_PATH"

# 3. Создание PKG
echo "📦 Создание PKG..."
pkgbuild \
    --root "dist" \
    --identifier "com.yourcompany.audio-device-manager" \
    --version "1.0.0" \
    --install-location "/Applications" \
    --scripts "scripts" \
    "AudioDeviceManager-1.0.0.pkg"

# 4. Подписание PKG
echo "✍️ Подписание PKG..."
productsign \
    --sign "$INSTALLER_IDENTITY" \
    "AudioDeviceManager-1.0.0.pkg" \
    "AudioDeviceManager-1.0.0-signed.pkg"

# 5. Нотаризация
echo "🏛️ Нотаризация..."
xcrun notarytool submit "AudioDeviceManager-1.0.0-signed.pkg" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

xcrun stapler staple "AudioDeviceManager-1.0.0-signed.pkg"

# 6. Проверка
echo "🔍 Проверка..."
xcrun stapler validate "AudioDeviceManager-1.0.0-signed.pkg"
spctl --assess --type install "AudioDeviceManager-1.0.0-signed.pkg"

echo "🎉 Готово! Пакет: AudioDeviceManager-1.0.0-signed.pkg"
```

### ✅ Финальная проверка

#### Чеклист готовности:
- [ ] Приложение собирается без ошибок
- [ ] Подписание прошло успешно
- [ ] PKG создан и подписан
- [ ] Нотаризация завершена
- [ ] Gatekeeper проверка пройдена
- [ ] Пакет можно установить на чистой системе

#### Тестирование:
```bash
# Установка пакета
sudo installer -pkg "AudioDeviceManager-1.0.0-signed.pkg" -target /

# Проверка установки
ls -la "/Applications/Audio Device Manager/"

# Запуск приложения
"/Applications/Audio Device Manager/AudioDeviceManager.app/Contents/MacOS/AudioDeviceManager"
```

---

**Готово к продакшену!** 🎉
