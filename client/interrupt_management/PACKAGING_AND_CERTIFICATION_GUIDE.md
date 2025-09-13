# Руководство по упаковке и сертификации interrupt_management для macOS

## 📋 Обзор

Данное руководство описывает процесс упаковки модуля `interrupt_management` в приложение для macOS, включая подписание кода, нотаризацию и распространение через PKG пакеты.

## 🏗️ Архитектура упаковки

### Структура пакета:
```
Nexy.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── nexy
│   ├── Resources/
│   │   ├── interrupt_management/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   ├── handlers/
│   │   │   └── config/
│   │   └── other_modules/
│   └── Frameworks/
└── _CodeSignature/
    └── CodeResources
```

## 🔧 Системные требования

### 1. Разработка
- **macOS**: 10.15+ (Catalina или новее)
- **Xcode**: 12.0+ (для инструментов подписания)
- **Python**: 3.8+ (встроенный в macOS)
- **py2app**: 0.28+ (для создания .app пакетов)

### 2. Сертификация
- **Apple Developer Account**: Активная подписка ($99/год)
- **Developer ID Application**: Сертификат для подписания
- **Developer ID Installer**: Сертификат для PKG пакетов
- **Notarization**: Доступ к Apple Notarization Service

## 🚀 Пошаговая упаковка

### Шаг 1: Подготовка окружения
```bash
# Установка зависимостей
pip install py2app
pip install pyobjc-framework-Cocoa
pip install pyobjc-framework-Security

# Создание виртуального окружения
python3 -m venv venv
source venv/bin/activate
```

### Шаг 2: Создание setup.py
```python
# setup.py для interrupt_management
from setuptools import setup, find_packages
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

APP = ['main.py']
DATA_FILES = [
    ('interrupt_management', [
        'interrupt_management/__init__.py',
        'interrupt_management/core/interrupt_coordinator.py',
        'interrupt_management/core/types.py',
        'interrupt_management/handlers/speech_interrupt.py',
        'interrupt_management/handlers/recording_interrupt.py',
        'interrupt_management/config/interrupt_config.py',
    ]),
    ('config', [
        'config/app_config.yaml',
        'config/logging_config.yaml',
    ]),
]

OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'assets/logo.icns',
    'plist': {
        'CFBundleName': 'Nexy',
        'CFBundleDisplayName': 'Nexy',
        'CFBundleIdentifier': 'com.nexy.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleExecutable': 'nexy',
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': 'NEXY',
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSMicrophoneUsageDescription': 'Nexy использует микрофон для распознавания речи',
        'NSCameraUsageDescription': 'Nexy использует камеру для захвата экрана',
        'NSDesktopFolderUsageDescription': 'Nexy сохраняет файлы на рабочий стол',
        'NSDocumentsFolderUsageDescription': 'Nexy сохраняет документы в папку Документы',
    },
    'includes': [
        'interrupt_management',
        'asyncio',
        'logging',
        'dataclasses',
        'enum',
        'typing',
    ],
    'excludes': [
        'tkinter',
        'unittest',
        'test',
        'tests',
    ],
    'packages': [
        'interrupt_management',
        'interrupt_management.core',
        'interrupt_management.handlers',
        'interrupt_management.config',
    ],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
    name='Nexy',
    version='1.0.0',
    description='Nexy - AI Assistant Application',
    author='Nexy Team',
    author_email='team@nexy.app',
    url='https://nexy.app',
)
```

### Шаг 3: Создание entitlements.plist
```xml
<!-- entitlements.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Основные права -->
    <key>com.apple.security.app-sandbox</key>
    <true/>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    
    <!-- Сетевые права -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- Файловая система -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    <key>com.apple.security.files.pictures.read-write</key>
    <true/>
    <key>com.apple.security.files.music.read-write</key>
    <true/>
    <key>com.apple.security.files.movies.read-write</key>
    <true/>
    
    <!-- Аудио и видео -->
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.device.camera</key>
    <true/>
    
    <!-- Системные права -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    <key>com.apple.security.print</key>
    <true/>
    
    <!-- Права для interrupt_management -->
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.cs.disable-executable-page-protection</key>
    <true/>
</dict>
</plist>
```

### Шаг 4: Сборка приложения
```bash
# Очистка предыдущих сборок
rm -rf build/ dist/

# Сборка приложения
python setup.py py2app

# Проверка структуры
ls -la dist/Nexy.app/Contents/
```

### Шаг 5: Подписание кода
```bash
# Подписание основного исполняемого файла
codesign --force --verify --verbose --sign "Developer ID Application: Your Name (TEAM_ID)" \
    --entitlements entitlements.plist \
    --options runtime \
    dist/Nexy.app

# Подписание всех внутренних файлов
find dist/Nexy.app -name "*.so" -exec codesign --force --verify --verbose \
    --sign "Developer ID Application: Your Name (TEAM_ID)" {} \;

find dist/Nexy.app -name "*.dylib" -exec codesign --force --verify --verbose \
    --sign "Developer ID Application: Your Name (TEAM_ID)" {} \;

# Проверка подписи
codesign --verify --verbose dist/Nexy.app
spctl --assess --verbose dist/Nexy.app
```

### Шаг 6: Нотаризация
```bash
# Создание архива для нотаризации
ditto -c -k --keepParent dist/Nexy.app Nexy.zip

# Отправка на нотаризацию
xcrun notarytool submit Nexy.zip \
    --apple-id "your-email@example.com" \
    --password "app-specific-password" \
    --team-id "TEAM_ID" \
    --wait

# Прикрепление тикета нотаризации
xcrun stapler staple dist/Nexy.app

# Проверка нотаризации
spctl --assess --type execute --verbose dist/Nexy.app
```

## 📦 Создание PKG пакета

### 1. Создание Distribution.xml
```xml
<!-- Distribution.xml -->
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Nexy 1.0.0</title>
    <organization>com.nexy</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="false"/>
    
    <!-- Требования к системе -->
    <requirements>
        <requirement type="os" version="10.15.0"/>
        <requirement type="architecture" value="x86_64"/>
        <requirement type="architecture" value="arm64"/>
    </requirements>
    
    <!-- Содержимое пакета -->
    <choices-outline>
        <line choice="default">
            <line choice="nexy"/>
        </line>
    </choices-outline>
    
    <choice id="default"/>
    <choice id="nexy" visible="false">
        <pkg-ref id="com.nexy.app"/>
    </choice>
    
    <pkg-ref id="com.nexy.app" version="1.0.0" onConclusion="none">Nexy.pkg</pkg-ref>
    
    <!-- Установка -->
    <installation-check script="pm_install_check();"/>
    <script>
        function pm_install_check() {
            if(!(system.version.ProductVersion >= '10.15.0')) {
                my.result.title = 'Несовместимая версия macOS';
                my.result.message = 'Nexy требует macOS 10.15 или новее.';
                my.result.type = 'Fatal';
                return false;
            }
            return true;
        }
    </script>
</installer-gui-script>
```

### 2. Создание PKG пакета
```bash
# Создание пакета приложения
pkgbuild --root dist/ \
    --identifier com.nexy.app \
    --version 1.0.0 \
    --install-location /Applications \
    --sign "Developer ID Installer: Your Name (TEAM_ID)" \
    Nexy.pkg

# Создание финального PKG
productbuild --distribution Distribution.xml \
    --package-path . \
    --sign "Developer ID Installer: Your Name (TEAM_ID)" \
    Nexy-1.0.0.pkg

# Проверка пакета
pkgutil --check-signature Nexy-1.0.0.pkg
```

## 🔒 Требования безопасности

### 1. Права доступа для interrupt_management
```xml
<!-- Дополнительные права в entitlements.plist -->
<key>com.apple.security.cs.allow-dyld-environment-variables</key>
<true/>
<key>com.apple.security.cs.disable-executable-page-protection</key>
<true/>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>
```

### 2. Проверка безопасности
```bash
# Проверка подписи всех компонентов
find dist/Nexy.app -type f -exec codesign --verify {} \;

# Проверка entitlements
codesign -d --entitlements - dist/Nexy.app

# Проверка на вирусы
spctl --assess --type execute --verbose dist/Nexy.app
```

## 🧪 Тестирование упаковки

### 1. Локальное тестирование
```bash
# Тестирование на локальной машине
open dist/Nexy.app

# Проверка логов
log show --predicate 'process == "nexy"' --last 1h

# Проверка разрешений
spctl --assess --type execute --verbose dist/Nexy.app
```

### 2. Тестирование на чистой системе
```bash
# Создание тестовой виртуальной машины
# Установка PKG пакета
# Проверка работы всех функций
```

## 📋 Чек-лист упаковки

### Подготовка:
- [ ] Настроено окружение разработки
- [ ] Установлены все зависимости
- [ ] Создан Apple Developer Account
- [ ] Получены сертификаты подписания

### Сборка:
- [ ] Создан setup.py
- [ ] Настроен entitlements.plist
- [ ] Собрано приложение с py2app
- [ ] Проверена структура пакета

### Подписание:
- [ ] Подписан основной исполняемый файл
- [ ] Подписаны все библиотеки
- [ ] Проверена подпись кода
- [ ] Настроены entitlements

### Нотаризация:
- [ ] Создан архив для нотаризации
- [ ] Отправлен на нотаризацию
- [ ] Получен тикет нотаризации
- [ ] Прикреплен тикет к приложению

### PKG пакет:
- [ ] Создан Distribution.xml
- [ ] Собран PKG пакет
- [ ] Подписан PKG пакет
- [ ] Проверена подпись пакета

### Тестирование:
- [ ] Протестировано локально
- [ ] Протестировано на чистой системе
- [ ] Проверены все функции
- [ ] Проверены права доступа

## ⚠️ Возможные проблемы

### 1. Ошибки подписания
```bash
# Проблема: "no identity found"
# Решение: Проверить установку сертификатов
security find-identity -v -p codesigning

# Проблема: "entitlements not found"
# Решение: Проверить путь к entitlements.plist
codesign --entitlements ./entitlements.plist --sign "Developer ID Application: Your Name" dist/Nexy.app
```

### 2. Ошибки нотаризации
```bash
# Проблема: "invalid signature"
# Решение: Переподписать приложение
codesign --force --sign "Developer ID Application: Your Name" dist/Nexy.app

# Проблема: "notarization failed"
# Решение: Проверить логи нотаризации
xcrun notarytool log "submission-id" --apple-id "your-email" --password "password" --team-id "TEAM_ID"
```

### 3. Ошибки PKG
```bash
# Проблема: "package verification failed"
# Решение: Проверить подпись пакета
pkgutil --check-signature Nexy-1.0.0.pkg

# Проблема: "installation failed"
# Решение: Проверить права доступа и совместимость
```

## 🚀 Автоматизация

### 1. Скрипт сборки
```bash
#!/bin/bash
# build_and_sign.sh

set -e

echo "🔨 Сборка приложения..."
python setup.py py2app

echo "🔐 Подписание кода..."
codesign --force --verify --verbose --sign "Developer ID Application: Your Name (TEAM_ID)" \
    --entitlements entitlements.plist \
    --options runtime \
    dist/Nexy.app

echo "📦 Создание PKG пакета..."
pkgbuild --root dist/ \
    --identifier com.nexy.app \
    --version 1.0.0 \
    --install-location /Applications \
    --sign "Developer ID Installer: Your Name (TEAM_ID)" \
    Nexy.pkg

echo "✅ Сборка завершена!"
```

### 2. CI/CD интеграция
```yaml
# .github/workflows/build-macos.yml
name: Build macOS App

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    
    - name: Install dependencies
      run: |
        pip install py2app
        pip install -r requirements.txt
    
    - name: Build app
      run: python setup.py py2app
    
    - name: Sign app
      run: |
        codesign --force --sign "Developer ID Application: Your Name" dist/Nexy.app
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v2
      with:
        name: Nexy.app
        path: dist/Nexy.app
```

## 📊 Мониторинг и обновления

### 1. Версионирование
```python
# В setup.py
VERSION = "1.0.0"
BUILD_NUMBER = "100"

# В Info.plist
<key>CFBundleVersion</key>
<string>100</string>
<key>CFBundleShortVersionString</key>
<string>1.0.0</string>
```

### 2. Обновления через Sparkle
```xml
<!-- appcast.xml -->
<rss version="2.0">
  <channel>
    <item>
      <title>Nexy 1.0.1</title>
      <description>Обновление с исправлениями</description>
      <pubDate>Mon, 13 Sep 2025 10:00:00 +0000</pubDate>
      <enclosure url="https://nexy.app/downloads/Nexy-1.0.1.pkg"
                 sparkle:version="101"
                 sparkle:shortVersionString="1.0.1"
                 type="application/octet-stream"/>
    </item>
  </channel>
</rss>
```

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи сборки
2. Убедитесь в корректности сертификатов
3. Проверьте entitlements
4. Обратитесь к документации Apple Developer
5. Проверьте статус нотаризации

---
*Документ создан: 2025-09-13*  
*Версия модуля: 1.0.0*  
*Автор: AI Assistant*
