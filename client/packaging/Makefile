# Makefile для сборки и упаковки Nexy
# Версия: 3.2.0 - Staging Pipeline

# Переменные
APP_NAME ?= Nexy
BUNDLE_ID ?= com.nexy.assistant
VERSION ?= 2.5.0
BUILD ?= 20500

DEVELOPER_ID_APP ?= Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)
DEVELOPER_ID_INSTALLER ?= Developer ID Installer: Sergiy Zasorin (5NKLL2CLB9)
APPLE_NOTARY_PROFILE ?= NexyNotary

SPEC ?= Nexy.spec
STAGE ?= /tmp/nexy-stage
STAGE_APP := $(STAGE)/$(APP_NAME).app
DIST_APP := ../dist/$(APP_NAME).app
PKG := artifacts/$(APP_NAME)-$(VERSION).pkg
DMG := artifacts/$(APP_NAME)-$(VERSION).dmg

.PHONY: all doctor sanitize-dist setup-staging app restage-app-root check-xattrs sign-nested sign-app stage-to-dist pkg dmg notarize-app notarize-pkg notarize-dmg staple-all verify verify-dest clean

all: doctor sanitize-dist setup-staging app restage-app-root check-xattrs sign-nested sign-app stage-to-dist pkg dmg notarize-app notarize-pkg notarize-dmg staple-all verify verify-dest

doctor:
	@echo "🔍 Проверка готовности к сборке..."
	@command -v python3 >/dev/null 2>&1 || { echo "❌ python3 не найден"; exit 1; }
	@python3 -m PyInstaller --version >/dev/null 2>&1 || { echo "❌ pyinstaller не найден. Установите: pip install pyinstaller"; exit 1; }
	@command -v codesign >/dev/null 2>&1 || { echo "❌ codesign не найден. Установите Xcode Command Line Tools"; exit 1; }
	@command -v productbuild >/dev/null 2>&1 || { echo "❌ productbuild не найден. Установите Xcode Command Line Tools"; exit 1; }
	@command -v xcrun >/dev/null 2>&1 || { echo "❌ xcrun не найден. Установите Xcode Command Line Tools"; exit 1; }
	@echo "✅ Все инструменты найдены"

sanitize-dist:
	@echo "🧹 Очистка dist/ директории..."
	@rm -rf ../dist
	@mkdir -p ../dist
	@echo "✅ dist/ директория очищена"

setup-staging:
	@echo "🏗️ Настройка staging директории..."
	@mkdir -p "$(STAGE)"
	@echo "✅ Staging директория: $(STAGE)"

app:
	@echo "🔨 Сборка приложения в staging..."
	cd .. && python3 -m PyInstaller --clean -y packaging/$(SPEC)
	@if [ -d "$(DIST_APP)" ]; then \
		echo "✅ $(APP_NAME).app создан в $(DIST_APP)"; \
		echo "📦 Переносим в staging: $(STAGE_APP)"; \
		cp -R "$(DIST_APP)" "$(STAGE_APP)"; \
		echo "✅ $(APP_NAME).app перенесен в staging"; \
	else \
		echo "❌ Ошибка при создании .app - файл не найден в $(DIST_APP)"; \
		exit 1; \
	fi

restage-app-root:
	@echo "🔄 Рестейджинг корня .app bundle..."
	@ditto --norsrc --noqtn "$(STAGE_APP)" "$(STAGE_APP).clean"
	@rm -rf "$(STAGE_APP)"
	@mv "$(STAGE_APP).clean" "$(STAGE_APP)"
	@echo "✅ .app bundle рестейджен"

check-xattrs:
	@echo "→ Checking extended attributes in $(STAGE_APP)"
	@! find "$(STAGE_APP)" -type f -print0 \
	 | xargs -0 xattr -l 2>/dev/null \
	 | grep -E "com\.apple\.(FinderInfo|ResourceFork|quarantine)" \
	 && echo "✅ No forbidden xattrs on files" \
	 || (echo "❌ Forbidden xattrs on files — run: xattr -rc $(STAGE_APP)"; exit 1)

# Дополнительно логируем каталоги (но не падаем)
log-xattrs-dirs:
	@echo "→ scan xattrs (dirs, non-fatal):"
	@find "$(STAGE_APP)" -type d -print0 \
	 | xargs -0 xattr -l 2>/dev/null | sed -n '1,100p' || true

# 1) Очистка xattrs и подпись внутренних бинарников/расширений
sign-nested:
	@echo "🔐 Подпись внутренних компонентов в staging..."
	xattr -rc "$(STAGE_APP)"
	xattr -dr com.apple.quarantine "$(STAGE_APP)" || true
	# dylib/so/исполняемые — подпишем по одному
	find "$(STAGE_APP)" -type f \( -name "*.dylib" -o -name "*.so" -o -perm -111 \) -print0 | xargs -0 -I{} codesign --force --timestamp \
	  --entitlements entitlements.plist \
	  --sign "$(DEVELOPER_ID_APP)" "{}" || true

# 2) Подпись самого .app (БЕЗ --deep)
sign-app:
	@echo "🔐 Подпись приложения в staging..."
	codesign --force --options runtime --timestamp \
	  --entitlements entitlements.plist \
	  --sign "$(DEVELOPER_ID_APP)" "$(STAGE_APP)"
	codesign --verify --deep --strict --verbose=2 "$(STAGE_APP)"
	- spctl -a -v "$(STAGE_APP)"

# Перенос подписанного .app в dist/ без xattrs
stage-to-dist:
	@echo "📦 Перенос подписанного .app в dist/..."
	@echo "🧹 Очистка xattrs в staging перед переносом..."
	@xattr -cr "$(STAGE_APP)"
	@xattr -dr com.apple.FinderInfo "$(STAGE_APP)" 2>/dev/null || true
	@ditto --norsrc --noqtn "$(STAGE_APP)" "$(DIST_APP)"
	@echo "✅ Подписанный .app перенесен в dist/"

# PKG — в /Applications (PKG = админ-установка; без-root — через DMG)
pkg:
	@echo "📦 Создание PKG..."
	productbuild --component "$(DIST_APP)" /Applications \
	  --sign "$(DEVELOPER_ID_INSTALLER)" "$(PKG)"
	@echo "✅ PKG built: $(PKG)"

dmg:
	@echo "💿 Создание DMG..."
	bash make_dmg.sh "$(DIST_APP)" "$(DMG)"
	@echo "✅ DMG built: $(DMG)"

notarize-app:
	@echo "📋 Нотарификация .app..."
	xcrun notarytool submit "$(DIST_APP)" --keychain-profile "$(APPLE_NOTARY_PROFILE)" --wait

notarize-pkg:
	@echo "📋 Нотарификация .pkg..."
	xcrun notarytool submit "$(PKG)" --keychain-profile "$(APPLE_NOTARY_PROFILE)" --wait

notarize-dmg:
	@echo "📋 Нотарификация .dmg..."
	xcrun notarytool submit "$(DMG)" --keychain-profile "$(APPLE_NOTARY_PROFILE)" --wait

staple-all:
	@echo "📌 Staple всех артефактов..."
	- xcrun stapler staple "$(DIST_APP)"
	- xcrun stapler staple "$(PKG)"
	- xcrun stapler staple "$(DMG)"

verify:
	@echo "🔍 Проверка подписей..."
	codesign --verify --deep --strict --verbose=2 "$(DIST_APP)"
	pkgutil --check-signature "$(PKG)"
	- spctl -a -v "$(DIST_APP)"
	- spctl -a -v "$(PKG)"
	- spctl -a -v "$(DMG)"

verify-dest:
	@echo "🔍 Проверка назначения PKG..."
	bash verify_pkg_destination.sh "$(PKG)"

clean:
	@echo "🧹 Очистка..."
	rm -rf build dist artifacts/*.pkg artifacts/*.dmg
	@if [ -n "$(STAGE)" ] && [ -d "$(STAGE)" ]; then \
		echo "🧹 Очистка staging: $(STAGE)"; \
		rm -rf "$(STAGE)"; \
	fi