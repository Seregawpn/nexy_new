# 📦 План упаковки Nexy (macOS PKG) — шаблон повторяемого процесса

Дата: 20 сентября 2025
Статус: ✅ ГОТОВ К ПРИМЕНЕНИЮ (все модули добавлены, дублирование устранено)

Цель: «Кнопочный» процесс сборки подписанного и нотарифицированного PKG с новой HTTP-системой обновлений, который можно быстро повторять на каждой версии.

---

## 0) Предпосылки и переменные окружения

Требуется:
- Xcode Command Line Tools: `xcode-select --install`
- Доступ к Apple Developer (Developer ID Application/Installer)
- Python 3.11+ с зависимостями: `urllib3`, `pynacl`, `packaging`
- **Архитектура:** Только Apple Silicon (M1+) - Intel Mac не поддерживается

Хранение секретов (рекомендуемые переменные):
- `DEVELOPER_ID_APP="Developer ID Application: YOUR NAME (TEAMID)"`
- `DEVELOPER_ID_INSTALLER="Developer ID Installer: YOUR NAME (TEAMID)"`
- `TEAM_ID="5NKLL2CLB9"` (пример)
- `BUNDLE_ID="com.nexy.assistant"`
- `APP_NAME="Nexy"`
- `APP_VERSION="2.5.0"` / `APP_BUILD="20500"` (CFBundleVersion)
- `UPDATE_MANIFEST_URL="https://api.yourdomain.com/updates/manifest.json"`
- `APPLE_NOTARY_PROFILE="NexyNotary"` (сохранённый профиль notarytool)

Создать профиль notarytool (однократно):
```
xcrun notarytool store-credentials "$APPLE_NOTARY_PROFILE" \
  --apple-id "APPLE_ID_EMAIL" \
  --team-id "$TEAM_ID" \
  --password "APP_SPECIFIC_PASSWORD"
```

---

## 1) Staging Pipeline (Новый подход)

**Проблема:** PyInstaller создает .app bundle в `dist/` директории, которая может содержать проблемные xattrs (FinderInfo, quarantine), блокирующие codesigning.

**Решение:** Staging pipeline - сборка и подпись в чистой временной директории, затем перенос в `dist/`.

### 1.1 Команды staging pipeline:

```bash
# Полный пайплайн (рекомендуется)
make all

# Или по шагам:
make sanitize-dist      # Очистка dist/ директории
make setup-staging      # Создание staging директории
make app               # Сборка PyInstaller + копирование в staging
make restage-app-root  # Очистка xattrs через ditto
make sign-nested       # Подпись всех вложений
make sign-app          # Подпись основного .app bundle
make stage-to-dist     # Перенос подписанного .app в dist/
make pkg               # Создание PKG
make dmg               # Создание DMG
make notarize-app      # Нотарификация .app
make notarize-pkg      # Нотарификация PKG
make notarize-dmg      # Нотарификация DMG
make staple-all        # Stapling всех артефактов
make verify            # Проверка подписей
```

### 1.2 Ключевые принципы:

- **Staging директория:** `/tmp/nexy-stage` (чистая среда)
- **Очистка xattrs:** `xattr -cr` перед подписью и переносом
- **Чистый перенос:** `ditto --norsrc --noqtn` без xattrs
- **Проверка на каждом этапе:** `codesign --verify --deep --strict`

### 1.3 Переменные окружения:

```bash
export DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
export APPLE_NOTARY_PROFILE="NexyNotary"
```

---

## 2) ПОЛНОЕ РУКОВОДСТВО ПО ПОДПИСИ ПРИЛОЖЕНИЙ

### 2.1 Что такое codesigning и зачем он нужен?

**Codesigning** — это процесс цифровой подписи приложения для macOS, который:
- **Подтверждает авторство** — пользователи знают, кто создал приложение
- **Обеспечивает целостность** — гарантирует, что приложение не было изменено
- **Разрешает запуск** — macOS позволяет запускать подписанные приложения
- **Требуется для распространения** — без подписи приложение заблокируется Gatekeeper

### 2.2 Типы сертификатов для подписи

#### **Developer ID Application** (для распространения вне Mac App Store)
```bash
DEVELOPER_ID_APP="Developer ID Application: YOUR NAME (TEAM_ID)"
```
- **Назначение:** Подпись приложений для распространения на сайте/по email
- **Где получить:** Apple Developer Portal → Certificates → Developer ID Application
- **Срок действия:** 3 года
- **Требуется для:** .app, .pkg, .dmg файлов

#### **Developer ID Installer** (для PKG инсталляторов)
```bash
DEVELOPER_ID_INSTALLER="Developer ID Installer: YOUR NAME (TEAM_ID)"
```
- **Назначение:** Подпись PKG инсталляторов
- **Где получить:** Apple Developer Portal → Certificates → Developer ID Installer
- **Срок действия:** 3 года
- **Требуется для:** .pkg файлов

### 2.3 Подготовка к подписи

#### **Шаг 1: Установка Xcode Command Line Tools**
```bash
xcode-select --install
```

#### **Шаг 2: Получение сертификатов**
1. Войдите в [Apple Developer Portal](https://developer.apple.com)
2. Перейдите в **Certificates, Identifiers & Profiles**
3. Создайте сертификаты:
   - **Developer ID Application** (для .app файлов)
   - **Developer ID Installer** (для .pkg файлов)
4. Скачайте и установите сертификаты в Keychain

#### **Шаг 3: Создание App-Specific Password**
1. Перейдите в [Apple ID Settings](https://appleid.apple.com)
2. В разделе **Security** создайте **App-Specific Password**
3. Сохраните пароль для notarytool

#### **Шаг 4: Настройка notarytool профиля**
```bash
xcrun notarytool store-credentials "NexyNotary" \
  --apple-id "your-apple-id@example.com" \
  --team-id "5NKLL2CLB9" \
  --password "your-app-specific-password"
```

### 2.4 Структура entitlements.plist

**Обязательные entitlements для Nexy:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Отключение App Sandbox (для Developer ID) -->
    <key>com.apple.security.app-sandbox</key>
    <false/>
    
    <!-- Отключение библиотечной валидации -->
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    
    <!-- Доступность (для управления другими приложениями) -->
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    
    <!-- Микрофон -->
    <key>com.apple.security.device.microphone</key>
    <true/>
    
    <!-- Камера (если требуется) -->
    <key>com.apple.security.device.camera</key>
    <true/>
    
    <!-- Сетевые соединения -->
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    
    <!-- Файловая система -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
</dict>
</plist>
```

### 2.5 Процесс подписи (пошагово)

#### **Этап 1: Подготовка окружения**
```bash
# Настройка переменных окружения
export DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
export APPLE_NOTARY_PROFILE="NexyNotary"

# Или используйте готовый скрипт
source packaging/setup_env.sh
```

#### **Этап 2: Сборка приложения**
```bash
# Сборка PyInstaller
make app

# Очистка staging директории
make sanitize-dist setup-staging
```

#### **Этап 3: Подпись всех компонентов**
```bash
# 1. Очистка xattrs
make restage-app-root

# 2. Подпись всех вложений (библиотеки, исполняемые файлы)
make sign-nested

# 3. Подпись основного .app bundle
make sign-app

# 4. Перенос в dist/
make stage-to-dist
```

#### **Этап 4: Создание PKG/DMG**
```bash
# Создание PKG инсталлятора
make pkg

# Создание DMG образа
make dmg
```

#### **Этап 5: Нотаризация**
```bash
# Нотаризация всех артефактов
make notarize-app
make notarize-pkg
make notarize-dmg

# Stapling (прикрепление билета нотаризации)
make staple-all
```

#### **Этап 6: Проверка**
```bash
# Проверка подписей
make verify

# Детальная проверка
codesign --verify --deep --strict --verbose=2 dist/Nexy.app
spctl --assess --type execute --verbose dist/Nexy.app
```

### 2.6 Типичные ошибки и их решения

#### **Ошибка: "resource fork, Finder information, or similar detritus not allowed"**
```bash
# Решение: очистка xattrs
xattr -cr dist/Nexy.app
xattr -dr com.apple.FinderInfo dist/Nexy.app
```

#### **Ошибка: "unsealed contents present in the bundle root"**
```bash
# Решение: удаление лишних файлов из корня .app
rm -rf dist/Nexy.app/Nexy.app  # удалить вложенный .app
rm -rf dist/Nexy.app/*.txt     # удалить текстовые файлы
```

#### **Ошибка: "a sealed resource is missing or invalid"**
```bash
# Решение: пересборка и подпись в staging
make clean
make sanitize-dist setup-staging app restage-app-root sign-nested sign-app stage-to-dist
```

#### **Ошибка: "code signing failed with exit code 1"**
```bash
# Проверка сертификата
security find-identity -v -p codesigning

# Проверка прав на файл
ls -la dist/Nexy.app/Contents/MacOS/Nexy
chmod +x dist/Nexy.app/Contents/MacOS/Nexy
```

### 2.7 Проверка подписи

#### **Базовые проверки:**
```bash
# Проверка подписи .app
codesign --verify --deep --strict --verbose=2 dist/Nexy.app

# Проверка Gatekeeper
spctl --assess --type execute --verbose dist/Nexy.app

# Проверка PKG
pkgutil --check-signature Nexy.pkg

# Проверка DMG
spctl -a -v Nexy.dmg
```

#### **Детальная информация о подписи:**
```bash
# Информация о подписи
codesign -dv --verbose=4 dist/Nexy.app

# Список entitlements
codesign -d --entitlements - dist/Nexy.app

# Проверка нотаризации
spctl -a -v --type install dist/Nexy.app
```

### 2.8 Автоматизация с Makefile

**Используйте готовые команды:**
```bash
# Полный пайплайн
make all

# Только подпись
make sign-app

# Только нотаризация
make notarize-all

# Проверка готовности
make doctor
```

### 2.9 Безопасность и best practices

#### **Хранение секретов:**
- ✅ Используйте environment variables
- ✅ Не коммитьте сертификаты в git
- ✅ Используйте App-Specific Passwords
- ✅ Ротируйте пароли регулярно

#### **Проверки перед релизом:**
- ✅ Все артефакты подписаны
- ✅ Все артефакты нотаризованы
- ✅ Gatekeeper проходит проверку
- ✅ Приложение запускается на чистой системе

#### **Мониторинг:**
- ✅ Проверяйте срок действия сертификатов
- ✅ Следите за изменениями в Apple требованиях
- ✅ Тестируйте на разных версиях macOS

---

## 3) Подготовка .app (PyInstaller)

1.1 Info.plist (обязательные ключи):
- `CFBundleIdentifier = $BUNDLE_ID`
- `CFBundleShortVersionString = $APP_VERSION`
- `CFBundleVersion = $APP_BUILD`
- `LSBackgroundOnly = 1` (для menubar‑приложений на rumps — опционально)
- Usage Descriptions (микрофон/скрин/камера/уведомления):
  - `NSMicrophoneUsageDescription`
  - `NSCameraUsageDescription` (если требуется)
  - `NSScreenCaptureUsageDescription`
  - `NSUserNotificationUsageDescription` (или UNNotifications)

1.2 Entitlements (entitlements.plist):
- `com.apple.security.app-sandbox` = false (Developer ID, не Mac App Store)
- `com.apple.security.cs.disable-library-validation` = true (для системных библиотек)
- Доступность/Automation при необходимости (Accessibility / AppleEvents)

1.3 PyInstaller (.spec шаблон):
```
# Nexy.spec — шаблон PyInstaller для сборки macOS .app
block_cipher = None

a = Analysis([
    'client/main.py',
],
    pathex=[],
    binaries=[],
    datas=[
        # Конфигурационные файлы и ресурсы
        ('client/config', 'config'),
        ('client/assets', 'assets'),
    ],
    hiddenimports=[
        'rumps', 'asyncio', 'grpc', 'pyaudio', 'PIL', 'speech_recognition', 
        'pynput', 'psutil', 'keyring', 'cryptography', 'urllib3', 'nacl', 'packaging',
        # Новые модули (instance_manager и autostart_manager)
        'modules.instance_manager.core.instance_manager',
        'modules.instance_manager.core.types',
        'modules.instance_manager.core.config',
        'modules.autostart_manager.core.autostart_manager',
        'modules.autostart_manager.core.types',
        'modules.autostart_manager.core.config',
        'modules.autostart_manager.macos.launch_agent',
        'modules.autostart_manager.macos.login_item',
        # Новые интеграции
        'integration.integrations.instance_manager_integration',
        'integration.integrations.autostart_manager_integration',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app = BUNDLE(pyz,
             a.scripts,
             name='Nexy.app',
             icon='client/assets/logo.icns',
             bundle_identifier='com.nexy.assistant',
             info_plist={
                 'CFBundleName': 'Nexy',
                 'CFBundleShortVersionString': '2.5.0',
                 'CFBundleVersion': '20500',
                 'LSMinimumSystemVersion': '11.0',
                 'LSBackgroundOnly': True,
                 'NSMicrophoneUsageDescription': 'Nexy нужен доступ к микрофону для распознавания голосовых команд',
                 'NSScreenCaptureUsageDescription': 'Nexy делает скриншоты для понимания контекста вашего экрана',
             },
             argv_emulation=False,
             target_arch='arm64')
```
Сборка: `pyinstaller --clean -y Nexy.spec` → `dist/Nexy.app`

Проверка локального запуска .app: OK.

---

## 2) Подпись .app (codesign, hardened runtime)

2.1 Подписать .app c entitlements:
```
codesign --force --deep --options runtime --timestamp \
  --entitlements entitlements.plist \
  --sign "$DEVELOPER_ID_APP" dist/Nexy.app

codesign --verify --deep --strict --verbose=2 dist/Nexy.app
spctl --assess --type execute --verbose dist/Nexy.app
```

---

## 3) Сборка и подпись PKG

3.1 Сборка PKG (ИСПРАВЛЕНО - единая стратегия установки):
```
productbuild \
  --component dist/Nexy.app ~/Applications \
  --sign "$DEVELOPER_ID_INSTALLER" \
  Nexy-$APP_VERSION.pkg
```

3.2 Верификация подписи PKG:
```
pkgutil --check-signature Nexy-$APP_VERSION.pkg
```

---

## 4) Нотарификация и stapling

4.1 Отправка на нотарификацию:
```
xcrun notarytool submit Nexy-$APP_VERSION.pkg \
  --keychain-profile "$APPLE_NOTARY_PROFILE" \
  --wait
```

4.2 Stapler:
```
xcrun stapler staple Nexy-$APP_VERSION.pkg
```

Проверка: установка PKG на чистом пользователе без предупреждений Gatekeeper.

---

## 5) HTTP Update System (обновления)

5.1 Готовим JSON манифест `manifest.json`:
```json
{
  "version": "2.5.0",
  "build": 20500,
  "release_date": "2025-09-19T10:00:00Z",
  "artifact": {
    "type": "dmg",
    "url": "https://api.yourdomain.com/updates/Nexy-2.5.0.dmg",
    "size": 12345678,
    "sha256": "abc123...",
    "ed25519": "BASE64_SIGNATURE",
    "arch": "arm64",
    "min_os": "11.0"
  },
  "notes_url": "https://api.yourdomain.com/changelog/2.5.0"
}
```

5.2 Публикация:
- Разместить `manifest.json` и `Nexy-$APP_VERSION.dmg` по HTTPS (например, Azure Static Site/App Service).
- Проверить доступность: `https://api.yourdomain.com/updates/manifest.json`.

5.3 Клиент:
- Убедиться, что конфиг указывает на правильный manifest URL.
- Проверить автообновление при выходе новой версии.

---

## 6) Автоматизация (шаблон Makefile)

```
.PHONY: app sign-app pkg notarize staple all clean

VERSION ?= 2.5.0
BUILD ?= 20500

all: app sign-app pkg notarize staple

app:
	pyinstaller --clean -y Nexy.spec

sign-app:
	codesign --force --deep --options runtime --timestamp \
	  --entitlements entitlements.plist \
	  --sign "$(DEVELOPER_ID_APP)" dist/Nexy.app
	codesign --verify --deep --strict --verbose=2 dist/Nexy.app

pkg:
	productbuild --component dist/Nexy.app ~/Applications \
	  --sign "$(DEVELOPER_ID_INSTALLER)" Nexy-$(VERSION).pkg

notarize:
	xcrun notarytool submit Nexy-$(VERSION).pkg \
	  --keychain-profile "$(APPLE_NOTARY_PROFILE)" --wait

staple:
	xcrun stapler staple Nexy-$(VERSION).pkg

clean:
	rm -rf build dist Nexy-*.pkg
```

---

## 7) Чек‑лист перед релизом

- [ ] Версии в Info.plist обновлены (ShortVersion/Build)
- [ ] Update manifest URL указывает на актуальный manifest.json
- [ ] Entitlements соответствуют требованиям (Mic/Screen/Notifications/Accessibility)
- [ ] .app подписан (codesign verify OK)
- [ ] PKG подписан и нотарифицирован, stapled
- [ ] Manifest.json доступен по HTTPS, запись корректна
- [ ] DMG файл создан и подписан
- [ ] Автообновление проверено на клиенте (HTTP система)
- [ ] **НОВОЕ:** Защита от дублирования работает (InstanceManagerIntegration)
- [ ] **НОВОЕ:** Автозапуск работает (LaunchAgent с bundle_id)
- [ ] **НОВОЕ:** PyInstaller spec включает новые модули (instance_manager, autostart_manager)
- [ ] **НОВОЕ:** PKG устанавливается в ~/Applications (единая стратегия)

---

## 8) Новые модули и их интеграция

### 8.1 Защита от дублирования (InstanceManagerIntegration)
- **Функция:** Блокирующая проверка дублирования при запуске
- **Механизм:** Файловые блокировки + PID валидация + TOCTOU защита
- **Аудио-сигналы:** Событие `signal.duplicate_instance` для незрячих пользователей
- **Порядок запуска:** ПЕРВЫМ в SimpleModuleCoordinator (блокирующий)

### 8.2 Автозапуск (AutostartManagerIntegration)
- **Функция:** LaunchAgent управление через bundle_id
- **Механизм:** `open -b com.nexy.assistant` (без жестких путей)
- **Совместимость:** KeepAlive.SuccessfulExit=false (совместимость с обновлениями)
- **Порядок запуска:** ПОСЛЕДНИМ в SimpleModuleCoordinator (неблокирующий)

### 8.3 Единая стратегия установки
- **Целевая папка:** `~/Applications` (без root)
- **PKG команда:** `productbuild --component dist/Nexy.app ~/Applications`
- **Совместимость:** Никакой миграции не требуется (updater уже настроен)

---

## 9) Типичные проблемы и решения

- Ошибка notarization: проверьте, что используете Developer ID, hardened runtime, timestamp, и что PKG подписан Installer‑сертификатом.
- Gatekeeper ругается: повторно проверьте stapler и целостность подписи.
- HTTP система не видит обновления: проверьте manifest URL и доступность manifest.json/DMG; корректность версии/даты/подписи.
- Фреймворки/библиотеки: убедитесь, что все вложенные .dylib/.framework подписаны до подписи .app.
- **НОВОЕ:** Дублирование экземпляров: проверьте что InstanceManagerIntegration запускается первым и вызывает `sys.exit(1)` при дублировании.
- **НОВОЕ:** Автозапуск не работает: проверьте LaunchAgent с `open -b com.nexy.assistant` и KeepAlive.SuccessfulExit=false.
- **НОВОЕ:** PKG устанавливается не туда: проверьте `productbuild --component ~/Applications` и `pkgutil --expand` для верификации.

---

## 10) Где хранить скрипты/артефакты

- Рекомендуемая структура:
```
client/
  tools/
    packaging/
      entitlements.plist
      setup.py
      Makefile
```

Док: этот файл (PACKAGING_PLAN.md) — источник истины по этапам упаковки.
