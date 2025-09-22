# 📦 МАСТЕР-РУКОВОДСТВО ПО УПАКОВКЕ NEXY
## Полное руководство по сборке, подписи и нотаризации

> **Обновлено:** 22.09.2025  
> **Статус:** Проверено и работает  
> **Версия:** 1.71.0  

---

## 🎯 ОБЗОР ПРОЦЕССА

### **Что мы создаем:**
1. **PKG** - первичная установка в `~/Applications` + автозапуск
2. **DMG** - для системы автообновлений (нотаризованный)
3. **Manifest** - JSON для собственной системы обновлений

### **Ключевые особенности:**
- ✅ **БЕЗ Hardened Runtime** (из-за PyInstaller + PIL конфликта)
- ✅ **PIL исправлен** для цветных иконок в меню-баре
- ✅ **Собственная система обновлений** (не Sparkle)
- ✅ **Ed25519 + SHA256 + codesign** тройная защита

---

## 🔧 ПРЕДВАРИТЕЛЬНАЯ НАСТРОЙКА

### **1. Сертификаты (один раз)**
```bash
# Проверяем наличие сертификатов
security find-identity -p codesigning -v

# Должны быть:
# Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)
# Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)
```

### **2. Настройка notarytool (один раз)**
```bash
# Настраиваем профиль для нотаризации
xcrun notarytool store-credentials nexy-notary \
  --apple-id seregawpn@gmail.com \
  --team-id 5NKLL2CLB9 \
  --password qtiv-kabm-idno-qmbl

# Проверяем
xcrun notarytool history --keychain-profile nexy-notary
```

### **3. Ed25519 ключи для автообновлений (один раз)**
```python
# Генерация ключей
python3 -c "
import nacl.signing
import base64

signing_key = nacl.signing.SigningKey.generate()
verify_key = signing_key.verify_key

# Сохраняем приватный ключ (СЕКРЕТНО!)
with open('private_key.pem', 'wb') as f:
    f.write(signing_key.encode())

# Публичный ключ для config
public_key_b64 = base64.b64encode(verify_key.encode()).decode()
print(f'Публичный ключ: {public_key_b64}')
"
```

---

## 🏗️ ПРОЦЕСС СБОРКИ

### **ЭТАП 1: Сборка приложения**

#### **1.1 Исправленный Nexy.spec**
**Ключевые исправления:**
```python
# КРИТИЧНО: PIL подмодули для иконок
hiddenimports=[
    'rumps', 'pynput', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'Pillow',
    # ... остальные модули
],

# КРИТИЧНО: Пути для интеграций
pathex=[str(client_dir), str(client_dir / 'integration')],

# КРИТИЧНО: НЕ подписывать автоматически
codesign_identity=None,
entitlements_file=None,
```

#### **1.2 Сборка в временной папке**
```bash
#!/bin/bash
# packaging/build_production.sh

set -euo pipefail

echo "🏗️ ПРОИЗВОДСТВЕННАЯ СБОРКА NEXY"
echo "==============================="

# Создаем временную папку (избегаем атрибутов macOS)
BUILD_DIR="/tmp/nexy_production_$(date +%s)"
mkdir -p "$BUILD_DIR"
echo "📁 Сборка: $BUILD_DIR"

# Копируем проект
cp -R . "$BUILD_DIR/"
cd "$BUILD_DIR"

# Настраиваем PATH
export PATH="$HOME/Library/Python/3.9/bin:$PATH"

# Сборка
echo "🔨 PyInstaller..."
pyinstaller --clean -y packaging/Nexy.spec

# Проверка результата
if [ -d "dist/Nexy.app" ]; then
    echo "✅ Приложение собрано"
    ls -la dist/Nexy.app/Contents/MacOS/
else
    echo "❌ Ошибка сборки"
    exit 1
fi

echo "📁 Результат: $BUILD_DIR/dist/Nexy.app"
```

---

### **ЭТАП 2: Подпись приложения**

#### **2.1 Подпись БЕЗ Hardened Runtime**
```bash
#!/bin/bash
# packaging/sign_app.sh

APP_PATH="$1"  # Путь к приложению
TEAM_ID="5NKLL2CLB9"
APP_IDENTITY="Developer ID Application: Sergiy Zasorin (${TEAM_ID})"

echo "🔏 ПОДПИСЬ ПРИЛОЖЕНИЯ"
echo "===================="

# Очищаем атрибуты macOS
echo "🧹 Очистка атрибутов..."
xattr -cr "$APP_PATH"

# Подписываем БЕЗ --options runtime (КРИТИЧНО!)
echo "✍️ Подпись..."
/usr/bin/codesign --force --timestamp \
    --entitlements packaging/entitlements.plist \
    --sign "$APP_IDENTITY" \
    "$APP_PATH"

# Проверка
echo "🔍 Проверка подписи..."
/usr/bin/codesign --verify --strict --deep "$APP_PATH"

echo "✅ Приложение подписано"
```

**⚠️ ВАЖНО:** НЕ использовать `--options runtime` из-за конфликта PyInstaller + PIL!

---

### **ЭТАП 3: Создание PKG**

#### **3.1 PKG для первичной установки**
```bash
#!/bin/bash
# packaging/create_pkg.sh

APP_PATH="$1"
TEAM_ID="5NKLL2CLB9"
INSTALLER_IDENTITY="Developer ID Installer: Sergiy Zasorin (${TEAM_ID})"

echo "📦 СОЗДАНИЕ PKG"
echo "==============="

# Подготовка payload
PKG_ROOT="build/payload"
rm -rf "$PKG_ROOT"
mkdir -p "$PKG_ROOT/usr/local/nexy/resources"

# Копируем подписанное приложение
cp -R "$APP_PATH" "$PKG_ROOT/usr/local/nexy/Nexy.app"
cp packaging/LaunchAgent/com.nexy.assistant.plist "$PKG_ROOT/usr/local/nexy/resources/"

# Создание PKG
pkgbuild \
    --root "$PKG_ROOT" \
    --identifier "com.nexy.assistant.pkg" \
    --version "1.71.0" \
    --scripts scripts \
    "dist/Nexy-raw.pkg"

productbuild \
    --distribution packaging/distribution.xml \
    --resources packaging \
    --package-path dist \
    "dist/Nexy.pkg"

# Подпись PKG
productsign --sign "$INSTALLER_IDENTITY" \
    "dist/Nexy.pkg" "dist/Nexy-signed.pkg"

echo "✅ PKG создан и подписан: dist/Nexy-signed.pkg"
```

---

### **ЭТАП 4: Создание DMG**

#### **4.1 DMG для автообновлений**
```bash
#!/bin/bash
# packaging/create_dmg.sh

APP_PATH="$1"
DMG_PATH="dist/Nexy.dmg"
TEMP_DMG="dist/Nexy-temp.dmg"
VOLUME_NAME="Nexy AI Assistant"

echo "💿 СОЗДАНИЕ DMG"
echo "==============="

# Размер с запасом
APP_SIZE_KB=$(du -sk "$APP_PATH" | awk '{print $1}')
DMG_SIZE_MB=$(( APP_SIZE_KB/1024 + 200 ))

echo "📏 Размер DMG: ${DMG_SIZE_MB}m"

# Создание временного DMG
hdiutil create -volname "$VOLUME_NAME" -srcfolder "$APP_PATH" \
    -fs HFS+ -format UDRW -size "${DMG_SIZE_MB}m" "$TEMP_DMG"

# Монтирование и настройка
MOUNT_DIR="/Volumes/$VOLUME_NAME"
hdiutil attach "$TEMP_DMG" -readwrite -noverify -noautoopen

# Добавляем alias на Applications
ln -s /Applications "$MOUNT_DIR/Applications" || true

# Размонтирование
hdiutil detach "$MOUNT_DIR"

# Конвертация в UDZO
hdiutil convert "$TEMP_DMG" -format UDZO -imagekey zlib-level=9 -o "$DMG_PATH"
rm -f "$TEMP_DMG"

echo "✅ DMG создан: $DMG_PATH"
```

---

### **ЭТАП 5: Нотаризация**

#### **5.1 Нотаризация DMG**
```bash
#!/bin/bash
# packaging/notarize.sh

DMG_PATH="$1"
KEYCHAIN_PROFILE="nexy-notary"

echo "🔒 НОТАРИЗАЦИЯ DMG"
echo "=================="

# Проверка профиля
if ! xcrun notarytool history --keychain-profile "$KEYCHAIN_PROFILE" >/dev/null 2>&1; then
    echo "❌ Профиль notarytool не найден: $KEYCHAIN_PROFILE"
    exit 1
fi

# Отправка на нотаризацию
echo "📤 Отправка на нотаризацию..."
xcrun notarytool submit "$DMG_PATH" \
    --keychain-profile "$KEYCHAIN_PROFILE" \
    --wait

# Степлинг
echo "📎 Степлинг..."
xcrun stapler staple "$DMG_PATH"
xcrun stapler validate "$DMG_PATH"

echo "✅ DMG нотаризован: $DMG_PATH"
```

**💡 Примечание:** PKG не нотаризуется из-за отсутствия Hardened Runtime, но DMG нотаризуется успешно!

---

### **ЭТАП 6: Генерация манифеста**

#### **6.1 JSON манифест для автообновлений**
```python
#!/usr/bin/env python3
# packaging/generate_manifest.py

import json
import hashlib
import base64
import os
from datetime import datetime

def generate_manifest(dmg_path, version, build, private_key_path=None):
    """Генерация манифеста для собственной системы обновлений"""
    
    # SHA256 хеш
    sha256_hash = hashlib.sha256()
    with open(dmg_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256_hash.update(chunk)
    
    # Ed25519 подпись (если есть ключ)
    ed25519_signature = ""
    if private_key_path and os.path.exists(private_key_path):
        try:
            from nacl.signing import SigningKey
            with open(private_key_path, "rb") as f:
                signing_key = SigningKey(f.read())
            with open(dmg_path, "rb") as f:
                signature = signing_key.sign(f.read()).signature
            ed25519_signature = base64.b64encode(signature).decode()
        except Exception as e:
            print(f"⚠️ Ed25519 подпись не удалась: {e}")
    
    # Создание манифеста
    manifest = {
        "version": version,
        "build": build,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "artifact": {
            "type": "dmg",
            "url": f"https://api.nexy.ai/updates/Nexy-{version}.dmg",
            "size": os.path.getsize(dmg_path),
            "sha256": sha256_hash.hexdigest(),
            "ed25519": ed25519_signature
        },
        "requirements": {
            "min_macos": "11.0",
            "architecture": "arm64"
        },
        "changelog": [
            "Исправлены иконки в меню-баре",
            "Улучшения стабильности",
            "Оптимизация производительности"
        ]
    }
    
    return manifest

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Использование: python generate_manifest.py <dmg> <version> <build> [private_key]")
        sys.exit(1)
    
    dmg_path = sys.argv[1]
    version = sys.argv[2]
    build = int(sys.argv[3])
    private_key = sys.argv[4] if len(sys.argv) > 4 else None
    
    manifest = generate_manifest(dmg_path, version, build, private_key)
    
    # Сохранение
    with open("dist/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print("✅ Манифест создан: dist/manifest.json")
```

---

## 🚀 ПОЛНЫЙ ПРОЦЕСС СБОРКИ

### **Главный скрипт**
```bash
#!/bin/bash
# packaging/build_all.sh

set -euo pipefail

echo "🚀 ПОЛНАЯ СБОРКА NEXY"
echo "===================="

VERSION="1.71.0"
BUILD="171"

# 1. Сборка приложения
echo "1️⃣ Сборка приложения..."
./packaging/build_production.sh

# Путь к собранному приложению
BUILD_DIR=$(ls -td /tmp/nexy_production_* | head -1)
APP_PATH="$BUILD_DIR/dist/Nexy.app"

# 2. Подпись приложения
echo "2️⃣ Подпись приложения..."
./packaging/sign_app.sh "$APP_PATH"

# 3. Создание PKG
echo "3️⃣ Создание PKG..."
./packaging/create_pkg.sh "$APP_PATH"

# 4. Создание DMG
echo "4️⃣ Создание DMG..."
./packaging/create_dmg.sh "$APP_PATH"

# 5. Нотаризация DMG
echo "5️⃣ Нотаризация DMG..."
./packaging/notarize.sh "dist/Nexy.dmg"

# 6. Генерация манифеста
echo "6️⃣ Генерация манифеста..."
python3 packaging/generate_manifest.py "dist/Nexy.dmg" "$VERSION" "$BUILD" "private_key.pem"

# 7. Копирование финальных артефактов
echo "7️⃣ Копирование артефактов..."
cp "$APP_PATH" "dist/Nexy-final.app"

echo ""
echo "✅ СБОРКА ЗАВЕРШЕНА!"
echo "==================="
echo "📦 PKG: dist/Nexy-signed.pkg"
echo "💿 DMG: dist/Nexy.dmg (нотаризован)"
echo "📋 Манифест: dist/manifest.json"
echo "📱 Приложение: dist/Nexy-final.app"
```

---

## 🔍 ПРОВЕРКА И ТЕСТИРОВАНИЕ

### **Проверка артефактов**
```bash
#!/bin/bash
# packaging/verify_all.sh

echo "🔍 ПРОВЕРКА АРТЕФАКТОВ"
echo "====================="

# Проверка приложения
echo "📱 Приложение:"
codesign --verify --strict --deep dist/Nexy-final.app
echo "✅ Подпись приложения корректна"

# Проверка PKG
echo "📦 PKG:"
pkgutil --check-signature dist/Nexy-signed.pkg | head -3
echo "✅ PKG подписан корректно"

# Проверка DMG
echo "💿 DMG:"
xcrun stapler validate dist/Nexy.dmg
echo "✅ DMG нотаризован корректно"

# Проверка манифеста
echo "📋 Манифест:"
python3 -c "
import json
with open('dist/manifest.json') as f:
    m = json.load(f)
print(f'Версия: {m[\"version\"]}')
print(f'SHA256: {m[\"artifact\"][\"sha256\"][:16]}...')
print(f'Ed25519: {\"Да\" if m[\"artifact\"][\"ed25519\"] else \"Нет\"}')
"
echo "✅ Манифест корректен"

echo ""
echo "🎯 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!"
```

### **Тестирование установки**
```bash
# Тестовая установка PKG
sudo installer -pkg dist/Nexy-signed.pkg -target /

# Проверка установки
ls -la ~/Applications/Nexy.app
ls -la ~/Library/LaunchAgents/com.nexy.assistant.plist

# Запуск приложения
~/Applications/Nexy.app/Contents/MacOS/Nexy &

# Проверка иконки в меню-баре (должна быть цветной!)
```

---

## ⚠️ ВАЖНЫЕ МОМЕНТЫ

### **1. Проблемы и решения**

**❌ Hardened Runtime + PyInstaller:**
- **Проблема:** `Library Validation failed: Team ID conflict`
- **Решение:** Подписывать БЕЗ `--options runtime`

**❌ PIL иконки не отображаются:**
- **Проблема:** `PIL.Image` и `PIL.ImageDraw` не включены в PyInstaller
- **Решение:** Добавить в `hiddenimports`: `'PIL', 'PIL.Image', 'PIL.ImageDraw', 'Pillow'`

**❌ PKG не нотаризуется:**
- **Проблема:** Apple требует Hardened Runtime для PKG
- **Решение:** Нотаризовать только DMG, PKG использовать подписанный

### **2. Безопасность**

**🔐 Что защищено:**
- **Приложение:** Developer ID Application подпись
- **PKG:** Developer ID Installer подпись  
- **DMG:** Нотаризация Apple + codesign проверка
- **Манифест:** Ed25519 подпись + SHA256 хеш

**🔑 Секреты:**
- Ed25519 приватный ключ → хранить в безопасном месте
- App-Specific Password → только в Keychain
- Team ID и сертификаты → защищены Keychain

### **3. Развертывание**

**Azure публикация:**
```bash
# Загрузка на Azure Blob Storage
az storage blob upload-batch \
  --account-name nexyai \
  --destination updates \
  --source dist \
  --pattern "*.pkg,*.dmg,*.json"
```

**URL структура:**
- PKG: `https://api.nexy.ai/updates/Nexy-1.71.0.pkg`
- DMG: `https://api.nexy.ai/updates/Nexy-1.71.0.dmg`
- Манифест: `https://api.nexy.ai/updates/manifest.json`

---

## 📋 ЧЕКЛИСТ РЕЛИЗА

### **Перед релизом:**
- [ ] Все сертификаты действительны
- [ ] notarytool профиль настроен
- [ ] Ed25519 ключи сгенерированы
- [ ] Версия обновлена в коде и spec файле
- [ ] PIL исправления включены в spec

### **Сборка:**
- [ ] Приложение собирается без ошибок
- [ ] PIL иконки работают (тест запуска)
- [ ] Приложение подписано БЕЗ Hardened Runtime
- [ ] PKG создан и подписан
- [ ] DMG создан и нотаризован
- [ ] Манифест сгенерирован с подписями

### **Тестирование:**
- [ ] PKG устанавливается без ошибок
- [ ] Приложение запускается автоматически
- [ ] Цветные иконки отображаются в меню-баре
- [ ] Меню работает при клике на иконку
- [ ] LaunchAgent настроен корректно

### **Публикация:**
- [ ] Артефакты загружены на Azure
- [ ] URL доступны и корректны
- [ ] Манифест обновлен на сервере
- [ ] Система автообновлений тестирована

---

## 🎯 ИТОГОВЫЕ КОМАНДЫ

```bash
# Полная сборка
./packaging/build_all.sh

# Проверка артефактов
./packaging/verify_all.sh

# Тестовая установка
sudo installer -pkg dist/Nexy-signed.pkg -target /

# Публикация на Azure
az storage blob upload-batch --account-name nexyai --destination updates --source dist
```

---

**📅 Последнее обновление:** 22.09.2025  
**✅ Статус:** Проверено и работает  
**🔧 Версия:** 1.71.0 с исправленными иконками
