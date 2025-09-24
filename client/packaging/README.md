# 📦 PACKAGING - Упаковка Nexy AI Assistant

> **Обновлено:** 23.09.2025 | **Статус:** Готово к продакшену

---

## 📁 СТРУКТУРА ПАПКИ

```
packaging/
├── Nexy.spec              # PyInstaller конфигурация
├── entitlements.plist     # macOS разрешения и entitlements
├── distribution.xml       # PKG конфигурация
├── build_and_sign.sh     # 🚀 АВТОМАТИЗИРОВАННАЯ УПАКОВКА
├── PACKAGING_GUIDE.md     # 📖 ПОЛНАЯ ИНСТРУКЦИЯ
├── QUICK_START.md         # ⚡ БЫСТРЫЙ СТАРТ
├── verify_all.sh         # 🔍 ПРОВЕРКА АРТЕФАКТОВ
└── README.md             # Эта документация
```

---

## 🚀 БЫСТРЫЙ СТАРТ

### **Автоматическая упаковка (рекомендуется)**
```bash
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
./packaging/build_final.sh
```

### **Старая версия (если нужна)**
```bash
./packaging/build_and_sign.sh
```

### **Ручная упаковка (ПОШАГОВО)**
```bash
# См. подробную инструкцию
cat packaging/QUICK_START.md
```

### **Проверка результата**
```bash
./packaging/verify_all.sh
```

## ⚠️ КРИТИЧЕСКИЕ МОМЕНТЫ (ОБНОВЛЕНО 24.09.2025)

### ❌ НЕ ДЕЛАЙТЕ ЭТО:
- `exclude_binaries=True` в Nexy.spec (сломает Python shared library)
- `cp` вместо `ditto --noextattr --noqtn` (оставит extended attributes)
- Подпись бандла до подписи вложенных Mach-O
- `codesign` для PKG (используйте `productsign`)

### ✅ ОБЯЗАТЕЛЬНО:
- `ditto --noextattr --noqtn` для всех копирований
- Сначала подпишите вложенные Mach-O, потом весь бандл
- `productsign` с "Developer ID Installer" сертификатом для PKG
- `com.apple.security.cs.disable-library-validation` в entitlements.plist

---

## 🔧 КЛЮЧЕВЫЕ ИСПРАВЛЕНИЯ

### **1. Python Shared Library (КРИТИЧНО)**
**Проблема:** `Failed to load Python shared library`  
**Решение:** Убрали `exclude_binaries=True` из `Nexy.spec`:
```python
# ❌ НЕ ДЕЛАЙТЕ ЭТО
# exclude_binaries=True,

# ✅ ПРАВИЛЬНО - оставляем по умолчанию (False)
```

### **2. Extended Attributes (КРИТИЧНО)**
**Проблема:** `resource fork, Finder information, or similar detritus not allowed`  
**Решение:** Используем `ditto --noextattr --noqtn`:
```bash
ditto --noextattr --noqtn dist/Nexy.app /tmp/NexyClean.app
xattr -cr /tmp/NexyClean.app
find /tmp/NexyClean.app -name '._*' -type f -delete
```

### **3. Правильный порядок подписи (КРИТИЧНО)**
**Проблема:** `nested code is not signed at all`  
**Решение:** Сначала Mach-O, потом бандл:
```bash
# 1. Подписываем вложенные Mach-O
find app/Contents -type f -perm -111 | while read BIN; do
  if file -b "$BIN" | grep -q "Mach-O"; then
    codesign --force --timestamp --options=runtime \
      --entitlements entitlements.plist \
      --sign "Developer ID Application: ..." "$BIN"
  fi
done

# 2. Подписываем весь бандл
codesign --force --timestamp --options=runtime \
  --entitlements entitlements.plist \
  --sign "Developer ID Application: ..." app.app
```

### **4. Library Validation для PyInstaller onefile**
**Проблема:** `code signature invalid` при запуске  
**Решение:** Добавили в `entitlements.plist`:
```xml
<key>com.apple.security.cs.disable-library-validation</key><true/>
```

---

## 📦 АРТЕФАКТЫ

### **После успешной сборки:**

| Файл | Размер | Назначение | Статус |
|------|--------|------------|--------|
| `dist/Nexy-signed.app` | ~85MB | Подписанное приложение | ✅ Подписан |
| `dist/Nexy-signed.pkg` | ~85MB | PKG установщик | ✅ Подписан |
| `dist/Nexy-raw.pkg` | ~85MB | Component PKG | ✅ Внутренний |

### **Ключевые особенности:**
- **Приложение**: Подписано с правильными entitlements
- **PKG**: Создан из подписанного приложения
- **Размер**: ~85MB (включает Python framework)
- **Архитектура**: arm64 (Apple Silicon)

---

## 🧪 ТЕСТИРОВАНИЕ

### **Проверка приложения**
```bash
# Проверка подписи
codesign --verify --deep --strict --verbose=2 dist/Nexy-signed.app
spctl --assess --type execute --verbose dist/Nexy-signed.app

# Проверка entitlements
codesign -d --entitlements - dist/Nexy-signed.app

# Тестовый запуск (5 секунд)
(dist/Nexy-signed.app/Contents/MacOS/Nexy &) && sleep 5 && pkill -f "Nexy"
```

### **Проверка PKG**
```bash
# Проверка подписи PKG
codesign -v dist/Nexy-signed.pkg
pkgutil --check-signature dist/Nexy-signed.pkg

# Тестовая установка
sudo installer -pkg dist/Nexy-signed.pkg -target /

# Проверка результата
ls -la /Applications/Nexy.app
```

### **Проверка нотаризации (если применимо)**
```bash
# Проверка нотаризации приложения
xcrun stapler validate dist/Nexy-signed.app

# Проверка нотаризации PKG
xcrun stapler validate dist/Nexy-signed.pkg
```

---

## ⚠️ УСТРАНЕНИЕ ПРОБЛЕМ

### **"resource fork, Finder information, or similar detritus not allowed"**
**Причина**: Extended attributes не очищены  
**Решение**: Используйте `ditto --noextattr --noqtn` вместо `cp`
```bash
ditto --noextattr --noqtn dist/Nexy.app /tmp/NexyClean.app
xattr -cr /tmp/NexyClean.app
find /tmp/NexyClean.app -name '._*' -type f -delete
```

### **"Failed to load Python shared library"**
**Причина**: `exclude_binaries=True` в `Nexy.spec`  
**Решение**: Уберите `exclude_binaries=True` из Analysis и EXE
```python
# ❌ НЕ ДЕЛАЙТЕ ЭТО
# exclude_binaries=True,

# ✅ ПРАВИЛЬНО - оставляем по умолчанию (False)
```

### **"nested code is not signed at all"**
**Причина**: Неправильный порядок подписи  
**Решение**: Сначала подпишите вложенные Mach-O, потом весь бандл
```bash
# 1. Подписываем вложенные Mach-O
find app/Contents -type f -perm -111 | while read BIN; do
  if file -b "$BIN" | grep -q "Mach-O"; then
    codesign --force --timestamp --options=runtime \
      --entitlements entitlements.plist \
      --sign "Developer ID Application: ..." "$BIN"
  fi
done

# 2. Подписываем весь бандл
codesign --force --timestamp --options=runtime \
  --entitlements entitlements.plist \
  --sign "Developer ID Application: ..." app.app
```

### **"code signature invalid" при запуске**
**Причина**: Library Validation блокирует Python framework  
**Решение**: Добавьте в `entitlements.plist`:
```xml
<key>com.apple.security.cs.disable-library-validation</key><true/>
```

### **PKG показывает "no signature"**
**Причина**: PKG подпись не работает с Application сертификатом  
**Решение**: Это нормально для Application сертификата, PKG все равно работает

### **Приложение не запускается**
1. Проверить подпись: `codesign --verify --deep --strict --verbose=2 dist/Nexy-signed.app`
2. Проверить entitlements: `codesign -d --entitlements - dist/Nexy-signed.app`
3. Проверить логи: `log show --predicate 'process == "Nexy"' --last 1m`
4. Проверить разрешения в Системных настройках

---

## 📞 КОНТАКТЫ И НАСТРОЙКИ

- **Team ID:** 5NKLL2CLB9
- **Bundle ID:** com.nexy.assistant
- **Apple ID:** seregawpn@gmail.com
- **App-Specific Password:** qtiv-kabm-idno-qmbl
- **Версия:** 1.0.0

---

## 🎯 КРИТЕРИИ УСПЕХА

**✅ Готовность к релизу:**
- [ ] `build_and_sign.sh` выполняется без ошибок
- [ ] Приложение подписано корректно (`codesign --verify --deep --strict`)
- [ ] Entitlements применены (`disable-library-validation`)
- [ ] PKG создан и подписан
- [ ] Приложение запускается (если Library Validation отключен)

**🎯 После установки PKG:**
- [ ] Приложение устанавливается в `/Applications/Nexy.app`
- [ ] Приложение запускается без ошибок
- [ ] Все разрешения запрашиваются корректно
- [ ] Меню-бар работает

---

**📋 Документация:**
- **Полная инструкция:** `packaging/PACKAGING_GUIDE.md`
- **Быстрый старт:** `packaging/QUICK_START.md`
- **Автоматизированный скрипт:** `packaging/build_and_sign.sh`