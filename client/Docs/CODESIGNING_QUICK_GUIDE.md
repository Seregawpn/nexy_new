# 🔐 Быстрое руководство по подписи Nexy

**Дата:** 20 сентября 2025  
**Статус:** ✅ Готово к использованию

---

## 🚀 Быстрый старт

### 1. Настройка окружения
```bash
# Настройка переменных окружения
source packaging/setup_env.sh

# Проверка готовности
make doctor
```

### 2. Полный пайплайн подписи
```bash
# Один раз для полной сборки и подписи
make all
```

### 3. Проверка результата
```bash
# Проверка подписи
codesign --verify --deep --strict --verbose=2 dist/Nexy.app

# Проверка Gatekeeper
spctl --assess --type execute --verbose dist/Nexy.app
```

---

## 📋 Что нужно подготовить заранее

### Сертификаты (получить в Apple Developer Portal):
- ✅ **Developer ID Application** (для .app файлов)
- ✅ **Developer ID Installer** (для .pkg файлов)

### App-Specific Password:
- ✅ Создать в [Apple ID Settings](https://appleid.apple.com)
- ✅ Настроить notarytool профиль

### Переменные окружения:
```bash
export DEVELOPER_ID_APP="Developer ID Application: YOUR NAME (TEAM_ID)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: YOUR NAME (TEAM_ID)"
export APPLE_NOTARY_PROFILE="NexyNotary"
```

---

## 🔧 Команды по этапам

### Сборка и подпись:
```bash
make sanitize-dist      # Очистка dist/
make setup-staging      # Создание staging
make app               # Сборка PyInstaller
make restage-app-root  # Очистка xattrs
make sign-nested       # Подпись библиотек
make sign-app          # Подпись основного .app
make stage-to-dist     # Перенос в dist/
```

### Создание артефактов:
```bash
make pkg               # Создание PKG
make dmg               # Создание DMG
```

### Нотаризация:
```bash
make notarize-app      # Нотарификация .app
make notarize-pkg      # Нотарификация PKG
make notarize-dmg      # Нотарификация DMG
make staple-all        # Stapling билетов
```

### Проверка:
```bash
make verify            # Проверка всех подписей
```

---

## ⚠️ Частые ошибки и решения

### "resource fork, Finder information, or similar detritus not allowed"
```bash
xattr -cr dist/Nexy.app
xattr -dr com.apple.FinderInfo dist/Nexy.app
```

### "unsealed contents present in the bundle root"
```bash
rm -rf dist/Nexy.app/Nexy.app  # удалить вложенный .app
```

### "a sealed resource is missing or invalid"
```bash
make clean
make sanitize-dist setup-staging app restage-app-root sign-nested sign-app stage-to-dist
```

### "code signing failed with exit code 1"
```bash
# Проверка сертификата
security find-identity -v -p codesigning

# Проверка прав на файл
chmod +x dist/Nexy.app/Contents/MacOS/Nexy
```

---

## 🔍 Проверки подписи

### Базовые проверки:
```bash
# Подпись .app
codesign --verify --deep --strict --verbose=2 dist/Nexy.app

# Gatekeeper
spctl --assess --type execute --verbose dist/Nexy.app

# PKG
pkgutil --check-signature Nexy.pkg

# DMG
spctl -a -v Nexy.dmg
```

### Детальная информация:
```bash
# Информация о подписи
codesign -dv --verbose=4 dist/Nexy.app

# Entitlements
codesign -d --entitlements - dist/Nexy.app

# Проверка нотаризации
spctl -a -v --type install dist/Nexy.app
```

---

## 📚 Дополнительная информация

- **Полное руководство:** `Docs/PACKAGING_PLAN.md` (раздел 2)
- **Чек-лист:** `Docs/FINAL_CHECKLIST.md`
- **Настройка окружения:** `packaging/setup_env.sh`

---

## 🆘 Если что-то не работает

1. **Проверьте переменные окружения:**
   ```bash
   echo $DEVELOPER_ID_APP
   echo $DEVELOPER_ID_INSTALLER
   echo $APPLE_NOTARY_PROFILE
   ```

2. **Проверьте сертификаты:**
   ```bash
   security find-identity -v -p codesigning
   ```

3. **Проверьте готовность системы:**
   ```bash
   make doctor
   ```

4. **Очистите и пересоберите:**
   ```bash
   make clean
   make all
   ```

---

**💡 Совет:** Используйте `make all` для полного пайплайна - это самый надежный способ получить правильно подписанное приложение.
