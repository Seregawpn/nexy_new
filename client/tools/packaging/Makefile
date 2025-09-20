# Makefile для автоматизированной сборки Nexy PKG
# Основан на PACKAGING_PLAN.md

# Переменные окружения (можно переопределить)
VERSION ?= 2.5.0
BUILD ?= 20500
APP_NAME = Nexy
BUNDLE_ID = com.nexy.assistant
TEAM_ID = 5NKLL2CLB9

# Пути
CLIENT_DIR = $(shell pwd)/..
PACKAGING_DIR = $(shell pwd)
BUILD_DIR = $(CLIENT_DIR)/build
DIST_DIR = $(CLIENT_DIR)/dist
APP_PATH = $(DIST_DIR)/$(APP_NAME).app
PKG_NAME = $(APP_NAME)-$(VERSION).pkg
SIGNED_PKG_NAME = $(APP_NAME)-$(VERSION)-signed.pkg

# Сертификаты (настроены)
DEVELOPER_ID_APP = "Developer ID Application: Sergiy Zasorin ($(TEAM_ID))"
DEVELOPER_ID_INSTALLER = "Developer ID Installer: Sergiy Zasorin ($(TEAM_ID))"
APPLE_NOTARY_PROFILE = "nexy-notary"

# Sparkle
SPARKLE_FRAMEWORK = /opt/homebrew/Caskroom/sparkle/2.7.1/Sparkle.framework

.PHONY: all clean app sign-app pkg sign-pkg notarize staple test-app help

# Основные цели
all: clean app sign-app pkg sign-pkg notarize staple
	@echo "✅ Полная сборка завершена: $(SIGNED_PKG_NAME)"

help:
	@echo "🔧 Доступные команды:"
	@echo "  all          - Полная сборка: app → подпись → pkg → нотаризация"
	@echo "  app          - Сборка .app с PyInstaller"
	@echo "  sign-app     - Подпись .app"
	@echo "  pkg          - Сборка .pkg"
	@echo "  sign-pkg     - Подпись .pkg"
	@echo "  notarize     - Нотаризация .pkg"
	@echo "  staple       - Степлинг .pkg"
	@echo "  test-app     - Тестовый запуск .app"
	@echo "  clean        - Очистка временных файлов"
	@echo ""
	@echo "📋 Переменные:"
	@echo "  VERSION=$(VERSION)"
	@echo "  BUILD=$(BUILD)"
	@echo "  TEAM_ID=$(TEAM_ID)"

# Очистка
clean:
	@echo "🧹 Очистка временных файлов..."
	rm -rf $(BUILD_DIR) $(DIST_DIR)
	rm -f $(CLIENT_DIR)/*.pkg
	rm -f $(CLIENT_DIR)/*.dmg

# 1. Сборка .app
app: clean
	@echo "🔨 Сборка $(APP_NAME).app..."
	cd $(CLIENT_DIR) && python3 -m PyInstaller --clean -y $(PACKAGING_DIR)/Nexy.spec
	@if [ -d "$(APP_PATH)" ]; then \
		echo "✅ $(APP_NAME).app успешно создан"; \
	else \
		echo "❌ Ошибка при создании .app"; exit 1; \
	fi

# 2. Подпись .app
sign-app: app
	@echo "🔐 Подпись приложения..."
	@# Подписываем Sparkle Framework
	@if [ -d "$(APP_PATH)/Contents/Frameworks/Sparkle.framework" ]; then \
		echo "📝 Подпись Sparkle.framework..."; \
		codesign --force --options runtime --timestamp \
			--sign $(DEVELOPER_ID_APP) \
			"$(APP_PATH)/Contents/Frameworks/Sparkle.framework"; \
	fi
	@# Подписываем основное приложение
	@echo "📝 Подпись основного приложения..."
	@echo "🧹 Очистка extended attributes..."
	xattr -cr "$(APP_PATH)"
	codesign --force --options runtime --timestamp \
		--entitlements $(PACKAGING_DIR)/entitlements.plist \
		--sign $(DEVELOPER_ID_APP) "$(APP_PATH)"
	@# Проверяем подпись
	@echo "🔍 Проверка подписи..."
	codesign --verify --strict --verbose=2 "$(APP_PATH)"
	spctl --assess --type execute --verbose "$(APP_PATH)"
	@echo "✅ Приложение подписано успешно"

# 3. Тестовый запуск
test-app: sign-app
	@echo "🧪 Тестовый запуск приложения..."
	@echo "Запуск $(APP_PATH)..."
	open "$(APP_PATH)"
	@echo "⏱️ Подождите 5 секунд для проверки запуска..."
	sleep 5
	@echo "✅ Тест завершен. Проверьте, что приложение запустилось корректно"

# 4. Сборка PKG
pkg: sign-app
	@echo "📦 Сборка PKG..."
	productbuild \
		--component "$(APP_PATH)" /Applications \
		"$(CLIENT_DIR)/$(PKG_NAME)"
	@echo "✅ PKG создан: $(PKG_NAME)"

# 5. Подпись PKG
sign-pkg: pkg
	@echo "🔐 Подпись PKG..."
	productsign \
		--sign $(DEVELOPER_ID_INSTALLER) \
		"$(CLIENT_DIR)/$(PKG_NAME)" \
		"$(CLIENT_DIR)/$(SIGNED_PKG_NAME)"
	@# Проверка подписи PKG
	pkgutil --check-signature "$(CLIENT_DIR)/$(SIGNED_PKG_NAME)"
	@echo "✅ PKG подписан: $(SIGNED_PKG_NAME)"

# 6. Нотаризация
notarize: sign-pkg
	@echo "🌐 Отправка на нотаризацию..."
	@echo "⏳ Это может занять несколько минут..."
	xcrun notarytool submit "$(CLIENT_DIR)/$(SIGNED_PKG_NAME)" \
		--keychain-profile $(APPLE_NOTARY_PROFILE) \
		--wait
	@echo "✅ Нотаризация завершена"

# 7. Степлинг
staple: notarize
	@echo "📎 Степлинг PKG..."
	xcrun stapler staple "$(CLIENT_DIR)/$(SIGNED_PKG_NAME)"
	@echo "✅ PKG готов к распространению: $(SIGNED_PKG_NAME)"

# Проверка требований
check-requirements:
	@echo "🔍 Проверка требований..."
	@python3 -c "import PyInstaller" >/dev/null 2>&1 || { echo "❌ PyInstaller не найден. Установите: pip install pyinstaller"; exit 1; }
	@command -v codesign >/dev/null 2>&1 || { echo "❌ codesign не найден. Установите Xcode Command Line Tools"; exit 1; }
	@command -v productbuild >/dev/null 2>&1 || { echo "❌ productbuild не найден. Установите Xcode Command Line Tools"; exit 1; }
	@command -v xcrun >/dev/null 2>&1 || { echo "❌ xcrun не найден. Установите Xcode Command Line Tools"; exit 1; }
	@if [ ! -d "$(SPARKLE_FRAMEWORK)" ]; then \
		echo "❌ Sparkle.framework не найден в $(SPARKLE_FRAMEWORK)"; \
		echo "   Установите: brew install --cask sparkle"; \
		exit 1; \
	fi
	@echo "✅ Все требования выполнены"

# Информация о сертификатах
cert-info:
	@echo "🔑 Доступные сертификаты подписи:"
	security find-identity -p codesigning -v | cat

# Быстрая сборка для разработки (без подписи)
dev-app: clean
	@echo "🚀 Быстрая сборка для разработки..."
	cd $(CLIENT_DIR) && python3 -m PyInstaller --clean -y $(PACKAGING_DIR)/Nexy.spec
	@echo "✅ Готово: $(APP_PATH)"
	@echo "💡 Для тестирования: make test-app"

# Настройка notarytool (уже выполнено)
setup-notary:
	@echo "✅ Профиль $(APPLE_NOTARY_PROFILE) уже настроен"
	@echo "📋 История нотаризации:"
	xcrun notarytool history --keychain-profile $(APPLE_NOTARY_PROFILE) | head -5
