# 🚀 БЫСТРАЯ СПРАВКА - УПАКОВКА NEXY

> **Обновлено:** 22.09.2025 | **Версия:** 1.71.0

---

## ⚡ БЫСТРЫЕ КОМАНДЫ

### **Полная сборка (одна команда)**
```bash
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
./packaging/build_all.sh
```

### **Проверка артефактов**
```bash
./packaging/verify_all.sh
```

### **Тестовая установка**
```bash
sudo installer -pkg dist/Nexy-signed.pkg -target /
```

---

## 📋 КРИТИЧЕСКИЕ НАСТРОЙКИ

### **1. Nexy.spec (ОБЯЗАТЕЛЬНО)**
```python
# PIL для иконок
hiddenimports=[
    'PIL', 'PIL.Image', 'PIL.ImageDraw', 'Pillow',
    # ... остальные
],

# Пути для интеграций
pathex=[str(client_dir), str(client_dir / 'integration')],

# НЕ подписывать автоматически
codesign_identity=None,
entitlements_file=None,
```

### **2. Подпись (БЕЗ Hardened Runtime)**
```bash
# ПРАВИЛЬНО:
codesign --force --timestamp \
  --entitlements packaging/entitlements.plist \
  --sign "Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)" \
  app.app

# НЕПРАВИЛЬНО (НЕ ДОБАВЛЯТЬ --options runtime!)
```

### **3. Сертификаты**
```bash
# Проверка наличия
security find-identity -p codesigning -v

# Должны быть:
# Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)
# Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)
```

### **4. Notarytool профиль**
```bash
# Настройка (один раз)
xcrun notarytool store-credentials nexy-notary \
  --apple-id seregawpn@gmail.com \
  --team-id 5NKLL2CLB9 \
  --password qtiv-kabm-idno-qmbl

# Проверка
xcrun notarytool history --keychain-profile nexy-notary
```

---

## 🎯 ФИНАЛЬНЫЕ АРТЕФАКТЫ

После выполнения `build_all.sh`:

| Файл | Назначение | Статус |
|------|------------|--------|
| `dist/Nexy-signed.pkg` | Первичная установка | ✅ Подписан |
| `dist/Nexy.dmg` | Автообновления | ✅ Нотаризован |
| `dist/manifest.json` | Манифест обновлений | ✅ С подписями |
| `dist/Nexy-final.app` | Готовое приложение | ✅ С иконками |

---

## ⚠️ ВАЖНЫЕ МОМЕНТЫ

### **❌ НЕ ДЕЛАТЬ:**
- НЕ использовать `--options runtime` (конфликт с PyInstaller)
- НЕ забывать PIL подмодули в hiddenimports
- НЕ собирать в основной папке (используйте /tmp)

### **✅ ОБЯЗАТЕЛЬНО:**
- Собирать в временной папке `/tmp`
- Добавлять `PIL.Image`, `PIL.ImageDraw` в spec
- Подписывать БЕЗ Hardened Runtime
- Тестировать иконки в меню-баре

---

## 🧪 БЫСТРОЕ ТЕСТИРОВАНИЕ

### **Тест иконок (30 сек)**
```bash
# Запуск приложения на 30 секунд
dist/Nexy-final.app/Contents/MacOS/Nexy &
APP_PID=$!
sleep 30
kill $APP_PID

# Должна появиться цветная иконка в меню-баре!
```

### **Проверка PKG**
```bash
# Информация о PKG
installer -pkg dist/Nexy-signed.pkg -dominfo

# Подпись PKG
pkgutil --check-signature dist/Nexy-signed.pkg
```

### **Проверка DMG**
```bash
# Нотаризация DMG
xcrun stapler validate dist/Nexy.dmg

# Монтирование DMG
open dist/Nexy.dmg
```

---

## 🔧 УСТРАНЕНИЕ ПРОБЛЕМ

### **Иконки не отображаются**
```bash
# 1. Проверить PIL в spec
grep -n "PIL.Image" packaging/Nexy.spec

# 2. Пересобрать с исправлениями
rm -rf build/ dist/
./packaging/build_all.sh

# 3. Тест PIL в приложении
python3 -c "
import sys
sys.path.append('dist/Nexy.app/Contents/MacOS')
from PIL import Image, ImageDraw
print('PIL работает!')
"
```

### **Приложение не запускается**
```bash
# Проверка подписи
codesign --verify --strict --deep dist/Nexy-final.app

# Проверка Gatekeeper
spctl --assess --type exec --verbose dist/Nexy-final.app

# Логи системы
log show --predicate 'process == "Nexy"' --last 1m
```

### **PKG не устанавливается**
```bash
# Проверка подписи PKG
pkgutil --check-signature dist/Nexy-signed.pkg

# Установка с подробным выводом
sudo installer -pkg dist/Nexy-signed.pkg -target / -verbose
```

---

## 📞 КОНТАКТЫ

- **Team ID:** 5NKLL2CLB9
- **Bundle ID:** com.nexy.assistant
- **Apple ID:** seregawpn@gmail.com
- **App Password:** qtiv-kabm-idno-qmbl (требует ротации)

---

**🎯 Главное правило:** Всегда тестировать иконки в меню-баре после сборки!

