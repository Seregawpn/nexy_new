# 📦 ПОЛНАЯ ИНСТРУКЦИЯ ПО УПАКОВКЕ И РАЗРЕШЕНИЯМ NEXY AI ASSISTANT

## 🎯 Обзор процесса

**Полный цикл:** Сборка → Подпись → PKG → Нотаризация → DMG → Нотаризация → Настройка разрешений → Готово

**Артефакты:**
- `Nexy-final.app` - подписанное приложение
- `Nexy-signed.pkg` - подписанный и нотарифицированный PKG
- `Nexy.dmg` - нотарифицированный DMG

---

## 🔐 Предварительные требования

### 1. Сертификаты в Keychain
```bash
# Проверка наличия сертификатов
security find-identity -p codesigning -v

# ОБЯЗАТЕЛЬНО должен быть:
# - Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)

# ДЛЯ PKG (опционально):
# - Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)
# Если нет - PKG будет unsigned (только для тестирования)
```

### 2. Notarytool профиль
```bash
# Настройка (если не настроен)
xcrun notarytool store-credentials nexy-notary \
  --apple-id seregawpn@gmail.com \
  --team-id 5NKLL2CLB9 \
  --password "qtiv-kabm-idno-qmbl" \
  --keychain-profile nexy-notary
```

**⚠️ ВАЖНО:** 
- Пароль `qtiv-kabm-idno-qmbl` - это App-Specific Password
- НЕ ваш обычный пароль Apple ID
- Создается в настройках Apple ID: https://appleid.apple.com/account/manage

**📋 Как создать App-Specific Password:**
1. Зайдите на https://appleid.apple.com/account/manage
2. Войдите в свой Apple ID
3. В разделе "Безопасность" найдите "Пароли для приложений"
4. Нажмите "Создать пароль для приложений"
5. Введите название: "Nexy Notarization"
6. Скопируйте сгенерированный пароль
7. Замените `qtiv-kabm-idno-qmbl` на ваш пароль в команде выше

**🔐 БЕЗОПАСНОСТЬ:**
- НЕ коммитьте пароль в Git
- Храните пароль в Keychain или переменных окружения
- Пароль `qtiv-kabm-idno-qmbl` - ВРЕМЕННЫЙ, требует ротации

### 3. Получение Developer ID Installer (опционально)
```bash
# Если нужен подписанный PKG, получите сертификат:
# 1. Зайдите в Apple Developer Portal:
#    https://developer.apple.com/account/resources/certificates/list
# 2. Создайте новый сертификат типа "Developer ID Installer"
# 3. Скачайте .cer файл
# 4. Установите в Keychain:
#    security import certificate.cer -k ~/Library/Keychains/login.keychain
# 5. Проверьте:
#    security find-identity -p codesigning -v | grep -i installer
```

### 4. Архитектура
- **Только Apple Silicon (arm64)**
- **macOS 11.0+**

---

## ✅ ПРОВЕРКА ГОТОВНОСТИ

Перед началом убедитесь, что все готово:

```bash
# 1. Проверка сертификатов
security find-identity -p codesigning -v
# Должен быть: Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)

# 2. Проверка notarytool профиля
xcrun notarytool history --keychain-profile nexy-notary
# Должен показать историю нотаризации

# 3. Проверка архитектуры
uname -m
# Должно быть: arm64

# 4. Проверка скриптов
ls -la packaging/*.sh
# Все скрипты должны быть исполняемыми

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
# Запуск сборки .app + DMG
./packaging/build_app_only.sh
```

**Результат:**
- `dist/Nexy-final.app` - подписанное приложение
- `dist/Nexy.dmg` - DMG для распространения

### Шаг 3: Создание PKG
```bash
# Создание unsigned PKG
./packaging/create_pkg_unsigned.sh

# Если есть Developer ID Installer сертификат:
./packaging/sign_and_notarize_pkg.sh
# Результат: dist/Nexy-signed.pkg (подписанный и нотарифицированный)

# Если НЕТ Installer сертификата:
# Результат: dist/Nexy.pkg (unsigned, только для тестирования)
```

**Результат:**
- `dist/Nexy.pkg` - unsigned PKG (если нет Installer сертификата)
- `dist/Nexy-signed.pkg` - подписанный и нотарифицированный PKG (если есть Installer сертификат)

### Шаг 4: Нотаризация DMG
```bash
# Нотаризация DMG (если не была выполнена)
xcrun notarytool submit dist/Nexy.dmg --keychain-profile nexy-notary --wait

# Степлинг и валидация
xcrun stapler staple dist/Nexy.dmg
xcrun stapler validate dist/Nexy.dmg
```

### Шаг 5: Установка и настройка разрешений
```bash
# Установка приложения
cp -R dist/Nexy-final.app ~/Applications/Nexy.app

# Сброс TCC разрешений
./packaging/reset_permissions.sh

# Запуск приложения
open ~/Applications/Nexy.app
```

---

## 🔧 НАСТРОЙКА РАЗРЕШЕНИЙ

### ✅ Что исправлено в разрешениях

#### 1. Bundle ID унифицирован
- **Единый ID**: `com.nexy.assistant` во всех местах
- **Удалены**: старые `com.nexy.voiceassistant`, `com.sergiyzasorin.nexy.voiceassistant`

#### 2. Добавлены правильные entitlements
```xml
<!-- Разрешения для микрофона и доступности -->
<key>com.apple.security.device.microphone</key>
<true/>
<key>com.apple.security.device.audio-input</key>
<true/>
```

#### 3. Триггеры системных диалогов
- **Accessibility**: `AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True})`
- **Microphone**: `AVCaptureDevice.requestAccessForMediaType_completionHandler_`
- **Screen Recording/Input Monitoring**: автоматическое открытие настроек

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

#### Если иконки не отображаются
- Проверьте, что в `packaging/Nexy.spec` есть:
  ```python
  hiddenimports=[
      'PIL', 'PIL.Image', 'PIL.ImageDraw', 'Pillow',
      # ... остальные импорты
  ]
  ```

### 📋 Быстрые ссылки на настройки
```bash
# Открыть настройки конфиденциальности
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"
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

## 🔧 ДЕТАЛЬНЫЕ КОМАНДЫ

### Сборка приложения
```bash
#!/bin/bash
# packaging/build_app_only.sh

VERSION="1.71.0"
TEAM_ID="5NKLL2CLB9"

# Проверка архитектуры
if [ "$(uname -m)" != "arm64" ]; then
    echo "❌ Требуется Apple Silicon (arm64)"
    exit 1
fi

# Временная директория
BUILD_DIR="/tmp/nexy_app_only_$(date +%s)"
mkdir -p "$BUILD_DIR"
cp -R . "$BUILD_DIR/"
cd "$BUILD_DIR"

# PyInstaller сборка
export PATH="$HOME/Library/Python/3.9/bin:$PATH"
pyinstaller --clean -y packaging/Nexy.spec

# Подпись приложения
APP_IDENTITY="Developer ID Application: Sergiy Zasorin ($TEAM_ID)"
xattr -cr "dist/Nexy.app"
codesign --force --timestamp \
    --options runtime \
    --entitlements packaging/entitlements.plist \
    --sign "$APP_IDENTITY" \
    "dist/Nexy.app"

# Проверка подписи
codesign --verify --strict --deep "dist/Nexy.app"

# Создание DMG
hdiutil create -volname "Nexy AI Assistant" -srcfolder "dist/Nexy.app" \
    -fs HFS+ -format UDRW -size "200m" "dist/Nexy-temp.dmg"

MOUNT_DIR="/Volumes/Nexy AI Assistant"
hdiutil attach "dist/Nexy-temp.dmg" -readwrite -noverify -noautoopen
ln -s /Applications "$MOUNT_DIR/Applications" || true
hdiutil detach "$MOUNT_DIR"

rm -f "dist/Nexy.dmg"
hdiutil convert "dist/Nexy-temp.dmg" -format UDZO -imagekey zlib-level=9 -o "dist/Nexy.dmg"
rm -f "dist/Nexy-temp.dmg"

# Копирование в основную директорию
MAIN_DIR="/Users/sergiyzasorin/Desktop/Development/Nexy/client"
mkdir -p "$MAIN_DIR/dist"
cp "dist/Nexy.dmg" "$MAIN_DIR/dist/"
cp -R "dist/Nexy.app" "$MAIN_DIR/dist/Nexy-final.app"

echo "✅ Сборка завершена: dist/Nexy-final.app, dist/Nexy.dmg"
```

### Создание PKG
```bash
#!/bin/bash
# packaging/create_pkg_unsigned.sh

APP_PATH="dist/Nexy-final.app"
PKG_ROOT="build/payload"
RAW_PKG="dist/Nexy-raw.pkg"
DIST_PKG="dist/Nexy.pkg"

# Подготовка payload
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/usr/local/nexy/resources"
cp -R "$APP_PATH" "$PKG_ROOT/usr/local/nexy/Nexy.app"
cp packaging/LaunchAgent/com.nexy.assistant.plist "$PKG_ROOT/usr/local/nexy/resources/"

# Создание PKG
pkgbuild \
    --root "$PKG_ROOT" \
    --identifier "com.nexy.assistant.pkg" \
    --version "1.71.0" \
    --scripts scripts \
    "$RAW_PKG"

productbuild \
    --distribution packaging/distribution.xml \
    --resources packaging \
    --package-path dist \
    "$DIST_PKG"

echo "✅ PKG создан: $DIST_PKG"
```

### Подпись и нотаризация PKG
```bash
#!/bin/bash
# packaging/sign_and_notarize_pkg.sh

TEAM_ID="5NKLL2CLB9"
PKG_PATH="dist/Nexy.pkg"
SIGNED_PKG_PATH="dist/Nexy-signed.pkg"

# Проверка сертификата
INSTALLER_IDENTITY="Developer ID Installer: Sergiy Zasorin ($TEAM_ID)"

# Подпись PKG
productsign --sign "$INSTALLER_IDENTITY" "$PKG_PATH" "$SIGNED_PKG_PATH"

# Проверка подписи
pkgutil --check-signature "$SIGNED_PKG_PATH"

# Нотаризация PKG
xcrun notarytool submit "$SIGNED_PKG_PATH" \
    --keychain-profile nexy-notary \
    --wait

# Степлинг и валидация
xcrun stapler staple "$SIGNED_PKG_PATH"
xcrun stapler validate "$SIGNED_PKG_PATH"

echo "✅ PKG готов: $SIGNED_PKG_PATH"
```

### Сброс разрешений
```bash
#!/bin/bash
# packaging/reset_permissions.sh

echo "🔄 Сброс TCC разрешений для Nexy AI Assistant"
echo "=============================================="

BUNDLE_ID="com.nexy.assistant"

echo "📋 Сбрасываем разрешения для bundle ID: $BUNDLE_ID"

# Сбрасываем все разрешения
echo "1️⃣ Сброс Microphone..."
tccutil reset Microphone "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "2️⃣ Сброс Screen Recording..."
tccutil reset ScreenCapture "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "3️⃣ Сброс Accessibility..."
tccutil reset Accessibility "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "4️⃣ Сброс Input Monitoring..."
tccutil reset ListenEvent "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo "5️⃣ Сброс Apple Events..."
tccutil reset AppleEvents "$BUNDLE_ID" 2>/dev/null || echo "   (уже сброшено или не было)"

echo ""
echo "✅ TCC разрешения сброшены"
echo ""
echo "📝 Следующие шаги:"
echo "1. Запустите приложение из ~/Applications/Nexy.app"
echo "2. Разрешите доступ к микрофону в системном диалоге"
echo "3. В настройках macOS включите:"
echo "   - Конфиденциальность → Доступность → Nexy"
echo "   - Конфиденциальность → Запись экрана → Nexy"
echo "   - Конфиденциальность → Ввод с клавиатуры → Nexy"
```

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
        'rumps', 'pynput', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'Pillow',
        'mss', 'numpy', 'pydub', 'psutil', 'speech_recognition', 'sounddevice',
        'urllib3', 'aiohttp', 'modules.updater.updater', 'modules.updater.verify',
        'modules.updater.dmg', 'modules.updater.net', 'modules.updater.replace',
        'modules.updater.migrate', 'Quartz', 'AVFoundation', 'CoreAudio',
        'Foundation', 'AppKit', 'Cocoa', 'ApplicationServices', 'SystemConfiguration',
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
        'CFBundleDisplayName': 'Nexy AI Assistant',
        'CFBundleIdentifier': 'com.nexy.assistant',
        'CFBundleVersion': '1.71.0',
        'CFBundleShortVersionString': '1.71.0',
        'CFBundlePackageType': 'APPL',
        'LSMinimumSystemVersion': '11.0',
        'LSUIElement': True,
        'NSMicrophoneUsageDescription': 'Nexy использует микрофон для распознавания речи.',
        'NSAppleEventsUsageDescription': 'Nexy использует Apple Events для интеграции с системой.',
        'CFBundleURLTypes': [{
            'CFBundleURLName': 'com.nexy.assistant.url',
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
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-executable-page-protection</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.cs.allow-dyld-environment-variables</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    <key>com.apple.security.device.microphone</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
</dict>
</plist>
```

### Distribution XML (packaging/distribution.xml)
```xml
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Nexy AI Assistant</title>
    <options customize="never" require-scripts="false"/>
    <choices-outline>
        <line choice="main"/>
    </choices-outline>
    <choice id="main" visible="false">
        <pkg-ref id="com.nexy.assistant.pkg"/>
    </choice>
    <pkg-ref id="com.nexy.assistant.pkg" installKBytes="0" version="1.71.0">Nexy-raw.pkg</pkg-ref>
</installer-gui-script>
```

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

---

## 📊 ИТОГОВЫЕ АРТЕФАКТЫ

После выполнения всех шагов у вас будет:

1. **`dist/Nexy-final.app`** (85MB)
   - Подписанное приложение с Hardened Runtime
   - Готово для установки в ~/Applications

2. **`dist/Nexy-signed.pkg`** (85MB)
   - Подписанный и нотарифицированный PKG
   - Готов для распространения

3. **`dist/Nexy.dmg`** (86MB)
   - Нотарифицированный DMG
   - Готов для автообновлений

---

## 🎯 БЫСТРЫЙ СТАРТ

```bash
# Полный цикл упаковки и настройки разрешений
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
rm -rf dist build /tmp/nexy_* && mkdir -p dist build

# 1. Сборка приложения и DMG
./packaging/build_app_only.sh

# 2. Создание PKG
./packaging/create_pkg_unsigned.sh

# 3. Подпись PKG (только если есть Developer ID Installer)
# ./packaging/sign_and_notarize_pkg.sh

# 4. Нотаризация DMG
xcrun notarytool submit dist/Nexy.dmg --keychain-profile nexy-notary --wait
xcrun stapler staple dist/Nexy.dmg && xcrun stapler validate dist/Nexy.dmg

# 5. Установка и настройка разрешений
cp -R dist/Nexy-final.app ~/Applications/Nexy.app
./packaging/reset_permissions.sh
open ~/Applications/Nexy.app

echo "🎉 Все готово!"
ls -la dist/

# 6. Финальная проверка
echo "📋 Финальная проверка:"
echo "✅ Приложение: $(ls -la dist/Nexy-final.app | wc -l) файлов"
echo "✅ DMG: $(ls -lh dist/Nexy.dmg | awk '{print $5}')"
echo "✅ PKG: $(ls -lh dist/Nexy*.pkg | awk '{print $5}')"
echo ""
echo "🔧 Для установки:"
echo "   cp -R dist/Nexy-final.app ~/Applications/Nexy.app"
echo "   ./packaging/reset_permissions.sh"
echo "   open ~/Applications/Nexy.app"
```

---

## ⚠️ Важные моменты

1. **Не перемещайте приложение** после выдачи разрешений
2. **Bundle ID должен быть одинаковым** во всех местах (`com.nexy.assistant`)
3. **Запускайте только из ~/Applications** для корректной работы TCC
4. **Перезапускайте приложение** после изменения разрешений
5. **Используйте только эту инструкцию** - все остальные удалены как дублирующие

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