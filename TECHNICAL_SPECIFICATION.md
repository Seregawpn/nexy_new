# 🔧 ТЕХНИЧЕСКАЯ СПЕЦИФИКАЦИЯ УПАКОВКИ NEXY

## 📋 АРХИТЕКТУРА СИСТЕМЫ

### Компоненты упаковки
```
client/
├── nexy.spec                 # PyInstaller конфигурация
├── entitlements.plist        # macOS entitlements
├── notarize_config.sh        # Настройки нотаризации
├── build_complete.sh         # Основной скрипт сборки
├── create_pkg.sh            # Создание PKG
├── notarize.sh              # Нотаризация
├── verify_packaging.sh      # Проверка готовности
├── sign_sparkle.sh          # Подпись Sparkle Framework
└── rebuild_and_notarize.sh  # Полная автоматизация
```

### Структура PKG
```
Nexy_AI_Voice_Assistant_v1.71.0.pkg
├── Applications/
│   └── Nexy.app/            # Основное приложение
│       ├── Contents/
│       │   ├── MacOS/Nexy   # Исполняемый файл
│       │   ├── Resources/   # Ресурсы и конфигурация
│       │   ├── Frameworks/  # Системные фреймворки
│       │   └── Info.plist   # Метаданные приложения
└── Library/
    └── LaunchAgents/        # Автозапуск
        ├── com.sergiyzasorin.nexy.voiceassistant.plist
        └── nexy_launcher.sh
```

## 🔐 СИСТЕМА ПОДПИСАНИЯ

### Сертификаты
- **Developer ID Application:** Подпись .app bundle
- **Developer ID Installer:** Подпись PKG файла

### Entitlements
```xml
<!-- Критические разрешения -->
com.apple.security.device.audio-input
com.apple.security.device.camera
com.apple.security.files.user-selected.read-write
com.apple.security.automation.apple-events

<!-- Сетевые разрешения -->
com.apple.security.network.client
com.apple.security.network.server

<!-- JIT и выполнение кода -->
com.apple.security.cs.allow-jit
com.apple.security.cs.allow-unsigned-executable-memory
com.apple.security.cs.allow-dyld-environment-variables
com.apple.security.cs.disable-library-validation

<!-- Дополнительные разрешения -->
com.apple.security.device.bluetooth
com.apple.security.device.usb
```

### TCC разрешения
```xml
<!-- Info.plist -->
NSMicrophoneUsageDescription
NSCameraUsageDescription
NSScreenCaptureUsageDescription
NSAppleEventsUsageDescription
```

## 📦 PYINSTALLER КОНФИГУРАЦИЯ

### Основные параметры
```python
# Режим сборки
console=False          # GUI приложение
windowed=True          # Без консоли

# Архитектура
target_arch='arm64'    # Apple Silicon

# Подпись
codesign_identity=None # Подписывается отдельно
entitlements_file=None # Используется отдельно
```

### Скрытые импорты
```python
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
]
```

### Данные для включения
```python
datas=[
    # Иконки и ресурсы
    ('assets/icons/app.icns', 'assets/icons/'),
    ('assets/icons/active.png', 'assets/icons/'),
    ('assets/icons/active@2x.png', 'assets/icons/'),
    ('assets/icons/off.png', 'assets/icons/'),
    ('assets/icons/off@2x.png', 'assets/icons/'),
    ('assets/logo.icns', 'assets/'),
    
    # Конфигурация
    ('config/app_config.yaml', 'config/'),
    ('config/logging_config.yaml', 'config/'),
    
    # LaunchAgent файлы
    ('pkg_root/Library/LaunchAgents/com.sergiyzasorin.nexy.voiceassistant.plist', 'Resources/'),
    ('pkg_root/Library/LaunchAgents/nexy_launcher.sh', 'Resources/'),
    
    # Entitlements
    ('entitlements.plist', '.'),
]
```

## 🔄 ПРОЦЕСС АВТОМАТИЗАЦИИ

### Этапы сборки
1. **Предварительная проверка** - `verify_packaging.sh`
2. **Установка зависимостей** - Homebrew + pip
3. **Сборка приложения** - PyInstaller
4. **Подпись Sparkle** - `sign_sparkle.sh`
5. **Создание PKG** - `create_pkg.sh`
6. **Нотаризация** - `notarize.sh`
7. **Финальная проверка** - Валидация

### Обработка ошибок
```bash
# Проверка успешности каждой операции
if command; then
    echo "✅ Операция успешна"
else
    echo "❌ Ошибка операции"
    exit 1
fi
```

## 🧪 СИСТЕМА ТЕСТИРОВАНИЯ

### Проверки подписи
```bash
# Проверка .app bundle
codesign --verify --verbose dist/Nexy.app

# Проверка PKG
pkgutil --check-signature Nexy_AI_Voice_Assistant_v1.71.0.pkg
```

### Проверки нотаризации
```bash
# Проверка тикета
xcrun stapler validate Nexy_AI_Voice_Assistant_v1.71.0.pkg

# Проверка Gatekeeper
spctl --assess --verbose Nexy_AI_Voice_Assistant_v1.71.0.pkg
```

### Функциональное тестирование
```bash
# Установка
sudo installer -pkg Nexy_AI_Voice_Assistant_v1.71.0.pkg -target /

# Запуск
open /Applications/Nexy.app

# Проверка автозапуска
launchctl list | grep nexy
```

## 🔧 КОНФИГУРАЦИЯ НОТАРИЗАЦИИ

### Параметры Apple Notary Service
```bash
# Отправка на нотаризацию
xcrun notarytool submit "$PKG_NAME" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

# Прикрепление тикета
xcrun stapler staple "$PKG_NAME"
```

### Требования к файлу
- Размер: < 500MB
- Формат: PKG, DMG, ZIP
- Подпись: Developer ID
- Архитектура: arm64, x86_64

## 📊 МОНИТОРИНГ И ЛОГИРОВАНИЕ

### Логи сборки
```bash
# PyInstaller логи
build/nexy/warn-nexy.txt

# Логи подписания
codesign --verify --verbose 2>&1

# Логи нотаризации
xcrun notarytool history --apple-id "$APPLE_ID"
```

### Метрики производительности
- **Время сборки:** ~5-10 минут
- **Время нотаризации:** ~10-15 минут
- **Размер PKG:** ~59MB
- **Размер .app:** ~200MB

## 🔄 СИСТЕМА ОБНОВЛЕНИЙ

### Sparkle Framework
```xml
<!-- Info.plist -->
<key>SUFeedURL</key>
<string>http://localhost:8080/appcast.xml</string>
<key>SUPublicEDKey</key>
<string>yixFT+HhjLehYH6sT8riFb1etq/hpXFWNqiGkZOBHjE=</string>
<key>SUEnableAutomaticChecks</key>
<true/>
<key>SUAllowsAutomaticUpdates</key>
<true/>
<key>SUAutomaticallyUpdate</key>
<true/>
```

### AppCast XML
```xml
<item>
    <title>Nexy 1.71.0</title>
    <description>Описание обновления</description>
    <pubDate>Mon, 07 Sep 2025 18:00:00 +0000</pubDate>
    <enclosure url="http://localhost:8080/downloads/Nexy_AI_Voice_Assistant_v1.71.0.pkg"
               sparkle:version="1.71.0"
               sparkle:shortVersionString="1.71.0"
               length="61439100"
               type="application/octet-stream"
               sparkle:edSignature="qNdO8cusUEca5OBgPtW1Vh5Xqi7OOR2UITqbFWcD4oNZC/lG26twpCxM6He0tyZh3/+NF9G/L3T3g2h+O4rWAw=="/>
</item>
```

## 🛠️ УСТРАНЕНИЕ НЕПОЛАДОК

### Диагностические команды
```bash
# Проверка сертификатов
security find-identity -v -p codesigning

# Проверка подписи
codesign --verify --verbose --deep dist/Nexy.app

# Проверка атрибутов
xattr -l dist/Nexy.app

# Очистка атрибутов
xattr -cr dist/Nexy.app

# Проверка зависимостей
otool -L dist/Nexy.app/Contents/MacOS/Nexy
```

### Частые проблемы и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| `Disallowed xattr` | Finder атрибуты | `xattr -cr file.app` |
| `Invalid credentials` | Неверный Apple ID | Проверить `notarize_config.sh` |
| `Module not found` | Отсутствует зависимость | `pip3 install module` |
| `Code signing failed` | Проблемы с сертификатом | Проверить Keychain |

## 📈 ОПТИМИЗАЦИЯ

### Размер PKG
- Исключение ненужных модулей
- Сжатие ресурсов
- Оптимизация зависимостей

### Скорость сборки
- Кэширование PyInstaller
- Параллельная обработка
- Инкрементальная сборка

### Качество подписи
- Валидация на каждом этапе
- Автоматические проверки
- Детальное логирование

---

**📖 Полная документация:** `COMPLETE_PACKAGING_GUIDE.md`
**⚡ Быстрый старт:** `QUICK_PACKAGING_CHECKLIST.md`

