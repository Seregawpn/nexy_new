# 📦 ПОЛНЫЙ ПЛАН УПАКОВКИ NEXY AI VOICE ASSISTANT

## 🎯 ОБЗОР

Этот документ содержит полный план по настройке, упаковке, подписанию и нотаризации macOS приложения Nexy AI Voice Assistant в PKG установщик.

---

## 📋 СОДЕРЖАНИЕ

1. [Предварительные требования](#предварительные-требования)
2. [Настройка сертификатов](#настройка-сертификатов)
3. [Настройка нотаризации](#настройка-нотаризации)
4. [Подготовка зависимостей](#подготовка-зависимостей)
5. [Конфигурация PyInstaller](#конфигурация-pyinstaller)
6. [Создание скриптов автоматизации](#создание-скриптов-автоматизации)
7. [Процесс упаковки](#процесс-упаковки)
8. [Тестирование](#тестирование)
9. [Распространение](#распространение)
10. [Устранение неполадок](#устранение-неполадок)

---

## 🔧 ПРЕДВАРИТЕЛЬНЫЕ ТРЕБОВАНИЯ

### Системные требования
- **macOS:** 10.15+ (рекомендуется 12.0+)
- **Xcode Command Line Tools:** `xcode-select --install`
- **Python:** 3.9+ (рекомендуется 3.9.6)
- **Homebrew:** для установки зависимостей

### Необходимые инструменты
```bash
# Установка Homebrew (если не установлен)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Установка Python зависимостей
pip3 install -r requirements.txt

# Установка PyInstaller
pip3 install pyinstaller

# Установка системных зависимостей
brew install switchaudio-osx sparkle
```

---

## 🔐 НАСТРОЙКА СЕРТИФИКАТОВ

### 1. Apple Developer Account
- **Требуется:** Активный Apple Developer Account ($99/год)
- **Сертификаты:** Developer ID Application + Developer ID Installer

### 2. Создание сертификатов
```bash
# В Keychain Access:
# 1. Запросить сертификат "Developer ID Application"
# 2. Запросить сертификат "Developer ID Installer"
# 3. Скачать и установить оба сертификата
```

### 3. Проверка сертификатов
```bash
# Проверка Developer ID Application
security find-identity -v -p codesigning | grep "Developer ID Application"

# Проверка Developer ID Installer  
security find-identity -v -p codesigning | grep "Developer ID Installer"
```

**Ожидаемый результат:**
```
1) ABC1234567890ABCDEF1234567890ABCDEF1234 "Developer ID Application: Your Name (TEAM_ID)"
2) FED0987654321FEDCBA0987654321FEDCBA0987 "Developer ID Installer: Your Name (TEAM_ID)"
```

---

## 🔐 НАСТРОЙКА НОТАРИЗАЦИИ

### 1. App-Specific Password
1. Перейти на [appleid.apple.com](https://appleid.apple.com)
2. Войти в Apple ID
3. В разделе "Security" → "App-Specific Passwords"
4. Создать новый пароль для "Notarization"
5. Сохранить пароль (понадобится только один раз)

### 2. Конфигурация нотаризации
Создать файл `client/notarize_config.sh`:
```bash
#!/bin/bash
# Конфигурация для нотаризации Nexy AI Voice Assistant

# Apple ID для нотаризации
export APPLE_ID="your-email@example.com"

# App-Specific Password (создайте в appleid.apple.com)
export APP_PASSWORD="abcd-efgh-ijkl-mnop"

# Team ID (найти в Apple Developer Portal)
export TEAM_ID="YOUR_TEAM_ID"

# Bundle ID
export BUNDLE_ID="com.sergiyzasorin.nexy.voiceassistant"
```

### 3. Тест подключения к Apple
```bash
# Проверка подключения к Apple Notary Service
xcrun notarytool history \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID"
```

---

## 📦 ПОДГОТОВКА ЗАВИСИМОСТЕЙ

### 1. Python зависимости
Файл `client/requirements.txt`:
```txt
# Основные зависимости
grpcio==1.74.0
grpcio-tools==1.74.0
protobuf==4.25.1
aiohttp==3.9.1
rumps==0.3.0
pystray==0.19.4
pynput==1.7.6
sounddevice==0.4.6
speechrecognition==3.10.0
pydub==0.25.1
numpy==1.24.3
Pillow==10.1.0
pyyaml==6.0.1

# PyObjC фреймворки для macOS
pyobjc-core==9.2
pyobjc-framework-Cocoa==9.2
pyobjc-framework-CoreAudio==9.2
pyobjc-framework-CoreFoundation==9.2
pyobjc-framework-AVFoundation==9.2
pyobjc-framework-Quartz==9.2
pyobjc-framework-ApplicationServices==9.2
pyobjc-framework-SystemConfiguration==9.2
```

### 2. Системные зависимости
```bash
# SwitchAudioSource для переключения аудио устройств
brew install switchaudio-osx

# Sparkle Framework для автообновлений (опционально)
brew install sparkle
```

### 3. FLAC интеграция
```bash
# Установка FLAC 1.5.0
brew install flac

# Замена встроенного FLAC в speech_recognition
# (выполняется автоматически в скрипте update_flac.sh)
```

---

## ⚙️ КОНФИГУРАЦИЯ PYINSTALLER

### 1. Основной spec файл
Файл `client/nexy.spec`:
```python
# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from pathlib import Path

# Импорты PyInstaller (для версии 6.x)
from PyInstaller.building.api import EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.building.osx import BUNDLE

# Конфигурация путей
client_dir = Path('.').resolve()
assets_dir = client_dir / 'assets'
pkg_root = client_dir / 'pkg_root'

# Проверка Sparkle Framework
sparkle_framework = "/usr/local/lib/Sparkle.framework"

# Создание Info.plist с автоматической настройкой Sparkle
info_plist = {
    'CFBundleName': 'Nexy',
    'CFBundleDisplayName': 'Nexy AI Voice Assistant',
    'CFBundleIdentifier': 'com.sergiyzasorin.nexy.voiceassistant',
    'CFBundleVersion': '1.71.0',
    'CFBundleShortVersionString': '1.71.0',
    'CFBundlePackageType': 'APPL',
    'CFBundleSignature': '????',
    'CFBundleExecutable': 'Nexy',
    'CFBundleIconFile': 'app.icns',
    
    # TCC разрешения
    'NSMicrophoneUsageDescription': 'Nexy использует микрофон для распознавания голосовых команд',
    'NSCameraUsageDescription': 'Nexy может использовать камеру для дополнительных функций',
    'NSScreenCaptureUsageDescription': 'Nexy может захватывать экран для анализа контента',
    'NSAppleEventsUsageDescription': 'Nexy использует Apple Events для автоматизации задач',
    
    # Настройки приложения
    'LSUIElement': True,  # Скрытое приложение (только в трее)
    'NSBackgroundOnly': False,  # Может работать в фоне, но не только в фоне
    'NSSupportsAutomaticTermination': False,  # Не завершать автоматически
    'NSSupportsSuddenTermination': False,  # Не завершать внезапно
    
    # Переменные окружения
    'LSEnvironment': {
        'PYTHONPATH': '/Applications/Nexy.app/Contents/Resources'
    }
}

# Автоматическая настройка Sparkle в Info.plist (если установлен)
if os.path.exists(sparkle_framework):
    info_plist.update({
        'SUFeedURL': 'http://localhost:8080/appcast.xml',
        'SUPublicEDKey': 'yixFT+HhjLehYH6sT8riFb1etq/hpXFWNqiGkZOBHjE=',
        'SUEnableAutomaticChecks': True,
        'SUAllowsAutomaticUpdates': True,
        'SUAutomaticallyUpdate': True
    })
    print("✅ Sparkle настройки добавлены в Info.plist")

# Анализ зависимостей
a = Analysis(
    ['main.py'],
    pathex=[str(client_dir)],
    binaries=[],
    datas=[
        # Конфигурационные файлы
        (str(assets_dir / 'icons' / 'app.icns'), 'assets/icons/'),
        (str(assets_dir / 'icons' / 'active.png'), 'assets/icons/'),
        (str(assets_dir / 'icons' / 'active@2x.png'), 'assets/icons/'),
        (str(assets_dir / 'icons' / 'off.png'), 'assets/icons/'),
        (str(assets_dir / 'icons' / 'off@2x.png'), 'assets/icons/'),
        (str(assets_dir / 'logo.icns'), 'assets/'),
        
        # Конфигурация
        ('config/app_config.yaml', 'config/'),
        ('config/logging_config.yaml', 'config/'),
        
        # LaunchAgent файлы
        (str(pkg_root / 'Library' / 'LaunchAgents' / 'com.sergiyzasorin.nexy.voiceassistant.plist'), 'Resources/'),
        (str(pkg_root / 'Library' / 'LaunchAgents' / 'nexy_launcher.sh'), 'Resources/'),
        
        # Entitlements
        ('entitlements.plist', '.'),
    ],
    hiddenimports=[
        # Основные модули
        'aiohttp', 'rumps', 'pystray', 'pynput', 'sounddevice',
        'speech_recognition', 'pydub', 'numpy', 'PIL', 'yaml',
        'grpcio', 'grpcio_tools', 'protobuf',
        
        # PyObjC фреймворки
        'pyobjc', 'pyobjc_framework_Cocoa', 'pyobjc_framework_CoreAudio',
        'pyobjc_framework_CoreFoundation', 'pyobjc_framework_AVFoundation',
        'pyobjc_framework_Quartz', 'pyobjc_framework_ApplicationServices',
        'pyobjc_framework_SystemConfiguration',
        
        # Стандартные библиотеки
        'asyncio', 'logging', 'threading', 'json', 'signal', 'typing',
        'dataclasses', 'urllib', 'socket', 'ssl', 'zipfile', 'tarfile',
        'tempfile', 'shutil', 'glob', 'fnmatch', 'pathlib', 'os', 'sys'
    ],
    hookspath=[str(client_dir)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Создание PYZ архива
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

# Создание исполняемого файла
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Nexy',
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
    entitlements_file=None,
)

# Создание .app bundle
app = BUNDLE(
    exe,
    name='Nexy.app',
    icon=str(assets_dir / 'icons' / 'app.icns'),
    bundle_identifier='com.sergiyzasorin.nexy.voiceassistant',
    info_plist=info_plist
)
```

### 2. Entitlements файл
Файл `client/entitlements.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Критические разрешения -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    
    <!-- Сетевые разрешения -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- JIT и выполнение кода -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    
    <!-- Bluetooth для аудио устройств -->
    <key>com.apple.security.device.bluetooth</key>
    <true/>
    
    <!-- Доступ к системным настройкам -->
    <key>com.apple.security.device.usb</key>
    <true/>
</dict>
</plist>
```

---

## 🤖 СОЗДАНИЕ СКРИПТОВ АВТОМАТИЗАЦИИ

### 1. Основной скрипт сборки
Файл `client/build_complete.sh`:
```bash
#!/bin/bash
# Полная автоматизированная сборка Nexy AI Voice Assistant

set -e

echo "🚀 ПОЛНАЯ СБОРКА NEXY AI VOICE ASSISTANT"
echo "========================================"

# Этап 1: Предварительная проверка
echo ""
echo "📋 ЭТАП 1: Предварительная проверка"
echo "-----------------------------------"
./verify_packaging.sh
echo "✅ Предварительная проверка завершена"

# Этап 2: Установка зависимостей
echo ""
echo "📋 ЭТАП 2: Установка зависимостей"
echo "---------------------------------"
if ! command -v SwitchAudioSource &> /dev/null; then
    echo "📦 Установка SwitchAudioSource..."
    brew install switchaudio-osx
else
    echo "✅ SwitchAudioSource уже установлен"
fi

if [ ! -d "/usr/local/lib/Sparkle.framework" ]; then
    echo "📦 Установка Sparkle Framework..."
    brew install sparkle || echo "⚠️ Sparkle Framework не установлен (опционально)"
else
    echo "✅ Sparkle Framework уже установлен"
fi

# Этап 3: Сборка приложения
echo ""
echo "📋 ЭТАП 3: Сборка приложения"
echo "----------------------------"
echo "🧹 Очистка предыдущих сборок..."
rm -rf build/ dist/

echo "🔨 Сборка через PyInstaller..."
python3 -m PyInstaller nexy.spec --clean --noconfirm

if [ ! -d "dist/Nexy.app" ]; then
    echo "❌ Ошибка сборки приложения"
    exit 1
fi
echo "✅ Приложение собрано успешно"

# Этап 4: Подпись Sparkle Framework (если включен)
echo ""
echo "📋 ЭТАП 4: Подпись Sparkle Framework"
echo "-----------------------------------"
./sign_sparkle.sh
echo "✅ Sparkle Framework подписан"

# Этап 5: Создание PKG
echo ""
echo "📋 ЭТАП 5: Создание PKG установщика"
echo "-----------------------------------"
./create_pkg.sh

if [ ! -f "Nexy_AI_Voice_Assistant_v1.71.0.pkg" ]; then
    echo "❌ Ошибка создания PKG"
    exit 1
fi
echo "✅ PKG создан успешно"

# Этап 6: Нотаризация
echo ""
echo "📋 ЭТАП 6: Нотаризация PKG"
echo "--------------------------"
./notarize.sh Nexy_AI_Voice_Assistant_v1.71.0.pkg
echo "✅ PKG нотаризован успешно"

# Этап 7: Финальная проверка
echo ""
echo "📋 ЭТАП 7: Финальная проверка"
echo "-----------------------------"
echo "🔍 Проверка подписи PKG..."
codesign --verify --verbose Nexy_AI_Voice_Assistant_v1.71.0.pkg

echo "📊 Информация о PKG:"
du -h Nexy_AI_Voice_Assistant_v1.71.0.pkg
pkgutil --check-signature Nexy_AI_Voice_Assistant_v1.71.0.pkg

echo ""
echo "🎉 СБОРКА ЗАВЕРШЕНА УСПЕШНО!"
echo "============================="
echo "📦 Готовый PKG: Nexy_AI_Voice_Assistant_v1.71.0.pkg"
echo "📱 Приложение: dist/Nexy.app"
echo ""
echo "📋 Информация о продукте:"
echo "   • Версия: 1.71.0"
echo "   • Bundle ID: com.sergiyzasorin.nexy.voiceassistant"
echo "   • Подпись: Developer ID Application/Installer"
echo "   • Нотаризация: ✅ Подтверждена Apple"
echo "   • Размер: $(du -h Nexy_AI_Voice_Assistant_v1.71.0.pkg | cut -f1)"
echo ""
echo "🚀 PKG готов к распространению!"
```

### 2. Скрипт создания PKG
Файл `client/create_pkg.sh`:
```bash
#!/bin/bash
set -e

APP_NAME="Nexy"
APP_VERSION="1.71.0"
PKG_NAME="Nexy_AI_Voice_Assistant_v${APP_VERSION}.pkg"
BUNDLE_ID="com.sergiyzasorin.nexy.voiceassistant"
DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"

echo "📦 Создание PKG установщика..."

# Создание временной директории
TEMP_DIR=$(mktemp -d)
PKG_ROOT="$TEMP_DIR/pkgroot"
APP_DIR="$PKG_ROOT/Applications"
LAUNCH_AGENTS_DIR="$PKG_ROOT/Library/LaunchAgents"

mkdir -p "$APP_DIR"
mkdir -p "$LAUNCH_AGENTS_DIR"

# Копирование приложения
cp -R "dist/Nexy.app" "$APP_DIR/"

# Копирование LaunchAgent файлов
if [ -f "pkg_root/Library/LaunchAgents/com.sergiyzasorin.nexy.voiceassistant.plist" ]; then
    cp "pkg_root/Library/LaunchAgents/com.sergiyzasorin.nexy.voiceassistant.plist" "$LAUNCH_AGENTS_DIR/"
    echo "✅ LaunchAgent plist скопирован"
fi

if [ -f "pkg_root/Library/LaunchAgents/nexy_launcher.sh" ]; then
    cp "pkg_root/Library/LaunchAgents/nexy_launcher.sh" "$LAUNCH_AGENTS_DIR/"
    chmod +x "$LAUNCH_AGENTS_DIR/nexy_launcher.sh"
    echo "✅ LaunchAgent скрипт скопирован"
fi

# Очистка расширенных атрибутов
xattr -cr "$APP_DIR/Nexy.app"

# Код-подпись приложения
echo "🔐 Подписание приложения..."
if codesign --force --verify --verbose --sign "$DEVELOPER_ID_APP" \
    --options runtime \
    --entitlements entitlements.plist \
    "$APP_DIR/Nexy.app"; then
    echo "✅ Приложение подписано успешно"
else
    echo "❌ Ошибка подписания приложения"
    exit 1
fi

# Создание PKG
echo "📦 Создание PKG..."
if pkgbuild --root "$PKG_ROOT" \
    --identifier "$BUNDLE_ID" \
    --version "$APP_VERSION" \
    --install-location "/" \
    --sign "$DEVELOPER_ID_INSTALLER" \
    "$PKG_NAME"; then
    echo "✅ PKG создан успешно"
else
    echo "❌ Ошибка создания PKG"
    exit 1
fi

# Очистка
rm -rf "$TEMP_DIR"

echo "✅ PKG создан: $PKG_NAME"
echo "ℹ️ Убедитесь, что пользователи установили зависимости: brew install switchaudio-osx sparkle"
```

### 3. Скрипт нотаризации
Файл `client/notarize.sh`:
```bash
#!/bin/bash
set -e

# Загружаем конфигурацию
source "$(dirname "$0")/notarize_config.sh"

PKG_NAME="$1"

if [ -z "$PKG_NAME" ]; then
    echo "❌ Использование: ./notarize.sh <PKG_NAME>"
    exit 1
fi

echo "🔐 Нотаризация PKG: $PKG_NAME"

# Проверка существования файла
if [ ! -f "$PKG_NAME" ]; then
    echo "❌ PKG файл не найден: $PKG_NAME"
    exit 1
fi

# Отправка на нотаризацию
echo "📤 Отправка на нотаризацию Apple..."
if xcrun notarytool submit "$PKG_NAME" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait; then
    echo "✅ Нотаризация прошла успешно"
else
    echo "❌ Ошибка нотаризации"
    exit 1
fi

# Прикрепление тикета
echo "📎 Прикрепление нотаризационного тикета..."
if xcrun stapler staple "$PKG_NAME"; then
    echo "✅ Тикет прикреплен успешно"
else
    echo "❌ Ошибка прикрепления тикета"
    exit 1
fi

echo "✅ PKG нотаризован и готов к распространению!"
```

### 4. Скрипт проверки готовности
Файл `client/verify_packaging.sh`:
```bash
#!/bin/bash
# Полная проверка готовности к упаковке Nexy AI Voice Assistant

set -e

echo "🔍 Полная проверка готовности к упаковке Nexy AI Voice Assistant"
echo "=================================================================="

# Проверка сертификатов
echo ""
echo "📱 Проверка сертификатов..."
if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then
    echo "✅ Developer ID Application найден"
else
    echo "❌ Developer ID Application не найден"
    exit 1
fi

if security find-identity -v -p codesigning | grep -q "Developer ID Installer"; then
    echo "✅ Developer ID Installer найден"
else
    echo "❌ Developer ID Installer не найден"
    exit 1
fi

# Проверка системных зависимостей
echo ""
echo "🔧 Проверка системных зависимостей..."
if command -v SwitchAudioSource &> /dev/null; then
    echo "✅ SwitchAudioSource найден"
else
    echo "⚠️ SwitchAudioSource не найден (установите: brew install switchaudio-osx)"
fi

if [ -d "/usr/local/lib/Sparkle.framework" ]; then
    echo "✅ Sparkle Framework найден"
else
    echo "⚠️ Sparkle Framework не найден (опционально для автообновлений)"
fi

# Проверка Python зависимостей
echo ""
echo "🐍 Проверка Python зависимостей..."
MISSING_MODULES=()
REQUIRED_MODULES=("grpcio" "aiohttp" "rumps" "pystray" "pynput" "sounddevice" "speech_recognition" "pydub" "numpy" "PIL" "yaml")

for module in "${REQUIRED_MODULES[@]}"; do
    if python3 -c "import $module" 2>/dev/null; then
        echo "✅ $module найден"
    else
        echo "❌ $module не найден"
        MISSING_MODULES+=("$module")
    fi
done

if [ ${#MISSING_MODULES[@]} -gt 0 ]; then
    echo "❌ Отсутствуют модули: ${MISSING_MODULES[*]}"
    echo "💡 Установите: pip3 install -r requirements.txt"
    exit 1
fi

# Проверка файлов конфигурации
echo ""
echo "📋 Проверка файлов конфигурации..."
REQUIRED_FILES=("nexy.spec" "entitlements.plist" "notarize_config.sh" "create_pkg.sh" "notarize.sh" "sign_sparkle.sh")

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file найден"
    else
        echo "❌ $file не найден"
        exit 1
    fi
done

# Проверка FLAC в Speech Recognition
echo ""
echo "🎵 Проверка FLAC в Speech Recognition..."
FLAC_VERSION=$(python3 -c "import speech_recognition; print(speech_recognition.__version__)" 2>/dev/null || echo "неизвестно")
echo "ℹ️ Speech Recognition версия: $FLAC_VERSION"

# Проверка конфигурации нотаризации
echo ""
echo "🔐 Проверка конфигурации нотаризации..."
if [ -f "notarize_config.sh" ]; then
    source notarize_config.sh
    echo "🔐 Конфигурация нотаризации:"
    echo "   Apple ID: $APPLE_ID"
    echo "   Team ID: $TEAM_ID"
    echo "   Bundle ID: $BUNDLE_ID"
    echo "   App Password: ${APP_PASSWORD:0:4}****"
else
    echo "❌ notarize_config.sh не найден"
    exit 1
fi

# Тест подключения к Apple
echo ""
echo "🍎 Тест подключения к Apple..."
if xcrun notarytool history \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" &>/dev/null; then
    echo "✅ Подключение к Apple работает"
else
    echo "❌ Проблемы с подключением к Apple"
    exit 1
fi

echo ""
echo "🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!"
echo "🚀 Система готова к упаковке: ./build_complete.sh"
```

---

## 🚀 ПРОЦЕСС УПАКОВКИ

### 1. Быстрый старт
```bash
cd client/
chmod +x *.sh
./build_complete.sh
```

### 2. Пошаговый процесс

#### Шаг 1: Подготовка
```bash
# Переход в директорию клиента
cd client/

# Установка прав на выполнение
chmod +x *.sh

# Проверка готовности
./verify_packaging.sh
```

#### Шаг 2: Сборка приложения
```bash
# Очистка предыдущих сборок
rm -rf build/ dist/

# Сборка через PyInstaller
python3 -m PyInstaller nexy.spec --clean --noconfirm
```

#### Шаг 3: Создание PKG
```bash
# Создание PKG установщика
./create_pkg.sh
```

#### Шаг 4: Нотаризация
```bash
# Отправка на нотаризацию Apple
./notarize.sh Nexy_AI_Voice_Assistant_v1.71.0.pkg
```

### 3. Полная автоматизация
```bash
# Один скрипт для всего процесса
./rebuild_and_notarize.sh
```

---

## 🧪 ТЕСТИРОВАНИЕ

### 1. Проверка подписи
```bash
# Проверка подписи PKG
pkgutil --check-signature Nexy_AI_Voice_Assistant_v1.71.0.pkg

# Проверка подписи .app bundle
codesign --verify --verbose dist/Nexy.app
```

### 2. Проверка нотаризации
```bash
# Проверка нотаризационного тикета
xcrun stapler validate Nexy_AI_Voice_Assistant_v1.71.0.pkg

# Проверка Gatekeeper
spctl --assess --verbose Nexy_AI_Voice_Assistant_v1.71.0.pkg
```

### 3. Тестирование установки
```bash
# Установка PKG
sudo installer -pkg Nexy_AI_Voice_Assistant_v1.71.0.pkg -target /

# Проверка установки
ls -la /Applications/Nexy.app
```

### 4. Тестирование функциональности
```bash
# Запуск приложения
open /Applications/Nexy.app

# Проверка в трее
# Проверка голосовых команд
# Проверка автозапуска
```

---

## 📤 РАСПРОСТРАНЕНИЕ

### 1. Готовый PKG
- **Файл:** `Nexy_AI_Voice_Assistant_v1.71.0.pkg`
- **Размер:** ~59MB
- **Статус:** ✅ Подписан и нотаризован
- **Совместимость:** macOS 10.15+

### 2. Требования для пользователей
```bash
# Установка зависимостей
brew install switchaudio-osx

# Опционально для автообновлений
brew install sparkle
```

### 3. Инструкции для пользователей
1. Скачать PKG файл
2. Дважды кликнуть для установки
3. Следовать инструкциям установщика
4. Разрешить доступ к микрофону при первом запуске
5. Приложение появится в трее

---

## 🔧 УСТРАНЕНИЕ НЕПОЛАДОК

### Проблема: Ошибка подписания
```
error: file with invalid attached data: Disallowed xattr com.apple.FinderInfo
```
**Решение:**
```bash
# Очистка расширенных атрибутов
xattr -cr dist/Nexy.app
```

### Проблема: Ошибка нотаризации
```
Error: HTTP status code: 401. Invalid credentials
```
**Решение:**
1. Проверить Apple ID в `notarize_config.sh`
2. Создать новый App-Specific Password
3. Проверить Team ID

### Проблема: PyInstaller не найден
```
zsh: command not found: pyinstaller
```
**Решение:**
```bash
# Использовать python3 -m PyInstaller
python3 -m PyInstaller nexy.spec --clean --noconfirm
```

### Проблема: Отсутствуют зависимости
```
ModuleNotFoundError: No module named 'grpcio'
```
**Решение:**
```bash
# Установка зависимостей
pip3 install -r requirements.txt
```

### Проблема: Ошибка сборки
```
ERROR: Hidden import 'grpcio' not found
```
**Решение:**
1. Проверить установку модуля: `pip3 install grpcio`
2. Обновить `hiddenimports` в `nexy.spec`

---

## 📚 ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ

### Полезные команды
```bash
# Проверка сертификатов
security find-identity -v -p codesigning

# Проверка подписи файла
codesign --verify --verbose file.app

# Проверка нотаризации
xcrun stapler validate file.pkg

# Очистка атрибутов
xattr -cr file.app

# Информация о PKG
pkgutil --check-signature file.pkg
```

### Ссылки на документацию
- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Apple Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)
- [macOS App Store Guidelines](https://developer.apple.com/app-store/review/guidelines/)

---

## ✅ ЧЕКЛИСТ ГОТОВНОСТИ

### Перед упаковкой
- [ ] Apple Developer Account активен
- [ ] Сертификаты установлены в Keychain
- [ ] App-Specific Password создан
- [ ] `notarize_config.sh` настроен
- [ ] Python зависимости установлены
- [ ] Системные зависимости установлены
- [ ] `nexy.spec` настроен
- [ ] `entitlements.plist` создан

### После упаковки
- [ ] .app bundle создан
- [ ] .app bundle подписан
- [ ] PKG создан
- [ ] PKG подписан
- [ ] PKG нотаризован
- [ ] Тикет прикреплен
- [ ] Функциональность протестирована

### Перед распространением
- [ ] PKG протестирован на чистой системе
- [ ] Все функции работают
- [ ] Автозапуск работает
- [ ] Разрешения запрашиваются корректно
- [ ] Документация для пользователей готова

---

## 🎯 ЗАКЛЮЧЕНИЕ

Этот план обеспечивает полную автоматизацию процесса упаковки, подписания и нотаризации macOS приложения Nexy AI Voice Assistant. Следуя этому руководству, вы сможете создать профессиональный PKG установщик, готовый к распространению.

**Ключевые преимущества:**
- ✅ Полная автоматизация процесса
- ✅ Соответствие требованиям Apple
- ✅ Профессиональная подпись и нотаризация
- ✅ Включение всех необходимых компонентов
- ✅ Подробная документация и чеклисты

**Время выполнения:** ~15-20 минут (включая нотаризацию)
**Результат:** Готовый к распространению PKG файл