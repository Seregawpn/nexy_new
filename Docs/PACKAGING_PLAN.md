# 📦 План упаковки Nexy (macOS PKG) — шаблон повторяемого процесса

Дата: 19 сентября 2025
Статус: Готов к применению (итеративный чек‑лист)

Цель: «Кнопочный» процесс сборки подписанного и нотарифицированного PKG с автообновлениями (Sparkle), который можно быстро повторять на каждой версии.

---

## 0) Предпосылки и переменные окружения

Требуется:
- Xcode Command Line Tools: `xcode-select --install`
- Доступ к Apple Developer (Developer ID Application/Installer)
- Sparkle 2 (через Homebrew) — фреймворк уже обнаружен в проекте

Хранение секретов (рекомендуемые переменные):
- `DEVELOPER_ID_APP="Developer ID Application: YOUR NAME (TEAMID)"`
- `DEVELOPER_ID_INSTALLER="Developer ID Installer: YOUR NAME (TEAMID)"`
- `TEAM_ID="5NKLL2CLB9"` (пример)
- `BUNDLE_ID="com.nexy.assistant"`
- `APP_NAME="Nexy"`
- `APP_VERSION="2.5.0"` / `APP_BUILD="20500"` (CFBundleVersion)
- `SPARKLE_FEED_URL="https://api.yourdomain.com/updates/appcast.xml"`
- `APPLE_NOTARY_PROFILE="NexyNotary"` (сохранённый профиль notarytool)

Создать профиль notarytool (однократно):
```
xcrun notarytool store-credentials "$APPLE_NOTARY_PROFILE" \
  --apple-id "APPLE_ID_EMAIL" \
  --team-id "$TEAM_ID" \
  --password "APP_SPECIFIC_PASSWORD"
```

---

## 1) Подготовка .app (PyInstaller)

1.1 Info.plist (обязательные ключи):
- `CFBundleIdentifier = $BUNDLE_ID`
- `CFBundleShortVersionString = $APP_VERSION`
- `CFBundleVersion = $APP_BUILD`
- `SUFeedURL = $SPARKLE_FEED_URL` (Sparkle)
- `LSBackgroundOnly = 1` (для menubar‑приложений на rumps — опционально)
- Usage Descriptions (микрофон/скрин/камера/уведомления):
  - `NSMicrophoneUsageDescription`
  - `NSCameraUsageDescription` (если требуется)
  - `NSScreenCaptureUsageDescription`
  - `NSUserNotificationUsageDescription` (или UNNotifications)

1.2 Entitlements (entitlements.plist):
- `com.apple.security.app-sandbox` = false (Developer ID, не Mac App Store)
- `com.apple.security.cs.disable-library-validation` = true (если требуется Sparkle/плагины)
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
        # Пример: включить Sparkle.framework, иконки, ресурсы
        # ('path/to/Sparkle.framework', 'Nexy.app/Contents/Frameworks/Sparkle.framework'),
    ],
    hiddenimports=['rumps'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

app = BUNDLE(pyz,
             a.scripts,
             name='Nexy.app',
             icon=None,
             bundle_identifier='com.nexy.assistant',
             info_plist={
                 'CFBundleName': 'Nexy',
                 'CFBundleShortVersionString': '2.5.0',
                 'CFBundleVersion': '20500',
                 'LSMinimumSystemVersion': '11.0',
                 'LSBackgroundOnly': True,
                 'SUFeedURL': 'https://api.yourdomain.com/updates/appcast.xml',
             },
             argv_emulation=False,
             target_arch=None)
```
Сборка: `pyinstaller --clean -y Nexy.spec` → `dist/Nexy.app`

Проверка локального запуска .app: OK.

---

## 2) Подпись .app (codesign, hardened runtime)

2.1 Подписать вложенные фреймворки (Sparkle.framework и пр.):
```
codesign --force --options runtime --timestamp \
  --sign "$DEVELOPER_ID_APP" \
  dist/Nexy.app/Contents/Frameworks/Sparkle.framework
```

2.2 Подписать .app c entitlements:
```
codesign --force --deep --options runtime --timestamp \
  --entitlements entitlements.plist \
  --sign "$DEVELOPER_ID_APP" dist/Nexy.app

codesign --verify --deep --strict --verbose=2 dist/Nexy.app
spctl --assess --type execute --verbose dist/Nexy.app
```

---

## 3) Сборка и подпись PKG

3.1 Сборка PKG:
```
productbuild \
  --component dist/Nexy.app /Applications \
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

## 5) Sparkle AppCast (обновления)

5.1 Готовим `appcast.xml` (пример записи):
```
<item>
  <title>Version 2.5.0</title>
  <sparkle:releaseNotesLink>https://api.yourdomain.com/updates/notes/2.5.0.html</sparkle:releaseNotesLink>
  <pubDate>Thu, 19 Sep 2025 18:00:00 +0000</pubDate>
  <enclosure url="https://api.yourdomain.com/updates/Nexy-2.5.0.pkg"
             sparkle:version="20500"
             length="12345678"
             type="application/octet-stream" />
</item>
```
Для Sparkle 2 рекомендуется использовать `generate_appcast` (включая EdDSA‑подпись). Если используете подпись, добавьте `sparkle:edSignature` в enclosure.

5.2 Публикация:
- Разместить `appcast.xml` и `Nexy-$APP_VERSION.pkg` по HTTPS (например, Azure Static Site/App Service).
- Проверить доступность: `https://api.yourdomain.com/updates/appcast.xml`.

5.3 Клиент:
- Убедиться, что `SUFeedURL`/конфиг указывает на правильный appcast URL.
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
	codesign --force --options runtime --timestamp \
	  --sign "$(DEVELOPER_ID_APP)" dist/Nexy.app/Contents/Frameworks/Sparkle.framework
	codesign --force --deep --options runtime --timestamp \
	  --entitlements entitlements.plist \
	  --sign "$(DEVELOPER_ID_APP)" dist/Nexy.app
	codesign --verify --deep --strict --verbose=2 dist/Nexy.app

pkg:
	productbuild --component dist/Nexy.app /Applications \
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
- [ ] SUFeedURL указывает на актуальный appcast
- [ ] Entitlements соответствуют требованиям (Mic/Screen/Notifications/Accessibility)
- [ ] Sparkle.framework включён и подписан
- [ ] .app подписан (codesign verify OK)
- [ ] PKG подписан и нотарифицирован, stapled
- [ ] AppCast доступен по HTTPS, запись корректна
- [ ] Автообновление проверено на клиенте (Sparkle)

---

## 8) Типичные проблемы и решения

- Ошибка notarization: проверьте, что используете Developer ID, hardened runtime, timestamp, и что PKG подписан Installer‑сертификатом.
- Gatekeeper ругается: повторно проверьте stapler и целостность подписи.
- Sparkle не видит обновления: проверьте SUFeedURL и доступность appcast.xml/PKG; корректность версии/даты/подписи.
- Фреймворки/библиотеки: убедитесь, что все вложенные .dylib/.framework подписаны до подписи .app.

---

## 9) Где хранить скрипты/артефакты

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
