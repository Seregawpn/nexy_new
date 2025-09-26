# 📦 ПОЛНОЕ РУКОВОДСТВО ПО УПАКОВКЕ NEXY AI ASSISTANT

## 🎯 Обзор процесса

**Полный цикл:** Сборка → Подпись → PKG → Нотаризация → Установка → Готово

**Артефакты:**
- `Nexy-final.app` - подписанное и нотарифицированное приложение
- `Nexy-signed.pkg` - подписанный и нотарифицированный PKG
- `Nexy.dmg` - нотарифицированный DMG (опционально)

---

## 🔐 Предварительные требования

### 1. Сертификаты в Keychain
```bash
# Проверка наличия сертификатов
security find-identity -p codesigning -v

# ОБЯЗАТЕЛЬНО должен быть:
# - Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)
# - Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)
```

### 2. App-Specific Password
```bash
# Настройка notarytool профиля
xcrun notarytool store-credentials nexy-notary \
  --apple-id sergiy.zasorin@gmail.com \
  --team-id 5NKLL2CLB9 \
  --password "qtiv-kabm-idno-qmbl" \
  --keychain-profile nexy-notary
```

**⚠️ ВАЖНО:** 
- Пароль `qtiv-kabm-idno-qmbl` - это App-Specific Password
- НЕ ваш обычный пароль Apple ID
- Создается в настройках Apple ID: https://appleid.apple.com/account/manage

### 3. Системные требования
- **Архитектура:** Apple Silicon (arm64) только
- **macOS:** 11.0+ (Big Sur и новее)
- **Python:** 3.9+
- **PyInstaller:** 6.15.0+

---

## ✅ ПРОВЕРКА ГОТОВНОСТИ

Перед началом убедитесь, что все готово:

```bash
# 1. Проверка сертификатов
security find-identity -p codesigning -v
# Должны быть: Developer ID Application и Developer ID Installer

# 2. Проверка notarytool профиля
xcrun notarytool history --keychain-profile nexy-notary
# Должен показать историю нотаризации

# 3. Проверка архитектуры
uname -m
# Должно быть: arm64

# 4. Проверка зависимостей
pip install -r requirements.txt
pip install grpcio grpcio-tools

# 5. Проверка директории проекта
pwd
# Должно быть: /Users/sergiyzasorin/Desktop/Development/Nexy/client
```

---

## 🚀 ПОШАГОВАЯ ИНСТРУКЦИЯ

### Шаг 1: Очистка и подготовка
```bash
# Очистка старых артефактов
rm -rf dist build /tmp/nexy_*
mkdir -p dist build

# Переход в директорию проекта
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
```

### Шаг 2: Сборка приложения
```bash
# Запуск полной сборки с подписанием и нотаризацией
cd packaging
./build_final.sh
```

**Результат:**
- `dist/Nexy-final.app` - подписанное и нотарифицированное приложение
- `dist/Nexy-signed.pkg` - подписанный и нотарифицированный PKG

### Шаг 3: Установка и тестирование
```bash
# Установка PKG (автоматически установит в ~/Applications)
open dist/Nexy-signed.pkg

# Или ручная установка приложения
cp -R dist/Nexy-final.app ~/Applications/Nexy.app

# Запуск приложения
open ~/Applications/Nexy.app
```

---

## 🔧 КЛЮЧЕВЫЕ ИСПРАВЛЕНИЯ

### ✅ Проблемы, которые мы исправили:

#### 1. **Путь установки PKG**
- ❌ **Было:** `~/Applications` (не работает с pkgbuild)
- ✅ **Стало:** `/Users/$(whoami)/Applications` (работает корректно)

#### 2. **Extended Attributes**
- ❌ **Проблема:** `com.apple.FinderInfo` блокирует подпись
- ✅ **Решение:** Очистка через `xattr -cr` и `ditto --rsrc --noextattr`

#### 3. **TCC Разрешения**
- ❌ **Проблема:** Множественные запросы разрешений
- ✅ **Решение:** Централизованный запрос через `PermissionsIntegration`

#### 4. **Audio Conversion**
- ❌ **Проблема:** Двойная конвертация аудио
- ✅ **Решение:** Убрана избыточная конвертация в `welcome_message_integration.py`

#### 5. **PyInstaller Imports**
- ❌ **Проблема:** Неправильные пути импорта модулей
- ✅ **Решение:** Исправлены пути для `rumps`, `grpc`, `AppKit`

---

## 📋 КОНФИГУРАЦИОННЫЕ ФАЙЛЫ

### PyInstaller Spec (packaging/Nexy.spec)
```python
# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import os

client_dir = Path(os.getcwd())
assets_dir = client_dir / "assets"
config_dir = client_dir / "config"
resources_dir = client_dir / "resources"

a = Analysis(
    [str(client_dir / 'main.py')],
    pathex=[str(client_dir), str(client_dir / 'integration')],
    binaries=[],
    datas=[
        (str(config_dir), 'config'),
        (str(assets_dir / 'icons'), 'assets/icons'),
        (str(resources_dir), 'resources'),
    ],
    hiddenimports=[
        # Основные модули
        'pynput', 'pynput.keyboard', 'pynput.mouse', 'mss', 'numpy', 'pydub', 'psutil',
        # PIL модули (правильные имена)
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageTk', 'PIL.ImageFont',
        # Аудио
        'speech_recognition', 'speech_recognition.recognizers', 'speech_recognition.recognizers.google', 'sounddevice',
        # Сеть
        'urllib3', 'aiohttp', 'grpc', 'grpc_tools',
        # PyObjC фреймворки (ПРАВИЛЬНЫЙ ПОРЯДОК для dlsym)
        'objc', 'PyObjCTools', 'PyObjCTools.AppHelper',
        'Foundation', 'CoreFoundation', 'AppKit', 'Cocoa',
        'Quartz', 'AVFoundation', 'CoreAudio', 'ApplicationServices', 'SystemConfiguration',
        # AppKit подмодули для NSMakeRect (правильный синтаксис)
        'AppKit',
        # rumps модули (правильные пути)
        'rumps', 'rumps._internal', 'rumps.events', 'rumps.utils', 'rumps.compat',
        # Уведомления
        'UserNotifications',
    ],
    excludes=['tkinter', 'matplotlib', 'pandas'],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name='Nexy',
    debug=False,
    upx=False,
    console=False,
    argv_emulation=False,
    target_arch=None,
    icon=str(assets_dir / 'icons' / 'app.icns'),
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='Nexy.app',
    icon=str(assets_dir / 'icons' / 'app.icns'),
    bundle_identifier='com.nexy.assistant',
    info_plist={
        'CFBundleName': 'Nexy',
        'CFBundleDisplayName': 'Nexy',
        'CFBundleIdentifier': 'com.nexy.assistant',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': '11.0',
        'LSUIElement': True,  # только меню-бар, без Dock
        # Usage Descriptions
        'NSMicrophoneUsageDescription': 'Nexy использует микрофон для распознавания речи.',
        'NSScreenCaptureUsageDescription': 'Nexy использует захват экрана для анализа контекста и обработки голосовых команд.',
        'NSAppleEventsUsageDescription': 'Nexy использует Apple Events для интеграции с системой.',
        'NSUserNotificationsUsageDescription': 'Nexy отправляет уведомления о статусе и событиях.',
        'NSInputMonitoringUsageDescription': 'Nexy использует мониторинг ввода для Push-to-Talk по пробелу.',
        # URL Scheme
        'CFBundleURLTypes': [{
            'CFBundleURLName': 'com.nexy.assistant',
            'CFBundleURLSchemes': ['nexy'],
        }],
        'LSApplicationCategoryType': 'public.app-category.productivity',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
    },
)
```

### Entitlements (packaging/entitlements.plist)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
 "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <!-- Вне App Store: sandbox выключен -->
  <key>com.apple.security.app-sandbox</key><false/>
  <!-- Нужен, если посылаете Apple Events -->
  <key>com.apple.security.automation.apple-events</key><true/>
  <!-- Доступ к микрофону -->
  <key>com.apple.security.device.microphone</key><true/>
  <!-- Доступ к аудио входу (требуется для Hardened Runtime) -->
  <key>com.apple.security.device.audio-input</key><true/>
  <!-- Доступ к камере -->
  <key>com.apple.security.device.camera</key><true/>
  <!-- Screen Recording (НЕ имеет отдельного entitlement, но нужны разрешения) -->
  <!-- Отключаем Library Validation для PyInstaller onefile -->
  <key>com.apple.security.cs.disable-library-validation</key><true/>
  <!-- Network для gRPC -->
  <key>com.apple.security.network.client</key><true/>
  <!-- Доступ к файловой системе -->
  <key>com.apple.security.files.user-selected.read-write</key><true/>
  <key>com.apple.security.files.downloads.read-write</key><true/>
  <!-- Дополнительные разрешения для TCC -->
  <key>com.apple.security.cs.allow-jit</key><true/>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
  <key>com.apple.security.cs.allow-dyld-environment-variables</key><true/>
</dict>
</plist>
```

### Distribution XML (packaging/distribution.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Nexy</title>
    <options customize="never" require-scripts="false"/>
    <!-- Разрешаем установку в профиль пользователя (без запроса пароля).
         Для этого компонентный PKG должен быть собран с install-location "/Users/$(whoami)/Applications". -->
    <domains enable_localSystem="false" enable_currentUserHome="true"/>
    <choices-outline>
        <line choice="main"/>
    </choices-outline>
    <choice id="main" visible="false">
        <pkg-ref id="com.nexy.assistant.pkg"/>
    </choice>
    <!-- id и version должны совпадать с параметрами pkgbuild -->
    <pkg-ref id="com.nexy.assistant.pkg" version="1.0.0">Nexy-raw.pkg</pkg-ref>
</installer-gui-script>
```

### Build Script (packaging/build_final.sh) - Ключевые настройки
```bash
# Правильный путь установки (КРИТИЧНО!)
INSTALL_LOCATION="/Users/$(whoami)/Applications"

# Создание PKG
pkgbuild --root /tmp/nexy_pkg_clean_final \
    --identifier "com.nexy.assistant" \
    --version "1.0.0" \
    --install-location "$INSTALL_LOCATION" \
    "$DIST_DIR/$APP_NAME-raw.pkg"
```

---

## 🔧 НАСТРОЙКА РАЗРЕШЕНИЙ

### ✅ Что исправлено в разрешениях

#### 1. Bundle ID унифицирован
- **Единый ID**: `com.nexy.assistant` во всех местах
- **Удалены**: старые `com.nexy.voiceassistant`, `com.sergiyzasorin.nexy.voiceassistant`

#### 2. Централизованный запрос разрешений
- **Проблема**: Множественные TCC запросы замедляли запуск
- **Решение**: `PermissionsIntegration` запрашивает все разрешения централизованно

#### 3. Правильные entitlements
```xml
<!-- Разрешения для микрофона и доступности -->
<key>com.apple.security.device.microphone</key><true/>
<key>com.apple.security.device.audio-input</key><true/>
<key>com.apple.security.device.camera</key><true/>
```

#### 4. Info.plist Usage Descriptions
```xml
<key>NSMicrophoneUsageDescription</key>
<string>Nexy использует микрофон для распознавания речи.</string>
<key>NSScreenCaptureUsageDescription</key>
<string>Nexy использует захват экрана для анализа контекста и обработки голосовых команд.</string>
```

### 🚀 Настройка разрешений при первом запуске

**При первом запуске приложения:**
1. **Microphone** - появится системный диалог → нажмите "Разрешить"
2. **Accessibility** - появится системный диалог → нажмите "Разрешить"
3. **Screen Recording** - откроются настройки → включите Nexy
4. **Input Monitoring** - откроются настройки → включите Nexy

### 🔍 Диагностика проблем с разрешениями

#### Если приложение не запускается
```bash
# Проверяем подпись
codesign --verify --strict --deep ~/Applications/Nexy.app

# Проверяем Gatekeeper
spctl --assess --type exec ~/Applications/Nexy.app
```

#### Если разрешения не работают
```bash
# Сбрасываем все разрешения
./packaging/reset_permissions.sh

# Проверяем статус разрешений
tccutil reset Microphone com.nexy.assistant
tccutil reset ScreenCapture com.nexy.assistant
tccutil reset Accessibility com.nexy.assistant
tccutil reset ListenEvent com.nexy.assistant
```

---

## 🎯 ОЖИДАЕМОЕ ПОВЕДЕНИЕ ПРИЛОЖЕНИЯ

### SLEEPING режим (серый кружок)
- Микрофон выключен
- Фоновые проверки обновлений
- Ожидание пользовательского ввода

### LISTENING режим (синий пульсирующий)
- **Триггер**: долгое нажатие пробела (500-700мс)
- Микрофон активен
- Распознавание речи
- Обновления приостановлены

### PROCESSING режим (желтый вращающийся)
- **Триггер**: отпускание пробела после LISTENING
- Отправка данных на сервер
- Воспроизведение ответа
- Обновления приостановлены

---

## 🔍 ПРОВЕРКИ КАЧЕСТВА

### Проверка подписи приложения
```bash
codesign --verify --strict --deep dist/Nexy-final.app
spctl --assess --type exec dist/Nexy-final.app
```

### Проверка подписи PKG
```bash
pkgutil --check-signature dist/Nexy-signed.pkg
spctl --assess --type install dist/Nexy-signed.pkg
```

### Проверка нотаризации
```bash
xcrun stapler validate dist/Nexy-signed.pkg
xcrun stapler validate dist/Nexy.dmg
```

---

## 🚨 УСТРАНЕНИЕ ПРОБЛЕМ

### Ошибка "Library Validation failed"
- **Причина:** Hardened Runtime конфликт с PyInstaller
- **Решение:** Убедитесь, что в entitlements.plist есть `com.apple.security.cs.disable-library-validation`

### Ошибка "resource fork, Finder information, or similar detritus not allowed"
- **Причина:** Атрибуты macOS в файлах
- **Решение:** `xattr -cr dist/Nexy.app` перед подписью

### Ошибка "The executable does not have the hardened runtime enabled"
- **Причина:** Отсутствует `--options runtime` в codesign
- **Решение:** Добавьте `--options runtime` в команду codesign

### Ошибка "No module named 'simple_module_coordinator'"
- **Причина:** Неправильный pathex в .spec
- **Решение:** Добавьте `str(client_dir / 'integration')` в pathex

### Проблемы с разрешениями
- **Причина:** Неправильный bundle ID или перемещение приложения
- **Решение:** 
  1. Убедитесь, что bundle ID везде `com.nexy.assistant`
  2. Не перемещайте приложение после выдачи разрешений
  3. Запускайте только из `~/Applications`
  4. Сбросьте разрешения: `./packaging/reset_permissions.sh`

### Ошибка "dlsym cannot find symbol NSMakeRect"
- **Причина:** Неправильные импорты AppKit в PyInstaller
- **Решение:** Добавьте `'AppKit'` в hiddenimports (не подмодули)

### Ошибка "ModuleNotFoundError: No module named 'grpcio'"
- **Причина:** Отсутствуют gRPC модули
- **Решение:** `pip install grpcio grpcio-tools`

### Ошибка "The file 'scripts' couldn't be opened"
- **Причина:** Неправильный путь к scripts в pkgbuild
- **Решение:** Уберите `--scripts` из pkgbuild или используйте абсолютный путь

---

## 📊 ИТОГОВЫЕ АРТЕФАКТЫ

После выполнения всех шагов у вас будет:

1. **`dist/Nexy-final.app`** (~107MB)
   - Подписанное и нотарифицированное приложение
   - Готово для установки в ~/Applications

2. **`dist/Nexy-signed.pkg`** (~107MB)
   - Подписанный и нотарифицированный PKG
   - Готов для распространения

3. **`dist/Nexy.dmg`** (~108MB) (опционально)
   - Нотарифицированный DMG
   - Готов для автообновлений

---

## 🎯 БЫСТРЫЙ СТАРТ

```bash
# Полный цикл упаковки
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
rm -rf dist build /tmp/nexy_* && mkdir -p dist build

# 1. Сборка приложения с подписанием и нотаризацией
cd packaging
./build_final.sh

# 2. Установка PKG
open dist/Nexy-signed.pkg

# 3. Запуск приложения
open ~/Applications/Nexy.app

echo "🎉 Все готово!"
ls -la dist/

# 4. Финальная проверка
echo "📋 Финальная проверка:"
echo "✅ Приложение: $(ls -la dist/Nexy-final.app | wc -l) файлов"
echo "✅ PKG: $(ls -lh dist/Nexy-signed.pkg | awk '{print $5}')"
echo ""
echo "🔧 Приложение установлено в: ~/Applications/Nexy.app"
```

---

## ⚠️ Важные моменты

1. **Не перемещайте приложение** после выдачи разрешений
2. **Bundle ID должен быть одинаковым** во всех местах (`com.nexy.assistant`)
3. **Запускайте только из ~/Applications** для корректной работы TCC
4. **Перезапускайте приложение** после изменения разрешений
5. **Используйте только эту инструкцию** - все исправления включены

---

## 📞 Поддержка

При проблемах проверьте:
1. Сертификаты в Keychain: `security find-identity -p codesigning -v`
2. Notarytool профиль: `xcrun notarytool history --keychain-profile nexy-notary`
3. Логи сборки в `/tmp/nexy_*`
4. Статус нотаризации: `xcrun notarytool history --keychain-profile nexy-notary`
5. Логи приложения: `~/Library/Logs/Nexy.out.log`

**Время выполнения:** ~10-15 минут (включая нотаризацию)
**Архитектура:** Apple Silicon (arm64) только
**macOS:** 11.0+ (Big Sur и новее)

---

## 📋 ЧЕКЛИСТ ПЕРЕД УПАКОВКОЙ

### ✅ Предварительные требования:
- [ ] Все зависимости установлены (`pip install -r requirements.txt`)
- [ ] gRPC модули установлены (`pip install grpcio grpcio-tools`)
- [ ] Сертификаты в Keychain (`security find-identity -p codesigning -v`)
- [ ] App-Specific Password настроен (`xcrun notarytool history --keychain-profile nexy-notary`)
- [ ] Архитектура arm64 (`uname -m`)

### ✅ После упаковки:
- [ ] PKG создан без ошибок (`ls -la dist/*.pkg`)
- [ ] Приложение подписано (`codesign --verify dist/Nexy-final.app`)
- [ ] PKG подписан (`pkgutil --check-signature dist/Nexy-signed.pkg`)
- [ ] Нотаризация прошла успешно (`xcrun stapler validate dist/Nexy-signed.pkg`)
- [ ] Установка работает в `~/Applications/Nexy.app`

---

## 🔄 ОБНОВЛЕНИЯ И ВЕРСИОНИРОВАНИЕ

### Изменение версии
1. Обновите версию в `packaging/Nexy.spec`:
   ```python
   'CFBundleVersion': '1.0.1',
   'CFBundleShortVersionString': '1.0.1',
   ```

2. Обновите версию в `packaging/build_final.sh`:
   ```bash
   VERSION="1.0.1"
   ```

3. Обновите версию в `packaging/distribution.xml`:
   ```xml
   <pkg-ref id="com.nexy.assistant.pkg" version="1.0.1">Nexy-raw.pkg</pkg-ref>
   ```

### Автоматические обновления
- DMG используется для автообновлений через Sparkle
- PKG используется для первичной установки
- Приложение проверяет обновления в фоновом режиме

---

**Это полное руководство покрывает все аспекты упаковки, подписания и нотаризации приложения Nexy AI Assistant!** 🎉
