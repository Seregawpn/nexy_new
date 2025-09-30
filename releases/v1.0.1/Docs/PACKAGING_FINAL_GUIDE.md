# PACKAGING FINAL GUIDE — Финальная инструкция по упаковке, подписи и нотаризации Nexy

Обновлено: 29.09.2025

Цель: единая, точная и минимальная инструкция. Один скрипт выполнит сборку, подпись, нотаризацию, создание DMG и PKG (строгая установка в /Applications) и оставит в dist/ только нужные артефакты.

—

1) Требования и подготовка (один раз)
- Установите инструменты Xcode: `xcode-select --install`
- Проверьте сертификаты в Keychain:
  - Developer ID Application (для подписи .app)
  - Developer ID Installer (для подписи PKG)
- Сохраните профиль нотаризации Apple:
  - `xcrun notarytool store-credentials nexy-notary --apple-id <APPLE_ID> --team-id <TEAM_ID> --password <APP_SPECIFIC_PASSWORD>`

2) Единая команда упаковки
- Запустите из корня проекта: `./packaging/build_final.sh`
- Скрипт выполнит:
  - сборку .app через PyInstaller;
  - очистку extended attributes;
  - подпись вложенных Mach‑O и всего .app (Hardened Runtime + entitlements);
  - нотаризацию .app и stapler;
  - создание DMG (drag‑and‑drop);
  - создание component PKG с install-location `/Applications`;
  - сборку distribution PKG (домен установки: только system);
  - подпись PKG (Developer ID Installer) и нотаризацию PKG;
  - финальные проверки и очистку мусора.

3) Результат
- В `dist/` останутся строго два файла:
- `Nexy.pkg` — подписанный и пронотаризованный установщик в `/Applications`.
  - `Nexy.dmg` — образ для drag-and-drop установки.

4) Установка PKG (строго /Applications)
- Очистите прежние следы при необходимости:
  - `sudo pkgutil --forget com.nexy.assistant.pkg || true`
  - `rm -rf ~/Applications/Nexy.app /Applications/Nexy.app`
- Установка:
- GUI: двойной клик по `dist/Nexy.pkg`
- CLI: `sudo installer -pkg dist/Nexy.pkg -target /`
- Проверка: `ls -la /Applications/Nexy.app`

5) Проверка подписи и печатей
- PKG:
  - `pkgutil --check-signature dist/Nexy.pkg`
  - `xcrun stapler validate dist/Nexy.pkg`
- Приложение (дополнительно):
  - `codesign --verify --deep --strict --verbose=2 /Applications/Nexy.app`

6) Критические требования (уже учтены)
- PKG: `--install-location /Applications`
- distribution.xml: `<domains enable_localSystem="true" enable_currentUserHome="false"/>`
- PKG подписывается сертификатом Developer ID Installer
- Hardened Runtime + `com.apple.security.cs.disable-library-validation`
- Порядок подписи: вложенные Mach‑O → весь .app
- Копирование только через `ditto --noextattr --noqtn` + `xattr -cr`
- В PyInstaller не использовать `exclude_binaries=True`
- VoiceOver разрешения: включены в entitlements.plist для управления VoiceOver

7) Сброс TCC (по желанию)
- `./packaging/reset_permissions.sh` — сбросить разрешения (микрофон, экран, VoiceOver и т.д.)

8) Диагностика
- Куда ставит PKG:
  - `pkgutil --expand dist/Nexy.pkg /tmp/nexy_check`
  - `grep -R "install-location" /tmp/nexy_check` → `/Applications`
- Домен установки:
  - `packaging/distribution.xml` → `<domains enable_localSystem="true" enable_currentUserHome="false"/>`

9) Частые проблемы и решения
- «resource fork, Finder information, or similar detritus not allowed» → `ditto --noextattr --noqtn`, `xattr -cr` (уже в скрипте)
- «Failed to load Python shared library» → не используйте `exclude_binaries=True`
- «nested code is not signed at all» → подпишите вложенные Mach‑O до подписи бандла
- PKG «no signature» → подписывайте PKG сертификатом Developer ID Installer

—

Контрольный список успеха
- [ ] `./packaging/build_final.sh` отработал без ошибок
- [ ] В `dist/` только `Nexy.pkg` и `Nexy.dmg`
- [ ] `pkgutil --check-signature dist/Nexy.pkg` — OK
- [ ] `xcrun stapler validate dist/Nexy.pkg` — OK
- [ ] Установка через PKG помещает приложение в `/Applications/Nexy.app`

Это единственная актуальная инструкция по упаковке Nexy.
