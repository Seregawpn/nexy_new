# 🔐 Быстрое руководство по подписи Nexy

**Дата:** 20 сентября 2025  
**Статус:** ✅ Готово к использованию

---

## 🚀 Быстрый старт

### 1. Настройка окружения
```bash
# Переход в директорию сборки
cd packaging/

# Настройка переменных окружения
source setup_env.sh

# Проверка готовности
make doctor
```

### 2. Полный пайплайн подписи
```bash
# Полный пайплайн (включая нотаризацию)
make all

# Быстрая сборка БЕЗ нотаризации (для разработки)
make build-only

# Нотаризация уже созданных артефактов
make notarize-all
```

### 3. Проверка результата
```bash
# Проверка подписи
codesign --verify --deep --strict --verbose=2 dist/Nexy.app

# Проверка Gatekeeper
spctl --assess --type execute --verbose dist/Nexy.app

# Проверка PKG/DMG
spctl -a -v artifacts/Nexy-2.5.0.pkg
spctl -a -v artifacts/Nexy-2.5.0.dmg
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
make pkg               # Создание PKG (с подписью)
make dmg               # Создание DMG (с подписью)
```

### Нотаризация:
```bash
make notarize-app      # Нотарификация .app
make notarize-pkg      # Нотарификация PKG
make notarize-dmg      # Нотарификация DMG
make notarize-all      # Нотарификация всех артефактов
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
   cd packaging/
   make clean
   make all
   ```

---

**💡 Советы по использованию:**

- **Для разработки:** `make build-only` - быстрая сборка без нотаризации
- **Для релиза:** `make all` - полный пайплайн с нотаризацией
- **Для нотаризации:** `make notarize-all` - нотаризация уже созданных артефактов
- **PKG и DMG** теперь автоматически подписываются при создании
