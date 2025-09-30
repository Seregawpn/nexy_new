# 📦 macOS Packaging Guide для Audio Device Manager

## 🎯 Обзор

Данный документ содержит пошаговые инструкции для упаковки, подписания, сертификации и нотаризации модуля `audio_device_manager` для macOS.

## 📋 Предварительные требования

### 1. **Apple Developer Account**
- Активный Apple Developer Program ($99/год)
- Сертификаты разработчика
- Provisioning Profiles

### 2. **Инструменты разработки**
```bash
# Xcode Command Line Tools
xcode-select --install

# Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# SwitchAudioSource для аудио управления
brew install switchaudio-osx
```

### 3. **Python окружение**
```bash
# Python 3.9+
python3 --version

# PyInstaller для создания bundle
pip3 install pyinstaller

# PyObjC для macOS интеграции
pip3 install pyobjc-framework-CoreAudio
pip3 install pyobjc-framework-Foundation
pip3 install pyobjc-framework-AppKit
```

## 🔧 Шаг 1: Подготовка к упаковке

### 1.1 Создание структуры проекта
```
audio_device_manager_build/
├── src/                    # Исходный код
│   └── audio_device_manager/
├── build/                  # Сборка
├── dist/                   # Готовые пакеты
├── scripts/               # Скрипты сборки
├── certificates/          # Сертификаты
└── entitlements/          # Права доступа
```

### 1.2 Создание .spec файла для PyInstaller
```python
# audio_device_manager.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/audio_device_manager/__main__.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('src/audio_device_manager/core', 'audio_device_manager/core'),
        ('src/audio_device_manager/config', 'audio_device_manager/config'),
        ('src/audio_device_manager/macos', 'audio_device_manager/macos'),
    ],
    hiddenimports=[
        'PyObjC',
        'CoreAudio',
        'Foundation',
        'AppKit',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

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

## 🔐 Шаг 2: Настройка сертификатов

### 2.1 Создание сертификатов в Keychain
```bash
# 1. Открыть Keychain Access
open -a "Keychain Access"

# 2. Создать Certificate Signing Request (CSR)
# Keychain Access > Certificate Assistant > Request a Certificate From a Certificate Authority

# 3. Загрузить CSR в Apple Developer Portal
# https://developer.apple.com/account/resources/certificates/list

# 4. Скачать и установить сертификаты:
# - Developer ID Application
# - Developer ID Installer
# - Apple Development
```

### 2.2 Проверка сертификатов
```bash
# Список доступных сертификатов
security find-identity -v -p codesigning

# Ожидаемый вывод:
# 1) ABC1234567890ABCDEF1234567890ABCDEF1234 "Developer ID Application: Your Name (TEAM_ID)"
# 2) DEF1234567890ABCDEF1234567890ABCDEF1234 "Developer ID Installer: Your Name (TEAM_ID)"
```

## 📝 Шаг 3: Создание Entitlements

### 3.1 Основные права доступа
```xml
<!-- entitlements/audio_device_manager.entitlements -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Аудио устройства -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.audio-output</key>
    <true/>
    
    <!-- Сеть для обновлений -->
    <key>com.apple.security.network.client</key>
    <true/>
    
    <!-- Файловая система -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    
    <!-- Системные события -->
    <key>com.apple.security.automation.apple-events</key>
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

## 🏗️ Шаг 4: Сборка приложения

### 4.1 Создание скрипта сборки
```bash
#!/bin/bash
# scripts/build.sh

set -e

echo "🔨 Начинаем сборку Audio Device Manager..."

# Очистка предыдущих сборок
rm -rf build/ dist/

# Сборка с PyInstaller
pyinstaller audio_device_manager.spec \
    --clean \
    --noconfirm \
    --log-level=INFO

echo "✅ Сборка завершена"
```

### 4.2 Создание Info.plist
```xml
<!-- Info.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleDisplayName</key>
    <string>Audio Device Manager</string>
    <key>CFBundleIdentifier</key>
    <string>com.yourcompany.audio-device-manager</string>
    <key>CFBundleName</key>
    <string>AudioDeviceManager</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleExecutable</key>
    <string>AudioDeviceManager</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSMicrophoneUsageDescription</key>
    <string>Audio Device Manager needs microphone access to manage audio devices.</string>
    <key>NSCameraUsageDescription</key>
    <string>Audio Device Manager may need camera access for device management.</string>
</dict>
</plist>
```

## ✍️ Шаг 5: Подписание кода

### 5.1 Подписание исполняемого файла
```bash
#!/bin/bash
# scripts/sign.sh

set -e

APP_PATH="dist/AudioDeviceManager.app"
ENTITLEMENTS="entitlements/audio_device_manager.entitlements"
IDENTITY="Developer ID Application: Your Name (TEAM_ID)"

echo "✍️ Подписываем приложение..."

# Подписание всех исполняемых файлов
find "$APP_PATH" -name "*.so" -exec codesign --force --sign "$IDENTITY" {} \;
find "$APP_PATH" -name "*.dylib" -exec codesign --force --sign "$IDENTITY" {} \;

# Подписание основного приложения
codesign --force \
    --sign "$IDENTITY" \
    --entitlements "$ENTITLEMENTS" \
    --options runtime \
    --timestamp \
    "$APP_PATH"

echo "✅ Подписание завершено"

# Проверка подписи
codesign --verify --verbose "$APP_PATH"
spctl --assess --verbose "$APP_PATH"
```

## 📦 Шаг 6: Создание PKG пакета

### 6.1 Создание скрипта установки
```bash
#!/bin/bash
# scripts/postinstall.sh

set -e

echo "📦 Устанавливаем Audio Device Manager..."

# Создание директории приложения
APP_DIR="/Applications/Audio Device Manager"
mkdir -p "$APP_DIR"

# Копирование приложения
cp -R "AudioDeviceManager.app" "$APP_DIR/"

# Установка прав доступа
chmod -R 755 "$APP_DIR"
chown -R root:admin "$APP_DIR"

# Создание символических ссылок
ln -sf "$APP_DIR/AudioDeviceManager.app/Contents/MacOS/AudioDeviceManager" /usr/local/bin/audio-device-manager

echo "✅ Установка завершена"
```

### 6.2 Создание PKG с pkgbuild
```bash
#!/bin/bash
# scripts/create_pkg.sh

set -e

echo "📦 Создаем PKG пакет..."

# Создание временной директории
TEMP_DIR="temp_pkg"
mkdir -p "$TEMP_DIR"

# Копирование файлов
cp -R "dist/AudioDeviceManager.app" "$TEMP_DIR/"
cp "scripts/postinstall.sh" "$TEMP_DIR/"

# Создание PKG
pkgbuild \
    --root "$TEMP_DIR" \
    --identifier "com.yourcompany.audio-device-manager" \
    --version "1.0.0" \
    --install-location "/Applications" \
    --scripts "scripts" \
    "AudioDeviceManager-1.0.0.pkg"

# Очистка
rm -rf "$TEMP_DIR"

echo "✅ PKG пакет создан: AudioDeviceManager-1.0.0.pkg"
```

## 🔒 Шаг 7: Подписание PKG

### 7.1 Подписание установочного пакета
```bash
#!/bin/bash
# scripts/sign_pkg.sh

set -e

PKG_FILE="AudioDeviceManager-1.0.0.pkg"
INSTALLER_IDENTITY="Developer ID Installer: Your Name (TEAM_ID)"

echo "✍️ Подписываем PKG пакет..."

# Подписание PKG
productsign \
    --sign "$INSTALLER_IDENTITY" \
    "$PKG_FILE" \
    "AudioDeviceManager-1.0.0-signed.pkg"

echo "✅ PKG подписан: AudioDeviceManager-1.0.0-signed.pkg"

# Проверка подписи
pkgutil --check-signature "AudioDeviceManager-1.0.0-signed.pkg"
```

## 🏛️ Шаг 8: Нотаризация

### 8.1 Подготовка к нотаризации
```bash
#!/bin/bash
# scripts/notarize.sh

set -e

PKG_FILE="AudioDeviceManager-1.0.0-signed.pkg"
APPLE_ID="your-apple-id@example.com"
APP_PASSWORD="your-app-specific-password"
TEAM_ID="5NKLL2CLB9"

echo "🏛️ Начинаем нотаризацию..."

# Отправка на нотаризацию
xcrun notarytool submit "$PKG_FILE" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

echo "✅ Нотаризация завершена"

# Прикрепление тикета нотаризации
xcrun stapler staple "$PKG_FILE"

echo "✅ Тикет прикреплен"
```

### 8.2 Проверка нотаризации
```bash
#!/bin/bash
# scripts/verify_notarization.sh

set -e

PKG_FILE="AudioDeviceManager-1.0.0-signed.pkg"

echo "🔍 Проверяем нотаризацию..."

# Проверка статуса нотаризации
xcrun stapler validate "$PKG_FILE"

# Проверка Gatekeeper
spctl --assess --type install "$PKG_FILE"

echo "✅ Нотаризация проверена успешно"
```

## 🚀 Шаг 9: Автоматизация процесса

### 9.1 Полный скрипт сборки
```bash
#!/bin/bash
# scripts/full_build.sh

set -e

echo "🚀 Полная сборка Audio Device Manager..."

# 1. Сборка
./scripts/build.sh

# 2. Подписание приложения
./scripts/sign.sh

# 3. Создание PKG
./scripts/create_pkg.sh

# 4. Подписание PKG
./scripts/sign_pkg.sh

# 5. Нотаризация
./scripts/notarize.sh

# 6. Проверка
./scripts/verify_notarization.sh

echo "🎉 Полная сборка завершена!"
echo "📦 Готовый пакет: AudioDeviceManager-1.0.0-signed.pkg"
```

## 📋 Чеклист готовности

### Перед сборкой:
- [ ] Apple Developer Account активен
- [ ] Сертификаты установлены в Keychain
- [ ] SwitchAudioSource установлен
- [ ] Python окружение настроено
- [ ] PyInstaller установлен

### После сборки:
- [ ] Приложение запускается без ошибок
- [ ] Подписание прошло успешно
- [ ] PKG создан корректно
- [ ] Нотаризация завершена
- [ ] Gatekeeper проверка пройдена

## 🐛 Решение проблем

### Ошибка подписания:
```bash
# Очистка кэша подписания
sudo rm -rf /var/db/receipts/com.apple.pkg.*
sudo rm -rf /Library/Receipts/com.apple.pkg.*
```

### Ошибка нотаризации:
```bash
# Проверка логов
xcrun notarytool log --apple-id "$APPLE_ID" --password "$APP_PASSWORD" --team-id "$TEAM_ID"
```

### Ошибка Gatekeeper:
```bash
# Временное отключение для тестирования
sudo spctl --master-disable
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сборки
2. Убедитесь в корректности сертификатов
3. Проверьте права доступа к файлам
4. Обратитесь к Apple Developer Documentation

---

**Готово к продакшену!** 🎉
