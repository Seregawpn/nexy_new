# ⚡ QUICK START - Быстрая упаковка Nexy AI Assistant

> **Обновлено:** 24 сентября 2025 | **Статус:** Протестировано

## 🚀 Автоматическая упаковка (РЕКОМЕНДУЕТСЯ)

```bash
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
./packaging/build_and_sign.sh
```

## 🔧 Ручная упаковка (ПОШАГОВО)

### 1. Очистка и сборка
```bash
cd /Users/sergiyzasorin/Desktop/Development/Nexy/client
rm -rf dist/ build/ *.pyc __pycache__/
python3 -m PyInstaller packaging/Nexy.spec --noconfirm --clean
```

### 2. Создание чистой копии (КРИТИЧНО!)
```bash
# Создаем чистую копию БЕЗ extended attributes
ditto --noextattr --noqtn dist/Nexy.app /tmp/NexyCleanFinal.app
xattr -cr /tmp/NexyCleanFinal.app
find /tmp/NexyCleanFinal.app -name '._*' -delete
```

### 3. Подпись приложения (ПРАВИЛЬНЫЙ ПОРЯДОК!)
```bash
IDENTITY="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
ENTITLEMENTS="packaging/entitlements.plist"
APP="/tmp/NexyCleanFinal.app"

# Удаляем старые подписи
codesign --remove-signature "$APP" 2>/dev/null || true
find "$APP/Contents" -type f -perm +111 -exec codesign --remove-signature {} \; 2>/dev/null || true

# Подписываем вложенные Mach-O (СНАЧАЛА!)
while IFS= read -r -d '' BIN; do
  if file -b "$BIN" | grep -q "Mach-O"; then
    codesign --force --timestamp --options=runtime \
      --entitlements "$ENTITLEMENTS" \
      --sign "$IDENTITY" "$BIN"
  fi
done < <(find "$APP/Contents/Frameworks" "$APP/Contents/MacOS" -type f -perm +111 -print0 2>/dev/null)

# Подписываем весь бандл (ПОТОМ!)
codesign --force --timestamp --options=runtime \
  --entitlements "$ENTITLEMENTS" \
  --sign "$IDENTITY" "$APP"
```

### 4. Нотаризация приложения
```bash
# Создаем ZIP для нотаризации
ditto -c -k --noextattr --noqtn "$APP" dist/Nexy-app.zip

# Отправляем на нотаризацию
xcrun notarytool submit dist/Nexy-app.zip \
  --keychain-profile "nexy-notary" \
  --apple-id "seregawpn@gmail.com" \
  --wait

# Прикрепляем печать
xcrun stapler staple "$APP"
```

### 5. Создание PKG
```bash
# Создаем component PKG
mkdir -p /tmp/nexy_pkg_clean
ditto --noextattr --noqtn "$APP" /tmp/nexy_pkg_clean/Nexy.app

pkgbuild --root /tmp/nexy_pkg_clean \
  --identifier "com.nexy.assistant" \
  --version "1.0.0" \
  --install-location /Applications \
  dist/Nexy-raw.pkg

# Создаем distribution PKG
productbuild --package-path dist \
  --distribution packaging/distribution.xml \
  dist/Nexy-distribution.pkg

# Подписываем PKG (ПРАВИЛЬНЫЙ СЕРТИФИКАТ!)
INSTALLER_IDENTITY="Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)"
productsign --sign "$INSTALLER_IDENTITY" \
  dist/Nexy-distribution.pkg \
  dist/Nexy-signed.pkg
```

### 6. Нотаризация PKG
```bash
# Отправляем PKG на нотаризацию
xcrun notarytool submit dist/Nexy-signed.pkg \
  --keychain-profile "nexy-notary" \
  --apple-id "seregawpn@gmail.com" \
  --wait

# Прикрепляем печать
xcrun stapler staple dist/Nexy-signed.pkg
```

### 7. Финальная проверка
```bash
echo "=== ПРОВЕРКА ПРИЛОЖЕНИЯ ==="
codesign --verify --deep --strict --verbose=2 "$APP"
xcrun stapler validate "$APP"

echo "=== ПРОВЕРКА PKG ==="
pkgutil --check-signature dist/Nexy-signed.pkg
xcrun stapler validate dist/Nexy-signed.pkg

echo "✅ ВСЕ ГОТОВО!"
echo "📦 Файлы:"
echo "   • Приложение: $APP"
echo "   • PKG: dist/Nexy-signed.pkg"
```

## 🚨 КРИТИЧЕСКИЕ МОМЕНТЫ

### ❌ НЕ ДЕЛАЙТЕ ЭТО:
- `exclude_binaries=True` в Nexy.spec
- `cp` вместо `ditto --noextattr --noqtn`
- Подпись бандла до подписи вложенных Mach-O
- `codesign` для PKG (используйте `productsign`)

### ✅ ОБЯЗАТЕЛЬНО:
- `ditto --noextattr --noqtn` для копирования
- Сначала Mach-O, потом бандл
- `productsign` с "Developer ID Installer" для PKG
- `com.apple.security.cs.disable-library-validation` в entitlements

## 🔍 Проверка результата

```bash
# Проверяем приложение
codesign --verify --deep --strict --verbose=2 app.app
xcrun stapler validate app.app

# Проверяем PKG
pkgutil --check-signature pkg.pkg
xcrun stapler validate pkg.pkg
```

## 📞 Если что-то не работает

1. **"resource fork, Finder information, or similar detritus not allowed"**
   → Используйте `ditto --noextattr --noqtn` + `xattr -cr`

2. **"Failed to load Python shared library"**
   → Уберите `exclude_binaries=True` из Nexy.spec

3. **"nested code is not signed at all"**
   → Сначала подпишите вложенные Mach-O, потом бандл

4. **PKG не проходит нотаризацию**
   → Используйте `productsign` с "Developer ID Installer" сертификатом

---

**📚 Подробная инструкция:** `packaging/PACKAGING_GUIDE.md`  
**🔧 Автоматизированный скрипт:** `packaging/build_and_sign.sh`