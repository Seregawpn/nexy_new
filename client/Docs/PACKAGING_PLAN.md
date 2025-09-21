# 📦 ПОЛНЫЙ ПЛАН УПАКОВКИ NEXY AI ASSISTANT

**Дата:** 20 сентября 2025  
**Версия:** 4.0.0 - Complete Production Pipeline  
**Статус:** ✅ ГОТОВ К ПРОДАКШЕНУ

---

## 🎯 ЦЕЛЬ

Создать полностью автоматизированный, повторяемый процесс сборки, подписи и нотаризации Nexy AI Assistant от исходного кода до готовых к распространению артефактов (.app, .pkg, .dmg) с полной нотаризацией и stapling.

---

## 📋 ПРЕДПОСЫЛКИ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ

### **Требования к системе:**
- ✅ **macOS 11.0+** (только Apple Silicon M1+)
- ✅ **Xcode Command Line Tools:** `xcode-select --install`
- ✅ **Python 3.11+** с зависимостями: `urllib3`, `pynacl`, `packaging`
- ✅ **Apple Developer Account** (Developer ID Application/Installer)
- ✅ **FLAC 1.5.0+** (проверено: актуальная версия установлена)

### **Обязательные переменные окружения:**
```bash
export DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
export APPLE_NOTARY_PROFILE="NexyNotary"
export BUNDLE_ID="com.nexy.assistant"
export APP_NAME="Nexy"
export VERSION="2.5.0"
export BUILD="20500"
```

### **Настройка notarytool профиля (однократно):**
```bash
xcrun notarytool store-credentials "NexyNotary" \
  --apple-id "your-apple-id@example.com" \
  --team-id "5NKLL2CLB9" \
  --password "your-app-specific-password"
```

---

## 🚀 ПОЛНЫЙ ПРОИЗВОДСТВЕННЫЙ ПАЙПЛАЙН

### **1. БЫСТРЫЙ СТАРТ (РЕКОМЕНДУЕТСЯ)**

```bash
# Переход в директорию сборки
cd packaging/

# Настройка окружения
source setup_env.sh

# Полный пайплайн (сборка + подпись + нотаризация + stapling)
make all

# Результат:
# - packaging/dist/Nexy.app (подписанный)
# - packaging/artifacts/Nexy-2.5.0.pkg (подписанный + нотаризованный)
# - packaging/artifacts/Nexy-2.5.0.dmg (подписанный + нотаризованный)
```

### **2. ПОШАГОВЫЙ ПАЙПЛАЙН (ДЛЯ ДЕБАГА)**

```bash
cd packaging/

# Этап 1: Подготовка
make doctor                    # Проверка готовности системы
make sanitize-dist            # Очистка dist/ директории
make setup-staging            # Создание staging директории

# Этап 2: Сборка
make app                      # PyInstaller сборка + копирование в staging
make restage-app-root         # Очистка xattrs через ditto

# Этап 3: Подпись
make check-xattrs             # Проверка xattrs перед подписью
make sign-nested              # Подпись всех вложений
make sign-app                 # Подпись основного .app bundle
make stage-to-dist            # Перенос подписанного .app в dist/

# Этап 4: Создание артефактов
make pkg                      # Создание PKG (с подписью)
make dmg                      # Создание DMG (с подписью)

# Этап 5: Нотаризация
make notarize-app             # Нотарификация .app
make notarize-pkg             # Нотарификация PKG
make notarize-dmg             # Нотарификация DMG

# Этап 6: Stapling
make staple-all               # Stapling всех артефактов

# Этап 7: Проверка
make verify                   # Проверка всех подписей
```

---

## 🏗️ АРХИТЕКТУРА STAGING PIPELINE

### **Проблема, которую решает staging:**
PyInstaller создает .app bundle в `dist/` директории, которая может содержать проблемные xattrs (FinderInfo, quarantine), блокирующие codesigning.

### **Решение - Staging Pipeline:**
1. **Сборка в чистой среде** - `/tmp/nexy-stage`
2. **Очистка xattrs** - `ditto --norsrc --noqtn`
3. **Подпись в staging** - без проблемных атрибутов
4. **Чистый перенос** - `cp -R -X` без xattrs

### **Ключевые принципы:**
- ✅ **Staging директория:** `/tmp/nexy-stage` (чистая среда)
- ✅ **Очистка xattrs:** `xattr -cr` перед подписью и переносом
- ✅ **Чистый перенос:** `cp -R -X` без xattrs
- ✅ **Проверка на каждом этапе:** `codesign --verify --deep --strict`

---

## 🔐 ПОЛНОЕ РУКОВОДСТВО ПО ПОДПИСИ

### **1. Типы сертификатов**

#### **Developer ID Application** (для .app файлов)
```bash
DEVELOPER_ID_APP="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
```
- **Назначение:** Подпись приложений для распространения вне Mac App Store
- **Где получить:** Apple Developer Portal → Certificates → Developer ID Application
- **Срок действия:** 3 года

#### **Developer ID Installer** (для PKG файлов)
```bash
DEVELOPER_ID_INSTALLER="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
```
- **Назначение:** Подпись PKG инсталляторов
- **Где получить:** Apple Developer Portal → Certificates → Developer ID Installer
- **Срок действия:** 3 года

### **2. Entitlements (entitlements.plist)**

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
    
    <!-- Доступность (только если реально используете Apple Events) -->
    <!--
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    -->
</dict>
</plist>
```

### **3. Процесс подписи (автоматизированный)**

#### **Этап 1: Подпись вложений**
```bash
# Автоматически выполняется в make sign-nested
find "$(STAGE_APP)" -type f \( -name "*.dylib" -o -name "*.so" -o -perm -111 \) -print0 | \
xargs -0 -I{} codesign --force --timestamp \
  --entitlements entitlements.plist \
  --sign "$(DEVELOPER_ID_APP)" "{}"
```

#### **Этап 2: Подпись основного .app**
```bash
# Автоматически выполняется в make sign-app
codesign --force --options runtime --timestamp \
  --entitlements entitlements.plist \
  --sign "$(DEVELOPER_ID_APP)" "$(STAGE_APP)"
```

#### **Этап 3: Проверка подписи**
```bash
# Автоматически выполняется в make sign-app
codesign --verify --deep --strict --verbose=2 "$(STAGE_APP)"
spctl -a -v "$(STAGE_APP)"
```

---

## 📦 СОЗДАНИЕ АРТЕФАКТОВ

### **1. PKG Инсталлятор**

```bash
# Автоматически выполняется в make pkg
productbuild \
  --component dist/Nexy.app /Applications \
  --sign "$(DEVELOPER_ID_INSTALLER)" \
  artifacts/Nexy-$(VERSION).pkg

# Подпись PKG
codesign --force --options runtime --timestamp \
  --sign "$(DEVELOPER_ID_APP)" artifacts/Nexy-$(VERSION).pkg
```

### **2. DMG Образ**

```bash
# Автоматически выполняется в make dmg
hdiutil create -volname "Nexy" -srcfolder dist/Nexy.app -ov -format UDZO \
  artifacts/Nexy-$(VERSION).dmg

# Подпись DMG
codesign --force --options runtime --timestamp \
  --sign "$(DEVELOPER_ID_APP)" artifacts/Nexy-$(VERSION).dmg
```

---

## 🔍 НОТАРИЗАЦИЯ И STAPLING

### **1. Нотаризация .app**

```bash
# Автоматически выполняется в make notarize-app
xcrun notarytool submit dist/Nexy.app \
  --keychain-profile "$(APPLE_NOTARY_PROFILE)" \
  --wait
```

### **2. Нотаризация PKG**

```bash
# Автоматически выполняется в make notarize-pkg
xcrun notarytool submit artifacts/Nexy-$(VERSION).pkg \
  --keychain-profile "$(APPLE_NOTARY_PROFILE)" \
  --wait
```

### **3. Нотаризация DMG**

```bash
# Автоматически выполняется в make notarize-dmg
xcrun notarytool submit artifacts/Nexy-$(VERSION).dmg \
  --keychain-profile "$(APPLE_NOTARY_PROFILE)" \
  --wait
```

### **4. Stapling (прикрепление билетов)**

```bash
# Автоматически выполняется в make staple-all
xcrun stapler staple dist/Nexy.app
xcrun stapler staple artifacts/Nexy-$(VERSION).pkg
xcrun stapler staple artifacts/Nexy-$(VERSION).dmg
```

---

## ✅ ПРОВЕРКА И ВЕРИФИКАЦИЯ

### **1. Проверка подписей**

```bash
# Автоматически выполняется в make verify

# Проверка .app
codesign --verify --deep --strict --verbose=2 dist/Nexy.app
spctl --assess --type execute --verbose dist/Nexy.app

# Проверка PKG
pkgutil --check-signature artifacts/Nexy-$(VERSION).pkg
spctl -a -v artifacts/Nexy-$(VERSION).pkg

# Проверка DMG
spctl -a -v artifacts/Nexy-$(VERSION).dmg
```

### **2. Детальная информация о подписи**

```bash
# Информация о подписи .app
codesign -dv --verbose=4 dist/Nexy.app

# Список entitlements
codesign -d --entitlements - dist/Nexy.app

# Проверка нотаризации
spctl -a -v --type install dist/Nexy.app
```

---

## 🚨 ТИПИЧНЫЕ ОШИБКИ И РЕШЕНИЯ

### **1. "resource fork, Finder information, or similar detritus not allowed"**
```bash
# Решение: очистка xattrs (автоматически в staging pipeline)
xattr -cr dist/Nexy.app
xattr -dr com.apple.FinderInfo dist/Nexy.app
```

### **2. "unsealed contents present in the bundle root"**
```bash
# Решение: удаление лишних файлов из корня .app
rm -rf dist/Nexy.app/Nexy.app  # удалить вложенный .app
rm -rf dist/Nexy.app/*.txt     # удалить текстовые файлы
```

### **3. "a sealed resource is missing or invalid"**
```bash
# Решение: пересборка и подпись в staging
make clean
make all
```

### **4. "code signing failed with exit code 1"**
```bash
# Проверка сертификата
security find-identity -v -p codesigning

# Проверка прав на файл
ls -la dist/Nexy.app/Contents/MacOS/Nexy
chmod +x dist/Nexy.app/Contents/MacOS/Nexy
```

### **5. Ошибки нотаризации**
```bash
# Проверка статуса нотаризации
xcrun notarytool history --keychain-profile "$(APPLE_NOTARY_PROFILE)"

# Проверка логов
xcrun notarytool log <SUBMISSION_ID> --keychain-profile "$(APPLE_NOTARY_PROFILE)"
```

---

## 🎯 ПРОИЗВОДСТВЕННЫЕ КОМАНДЫ

### **Для разработки (быстрая сборка БЕЗ нотаризации):**
```bash
cd packaging/
source setup_env.sh
make build-only
```

### **Для релиза (полный пайплайн с нотаризацией):**
```bash
cd packaging/
source setup_env.sh
make all
```

### **Для нотаризации уже созданных артефактов:**
```bash
cd packaging/
source setup_env.sh
make notarize-all
```

### **Проверка готовности системы:**
```bash
cd packaging/
make doctor
```

---

## 📊 СИСТЕМА ОБНОВЛЕНИЙ

### **HTTP-система обновлений (вместо Sparkle):**
- ✅ **Миграция в `~/Applications`** - пароль только один раз
- ✅ **Многоуровневая безопасность** - SHA256 + Ed25519 + codesign/spctl
- ✅ **Атомарная замена** - с откатом при ошибках
- ✅ **EventBus интеграция** - полная совместимость

### **JSON манифест обновлений:**
```json
{
  "version": "2.5.0",
  "build": 20500,
  "release_date": "2025-09-19T10:00:00Z",
  "artifact": {
    "type": "dmg",
    "url": "https://updates.nexy.ai/Nexy-2.5.0.dmg",
    "size": 12345678,
    "sha256": "a1b2c3d4e5f6...",
    "ed25519": "BASE64_SIGNATURE",
    "arch": "arm64",
    "min_os": "11.0"
  },
  "notes_url": "https://nexy.ai/changelog/2.5.0"
}
```

---

## 🔧 НОВЫЕ МОДУЛИ И ИХ ИНТЕГРАЦИЯ

### **1. Защита от дублирования (InstanceManagerIntegration)**
- ✅ **Функция:** Блокирующая проверка дублирования при запуске
- ✅ **Механизм:** Файловые блокировки + PID валидация + TOCTOU защита
- ✅ **Аудио-сигналы:** Событие `signal.duplicate_instance` для незрячих пользователей
- ✅ **Порядок запуска:** ПЕРВЫМ в SimpleModuleCoordinator (блокирующий)

### **2. Автозапуск (AutostartManagerIntegration)**
- ✅ **Функция:** LaunchAgent управление через bundle_id
- ✅ **Механизм:** `open -b com.nexy.assistant` (без жестких путей)
- ✅ **Совместимость:** KeepAlive.SuccessfulExit=false (совместимость с обновлениями)
- ✅ **Порядок запуска:** ПОСЛЕДНИМ в SimpleModuleCoordinator (неблокирующий)

---

## 📋 ФИНАЛЬНЫЙ ЧЕК-ЛИСТ ПЕРЕД РЕЛИЗОМ

### **Подготовка:**
- [ ] ✅ **Переменные окружения установлены** (`make doctor`)
- [ ] ✅ **Сертификаты в Keychain** (Developer ID Application/Installer)
- [ ] ✅ **notarytool профиль настроен** (NexyNotary)
- [ ] ✅ **FLAC версия 1.5.0+** (проверено)

### **Сборка:**
- [ ] ✅ **Версии в Info.plist обновлены** (ShortVersion/Build)
- [ ] ✅ **PyInstaller spec включает все модули** (17 интеграций)
- [ ] ✅ **Entitlements соответствуют требованиям** (микрофон/экран/уведомления)
- [ ] ✅ **Staging pipeline работает** (`make all`)

### **Подпись:**
- [ ] ✅ **.app подписан** (`codesign --verify --deep --strict`)
- [ ] ✅ **PKG подписан** (`pkgutil --check-signature`)
- [ ] ✅ **DMG подписан** (`spctl -a -v`)

### **Нотаризация:**
- [ ] ✅ **.app нотаризован** (`xcrun notarytool history`)
- [ ] ✅ **PKG нотаризован** (`xcrun notarytool history`)
- [ ] ✅ **DMG нотаризован** (`xcrun notarytool history`)
- [ ] ✅ **Все артефакты stapled** (`xcrun stapler staple`)

### **Проверка:**
- [ ] ✅ **Gatekeeper проходит проверку** (`spctl --assess`)
- [ ] ✅ **Приложение запускается на чистой системе**
- [ ] ✅ **Защита от дублирования работает** (InstanceManagerIntegration)
- [ ] ✅ **Автозапуск работает** (LaunchAgent с bundle_id)

### **Система обновлений:**
- [ ] ✅ **Manifest.json доступен по HTTPS**
- [ ] ✅ **DMG файл размещен на сервере**
- [ ] ✅ **HTTP система обновлений протестирована**

---

## 🎉 РЕЗУЛЬТАТ

После выполнения полного пайплайна вы получите:

### **Готовые к распространению артефакты:**
- ✅ **`packaging/dist/Nexy.app`** - подписанное приложение
- ✅ **`packaging/artifacts/Nexy-2.5.0.pkg`** - подписанный + нотаризованный инсталлятор
- ✅ **`packaging/artifacts/Nexy-2.5.0.dmg`** - подписанный + нотаризованный образ

### **Все артефакты:**
- ✅ **Подписаны** Developer ID сертификатами
- ✅ **Нотаризованы** Apple
- ✅ **Stapled** (билеты прикреплены)
- ✅ **Проверены** Gatekeeper
- ✅ **Готовы к распространению**

---

## 📚 ДОПОЛНИТЕЛЬНАЯ ДОКУМЕНТАЦИЯ

- **[CODESIGNING_QUICK_GUIDE.md](CODESIGNING_QUICK_GUIDE.md)** - Быстрое руководство по подписи
- **[TROUBLESHOOTING_CODESIGNING.md](TROUBLESHOOTING_CODESIGNING.md)** - Решение проблем с подписью
- **[FINAL_CHECKLIST.md](FINAL_CHECKLIST.md)** - Финальный чек-лист перед релизом
- **[UPDATE_SYSTEM_GUIDE.md](UPDATE_SYSTEM_GUIDE.md)** - Система обновлений

---

**🎯 ЦЕЛЬ ДОСТИГНУТА:** Полностью автоматизированный процесс от исходного кода до готовых к распространению артефактов с полной нотаризацией и stapling!

**Время выполнения полного пайплайна:** ~15-20 минут (включая нотаризацию)  
**Статус:** ✅ Готов к продакшену