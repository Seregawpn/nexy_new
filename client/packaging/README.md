# 📦 Packaging Directory - Nexy AI Assistant

**Дата:** 20 сентября 2025  
**Версия:** 3.4.0 - Local Build

---

## 🎯 Назначение

Эта директория содержит все файлы для сборки, подписи и упаковки Nexy AI Assistant.

---

## 📁 Структура

```
packaging/
├── README.md                    # Этот файл
├── Makefile                     # Основной Makefile для сборки
├── setup_env.sh                 # Скрипт настройки переменных окружения
├── Nexy.spec                    # PyInstaller spec для сборки
├── entitlements.plist           # Entitlements для подписи
├── make_dmg.sh                  # Скрипт создания DMG
├── verify_pkg_destination.sh    # Скрипт проверки PKG
├── artifacts/                   # Готовые артефакты (.pkg, .dmg)
├── dist/                        # Собранные .app файлы
├── build/                       # Временные файлы PyInstaller
└── .gitignore                   # Исключения для git
```

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

### 2. Сборка
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

## 🔧 Основные команды

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
make doctor            # Проверка готовности системы
```

### Очистка:
```bash
make clean             # Очистка всех артефактов
make sanitize-dist     # Очистка только dist/
```

---

## 📋 Переменные окружения

Обязательные переменные:
```bash
export DEVELOPER_ID_APP="Developer ID Application: YOUR NAME (TEAM_ID)"
export DEVELOPER_ID_INSTALLER="Developer ID Installer: YOUR NAME (TEAM_ID)"
export APPLE_NOTARY_PROFILE="NexyNotary"
```

Или используйте готовый скрипт:
```bash
source setup_env.sh
```

---

## 🔍 Проверки

### Базовые проверки:
```bash
# Подпись .app
codesign --verify --deep --strict --verbose=2 dist/Nexy.app

# Gatekeeper
spctl --assess --type execute --verbose dist/Nexy.app

# PKG
pkgutil --check-signature artifacts/Nexy-2.5.0.pkg

# DMG
spctl -a -v artifacts/Nexy-2.5.0.dmg
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

## 🆘 Получение помощи

1. **Проверьте переменные окружения:**
   ```bash
   echo $DEVELOPER_ID_APP
   echo $DEVELOPER_ID_INSTALLER
   echo $APPLE_NOTARY_PROFILE
   ```

2. **Проверьте готовность системы:**
   ```bash
   make doctor
   ```

3. **Очистите и пересоберите:**
   ```bash
   make clean
   make all
   ```

4. **Документация:**
   - **Быстрое руководство:** `../Docs/CODESIGNING_QUICK_GUIDE.md`
   - **Полное руководство:** `../Docs/PACKAGING_PLAN.md` (раздел 2)
   - **Troubleshooting:** `../Docs/TROUBLESHOOTING_CODESIGNING.md`

---

## 💡 Советы

- **Для разработки:** `make build-only` - быстрая сборка без нотаризации
- **Для релиза:** `make all` - полный пайплайн с нотаризацией
- **PKG и DMG** автоматически подписываются при создании
- **Все артефакты** создаются в локальной директории `packaging/`

---

**🎯 Цель:** Получить готовые к распространению файлы `artifacts/Nexy-2.5.0.pkg` и `artifacts/Nexy-2.5.0.dmg`
