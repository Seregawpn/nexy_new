#!/bin/bash

# Скрипт для сборки macOS приложения с PyInstaller
# Запускать из корневой директории проекта Nexy

# --- Конфигурация ---
MODULE_NAME="hardware_id"
APP_NAME="NexyHardwareID"
PYTHON_VERSION="3.9" # Убедитесь, что это соответствует вашей версии Python
BUILD_DIR="./build/${MODULE_NAME}"
DIST_DIR="./dist/${MODULE_NAME}"
ENTITLEMENTS_FILE="./client/${MODULE_NAME}/macos/entitlements/${MODULE_NAME}.entitlements"
INFO_PLIST_FILE="./client/${MODULE_NAME}/macos/info/Info.plist"
MAIN_SCRIPT="./client/${MODULE_NAME}/core/${MODULE_NAME}.py" # Основной скрипт модуля
ICON_FILE="./client/assets/icons/nexy.icns" # Путь к иконке приложения

echo "🚀 Начинаем сборку модуля ${MODULE_NAME} для macOS..."

# 1. Создаем виртуальное окружение (если не существует)
if [ ! -d "venv" ]; then
    echo "🛠️ Создаем виртуальное окружение..."
    python${PYTHON_VERSION} -m venv venv
fi

# 2. Активируем виртуальное окружение
echo "🔄 Активируем виртуальное окружение..."
source venv/bin/activate

# 3. Устанавливаем зависимости
echo "📦 Устанавливаем зависимости..."
pip install -r "./client/${MODULE_NAME}/macos/packaging/requirements.txt"
pip install pyinstaller

# 4. Очищаем предыдущие сборки
echo "🧹 Очищаем предыдущие сборки..."
rm -rf "${BUILD_DIR}" "${DIST_DIR}"

# 5. Запускаем PyInstaller
echo "🏗️ Запускаем PyInstaller для сборки ${APP_NAME}..."
pyinstaller \
    --name "${APP_NAME}" \
    --onefile \
    --windowed \
    --add-data "client/${MODULE_NAME}/core:client/${MODULE_NAME}/core" \
    --add-data "client/${MODULE_NAME}/macos:client/${MODULE_NAME}/macos" \
    --add-data "client/${MODULE_NAME}/utils:client/${MODULE_NAME}/utils" \
    --add-data "client/config:client/config" \
    --add-data "client/utils:client/utils" \
    --hidden-import "subprocess" \
    --hidden-import "json" \
    --hidden-import "os" \
    --hidden-import "pathlib" \
    --hidden-import "datetime" \
    --hidden-import "uuid" \
    --hidden-import "re" \
    --hidden-import "platform" \
    --hidden-import "sys" \
    --hidden-import "logging" \
    --hidden-import "tempfile" \
    --hidden-import "unittest" \
    --hidden-import "unittest.mock" \
    --icon "${ICON_FILE}" \
    --osx-bundle-identifier "com.nexy.hardware.id" \
    --target-architecture universal2 \
    --distpath "${DIST_DIR}" \
    --workpath "${BUILD_DIR}" \
    "${MAIN_SCRIPT}"

if [ $? -ne 0 ]; then
    echo "❌ Ошибка PyInstaller. Сборка прервана."
    deactivate
    exit 1
fi

echo "✅ PyInstaller завершен. Приложение собрано в ${DIST_DIR}/${APP_NAME}.app"

# 6. Копируем Info.plist и применяем Entitlements
echo "📝 Применяем Info.plist и Entitlements..."
cp "${INFO_PLIST_FILE}" "${DIST_DIR}/${APP_NAME}.app/Contents/Info.plist"

# 7. Подписываем приложение (если есть сертификат)
echo "✍️ Подписываем приложение..."
codesign --force --deep --entitlements "${ENTITLEMENTS_FILE}" --options runtime --sign "Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)" "${DIST_DIR}/${APP_NAME}.app"

if [ $? -ne 0 ]; then
    echo "⚠️ Ошибка при подписании приложения. Продолжаем без подписи."
fi

echo "🎉 Сборка ${APP_NAME} завершена успешно!"
echo "📁 Приложение находится в: ${DIST_DIR}/${APP_NAME}.app"

# 8. Показываем информацию о сборке
echo ""
echo "📊 Информация о сборке:"
echo "   - Модуль: ${MODULE_NAME}"
echo "   - Приложение: ${APP_NAME}"
echo "   - Архитектура: universal2 (arm64 + x86_64)"
echo "   - Директория: ${DIST_DIR}"
echo "   - Entitlements: ${ENTITLEMENTS_FILE}"
echo "   - Info.plist: ${INFO_PLIST_FILE}"

deactivate
