# Руководство по упаковке screenshot_capture для macOS

## 📋 Обзор

Данное руководство описывает требования и процедуры для правильной упаковки модуля `screenshot_capture` в macOS приложение с сертификацией, подписью и нотаризацией. Модуль требует специальных разрешений для захвата экрана.

## 🏗️ Архитектура macOS приложения

### Структура приложения
```
Nexy.app/
├── Contents/
│   ├── Info.plist
│   ├── MacOS/
│   │   └── Nexy (исполняемый файл)
│   ├── Resources/
│   │   ├── screenshot_capture/
│   │   │   ├── __init__.py
│   │   │   ├── core/
│   │   │   ├── macos/
│   │   │   └── utils/
│   │   └── other_modules/
│   └── Frameworks/
│       └── Python.framework/
```

## 🔐 Требования к сертификации

### 1. Apple Developer Account
- **Требуется**: Активный Apple Developer Account ($99/год)
- **Необходимо для**: Code Signing, Notarization, App Store
- **Альтернатива**: Ad Hoc distribution (без App Store)

### 2. Сертификаты
```bash
# Создание сертификата для разработки
security create-keychain -p "password" build.keychain
security default-keychain -s build.keychain
security unlock-keychain -p "password" build.keychain

# Импорт сертификата разработчика
security import "DeveloperIDApplication.cer" -k build.keychain -T /usr/bin/codesign
security import "DeveloperIDInstaller.cer" -k build.keychain -T /usr/bin/codesign
```

### 3. Provisioning Profiles
- **Development**: Для тестирования на зарегистрированных устройствах
- **Distribution**: Для распространения через App Store или Ad Hoc

## 📦 Упаковка модуля

### 1. Создание структуры приложения
```bash
#!/bin/bash
# create_app_structure.sh

APP_NAME="Nexy"
APP_VERSION="1.0.0"
BUNDLE_ID="com.nexy.assistant"

# Создание структуры .app
mkdir -p "${APP_NAME}.app/Contents/MacOS"
mkdir -p "${APP_NAME}.app/Contents/Resources"
mkdir -p "${APP_NAME}.app/Contents/Frameworks"

# Копирование screenshot_capture
cp -r client/screenshot_capture "${APP_NAME}.app/Contents/Resources/"

# Копирование других модулей
cp -r client/mode_management "${APP_NAME}.app/Contents/Resources/"
cp -r client/grpc_client "${APP_NAME}.app/Contents/Resources/"
# state_management удален - не требуется
```

### 2. Создание Info.plist
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Nexy</string>
    <key>CFBundleIdentifier</key>
    <string>com.nexy.app</string>
    <key>CFBundleName</key>
    <string>Nexy</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSSupportsAutomaticGraphicsSwitching</key>
    <true/>
    
    <!-- Разрешения для screenshot_capture -->
    <key>NSScreenCaptureUsageDescription</key>
    <string>Nexy needs screen capture access to take screenshots for voice command processing and context analysis.</string>
    <!-- Камера не требуется для Screen Recording; добавляйте NSCameraUsageDescription только при реальном использовании камеры -->
    <key>NSMicrophoneUsageDescription</key>
    <string>Nexy needs microphone access for voice recognition and processing.</string>
    <key>NSAppleEventsUsageDescription</key>
    <string>Nexy needs to control other applications for automation tasks.</string>
    
    <!-- Дополнительные разрешения -->
    <key>NSDesktopFolderUsageDescription</key>
    <string>Nexy needs access to desktop folder for saving screenshots and temporary files.</string>
    <key>NSDocumentsFolderUsageDescription</key>
    <string>Nexy needs access to documents folder for saving processed screenshots.</string>
</dict>
</plist>
```

### 3. Создание исполняемого файла
```python
#!/usr/bin/env python3
# main.py - Главный файл приложения

import sys
import os
import asyncio
import logging
from pathlib import Path

# Добавление пути к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Resources'))

from mode_management import ModeController, AppMode, ModeConfig
from screenshot_capture import ScreenshotCapture, ScreenshotConfig, ScreenshotFormat, ScreenshotQuality
from grpc_client import GrpcClient
# state_management удален - используйте основной StateManager из main.py

class NexyApp:
    def __init__(self):
        self.controller = None
        self.screenshot_capture = None
        self.setup_logging()
    
    def setup_logging(self):
        """Настройка логирования для macOS"""
        log_dir = Path.home() / "Library" / "Logs" / "Nexy"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "nexy.log"),
                logging.StreamHandler()
            ]
        )
    
    async def initialize(self):
        """Инициализация приложения"""
        try:
            # Создание компонентов
            config = ModeConfig(default_mode=AppMode.SLEEPING)
            self.controller = ModeController(config)
            
            # Инициализация screenshot_capture
            screenshot_config = ScreenshotConfig(
                format=ScreenshotFormat.JPEG,
                quality=ScreenshotQuality.MEDIUM,
                max_width=1280,
                max_height=720,
                timeout=5.0
            )
            self.screenshot_capture = ScreenshotCapture(screenshot_config)
            
            # Проверяем права доступа к экрану
            can_capture = await self.screenshot_capture.test_capture()
            if not can_capture:
                logging.warning("⚠️ Нет прав доступа к экрану. Скриншоты недоступны.")
                # Показываем пользователю инструкции по настройке разрешений
                self.show_screen_permission_instructions()
            
            # Инициализация других компонентов
            grpc_client = GrpcClient()
            state_manager = StateManager()
            
            # Регистрация режимов
            await self.register_modes(grpc_client, state_manager)
            
            # Регистрация переходов
            self.register_transitions()
            
            logging.info("Nexy приложение инициализировано")
            return True
            
        except Exception as e:
            logging.error(f"Ошибка инициализации: {e}")
            return False
    
    def show_screen_permission_instructions(self):
        """Показывает инструкции по настройке разрешений экрана"""
        instructions = """
        Для работы скриншотов необходимо предоставить разрешения:
        
        1. Откройте Системные настройки > Безопасность и конфиденциальность
        2. Перейдите на вкладку "Конфиденциальность"
        3. Выберите "Запись экрана" в левом меню
        4. Добавьте Nexy в список разрешенных приложений
        5. Перезапустите приложение
        
        Без этих разрешений функция скриншотов будет недоступна.
        """
        logging.info(instructions)
        # Здесь можно показать диалог пользователю
    
    async def register_modes(self, grpc_client, state_manager):
        """Регистрация режимов с интеграцией screenshot_capture"""
        from mode_management import SleepingMode, ProcessingMode, ListeningMode
        
        # Создание режимов с интеграцией скриншотов
        sleeping_mode = SleepingMode()
        processing_mode = ProcessingMode(grpc_client, state_manager)
        listening_mode = ListeningMode(None, None)  # speech_recognizer будет добавлен позже
        
        # Регистрация обработчиков с захватом скриншотов
        async def sleeping_handler():
            logging.info("🔄 Обработчик режима SLEEPING")
            await sleeping_mode.enter_mode()
            
        async def processing_handler():
            logging.info("🔄 Обработчик режима PROCESSING")
            await processing_mode.enter_mode()
            
            # Захватываем скриншот при обработке
            if self.screenshot_capture:
                result = await self.screenshot_capture.capture_screenshot()
                if result.success:
                    logging.info(f"📸 Скриншот захвачен: {result.data.width}x{result.data.height}")
                    # Отправляем скриншот на обработку
                    await self.process_screenshot(result.data)
                else:
                    logging.warning(f"⚠️ Ошибка захвата скриншота: {result.error}")
            
        async def listening_handler():
            logging.info("🔄 Обработчик режима LISTENING")
            await listening_mode.enter_mode()
            
            # Захватываем скриншот при начале прослушивания
            if self.screenshot_capture:
                result = await self.screenshot_capture.capture_screenshot()
                if result.success:
                    logging.info(f"📸 Контекстный скриншот: {result.data.width}x{result.data.height}")
                    # Сохраняем контекстный скриншот
                    await self.save_context_screenshot(result.data)
        
        self.controller.register_mode_handler(AppMode.SLEEPING, sleeping_handler)
        self.controller.register_mode_handler(AppMode.PROCESSING, processing_handler)
        self.controller.register_mode_handler(AppMode.LISTENING, listening_handler)
    
    async def process_screenshot(self, screenshot_data):
        """Обрабатывает захваченный скриншот"""
        try:
            # Конвертируем в формат для gRPC
            screenshot_dict = screenshot_data.to_dict()
            
            # Отправляем на сервер для анализа
            # response = await grpc_client.process_command("analyze_screenshot", screenshot_dict)
            
            logging.info("📸 Скриншот отправлен на обработку")
            
        except Exception as e:
            logging.error(f"Ошибка обработки скриншота: {e}")
    
    async def save_context_screenshot(self, screenshot_data):
        """Сохраняет контекстный скриншот"""
        try:
            # Сохраняем в временную папку
            temp_dir = Path.home() / "Library" / "Caches" / "Nexy" / "screenshots"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = int(time.time())
            filename = f"context_{timestamp}.jpg"
            filepath = temp_dir / filename
            
            # Декодируем base64 и сохраняем
            import base64
            with open(filepath, 'wb') as f:
                f.write(base64.b64decode(screenshot_data.base64_data))
            
            logging.info(f"📸 Контекстный скриншот сохранен: {filepath}")
            
        except Exception as e:
            logging.error(f"Ошибка сохранения скриншота: {e}")
    
    def register_transitions(self):
        """Регистрация переходов между режимами"""
        from mode_management import ModeTransition, ModeTransitionType
        
        # Основные переходы
        transitions = [
            ModeTransition(AppMode.SLEEPING, AppMode.LISTENING, ModeTransitionType.AUTOMATIC),
            ModeTransition(AppMode.LISTENING, AppMode.PROCESSING, ModeTransitionType.AUTOMATIC),
            ModeTransition(AppMode.PROCESSING, AppMode.SLEEPING, ModeTransitionType.AUTOMATIC),
        ]
        
        for transition in transitions:
            self.controller.register_transition(transition)
    
    async def run(self):
        """Запуск приложения"""
        if not await self.initialize():
            return False
        
        try:
            # Основной цикл приложения
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logging.info("Получен сигнал завершения")
        except Exception as e:
            logging.error(f"Ошибка в основном цикле: {e}")
        finally:
            await self.cleanup()
        
        return True
    
    async def cleanup(self):
        """Очистка ресурсов"""
        if self.controller:
            # Переключение в режим сна
            await self.controller.switch_mode(AppMode.SLEEPING)
        
        if self.screenshot_capture:
            self.screenshot_capture.cleanup()
        
        logging.info("Приложение завершено")

async def main():
    """Главная функция"""
    app = NexyApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
```

## 🔏 Подпись кода (Code Signing)

### 1. Создание скрипта подписи
```bash
#!/bin/bash
# sign_app.sh

APP_NAME="Nexy"
BUNDLE_ID="com.nexy.assistant"
DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
INSTALLER_ID="Developer ID Installer: Your Name (TEAM_ID)"

# Подпись исполняемого файла
codesign --force --verify --verbose --sign "$DEVELOPER_ID" \
    --options runtime \
    --entitlements entitlements.plist \
    "${APP_NAME}.app/Contents/MacOS/Nexy"

# Подпись всех Python файлов
find "${APP_NAME}.app" -name "*.py" -exec codesign --force --verify --verbose --sign "$DEVELOPER_ID" {} \;

# Подпись всего приложения
codesign --force --verify --verbose --sign "$DEVELOPER_ID" \
    --options runtime \
    --entitlements entitlements.plist \
    "${APP_NAME}.app"

# Проверка подписи
codesign --verify --verbose "${APP_NAME}.app"
spctl --assess --verbose "${APP_NAME}.app"
```

### 2. Создание entitlements.plist
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.app-sandbox</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.device.audio-input</key>
    <true/>
    <key>com.apple.security.automation.apple-events</key>
    <true/>
    
    <!-- Для Screen Recording отдельного entitlement нет; доступ выдаётся пользователем в настройках -->
    
    <!-- Дополнительные разрешения -->
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>
    <key>com.apple.security.files.pictures.read-write</key>
    <true/>
    
    <!-- Технические разрешения -->
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
</dict>
</plist>
```

## 📦 Создание PKG установщика

### 1. Создание скрипта сборки PKG
```bash
#!/bin/bash
# create_pkg.sh

APP_NAME="Nexy"
PKG_NAME="Nexy-1.0.0.pkg"
BUNDLE_ID="com.nexy.assistant"
INSTALLER_ID="Developer ID Installer: Your Name (TEAM_ID)"

# Создание временной директории
TEMP_DIR=$(mktemp -d)
mkdir -p "$TEMP_DIR/Applications"

# Копирование приложения
cp -r "${APP_NAME}.app" "$TEMP_DIR/Applications/"

# Создание скриптов установки/удаления
cat > "$TEMP_DIR/postinstall" << 'EOF'
#!/bin/bash
# Скрипт пост-установки

echo "Nexy установлен успешно"
echo ""
echo "ВАЖНО: Для работы скриншотов необходимо:"
echo "1. Открыть Системные настройки > Безопасность и конфиденциальность"
echo "2. Перейти на вкладку 'Конфиденциальность'"
echo "3. Выбрать 'Запись экрана' в левом меню"
echo "4. Добавить Nexy в список разрешенных приложений"
echo "5. Перезапустить приложение"
echo ""

# Создание папок для логов и кэша
mkdir -p "$HOME/Library/Logs/Nexy"
mkdir -p "$HOME/Library/Caches/Nexy/screenshots"
mkdir -p "$HOME/Library/Application Support/Nexy"

exit 0
EOF

cat > "$TEMP_DIR/preinstall" << 'EOF'
#!/bin/bash
# Скрипт пред-установки

echo "Подготовка к установке Nexy..."
echo "Проверка системных требований..."

# Проверяем версию macOS
OS_VERSION=$(sw_vers -productVersion)
REQUIRED_VERSION="10.15"

if [[ "$(printf '%s\n' "$REQUIRED_VERSION" "$OS_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]]; then
    echo "ОШИБКА: Требуется macOS $REQUIRED_VERSION или новее. Текущая версия: $OS_VERSION"
    exit 1
fi

echo "Системные требования выполнены"
exit 0
EOF

chmod +x "$TEMP_DIR/postinstall"
chmod +x "$TEMP_DIR/preinstall"

# Создание PKG
pkgbuild --root "$TEMP_DIR" \
    --identifier "$BUNDLE_ID" \
    --version "1.0.0" \
    --install-location "/" \
    --scripts "$TEMP_DIR" \
    "$PKG_NAME"

# Подпись PKG
productsign --sign "$INSTALLER_ID" "$PKG_NAME" "signed_$PKG_NAME"

# Очистка
rm -rf "$TEMP_DIR"
```

### 2. Создание Distribution.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<installer-gui-script minSpecVersion="1">
    <title>Nexy - Voice Assistant</title>
    <organization>com.nexy</organization>
    <domains enable_localSystem="true"/>
    <options customize="never" require-scripts="true"/>
    
    <pkg-ref id="com.nexy.app">
        <bundle-version>
            <bundle id="com.nexy.app" path="Nexy.app" CFBundleVersion="1.0.0"/>
        </bundle-version>
    </pkg-ref>
    
    <choices-outline>
        <line choice="default">
            <line choice="com.nexy.app"/>
        </line>
    </choices-outline>
    
    <choice id="default"/>
    <choice id="com.nexy.app" visible="false">
        <pkg-ref id="com.nexy.app"/>
    </choice>
    
    <pkg-ref id="com.nexy.app" version="1.0.0" onConclusion="none">Nexy-1.0.0.pkg</pkg-ref>
    
    <!-- Информация о разрешениях -->
    <welcome file="welcome.html"/>
    <readme file="readme.html"/>
</installer-gui-script>
```

## 🔐 Нотаризация (Notarization)

### 1. Создание скрипта нотаризации
```bash
#!/bin/bash
# notarize.sh

APP_NAME="Nexy"
PKG_NAME="signed_Nexy-1.0.0.pkg"
BUNDLE_ID="com.nexy.assistant"
APPLE_ID="seregawpn@gmail.com"
APP_PASSWORD="qtiv-kabm-idno-qmbl"
TEAM_ID="5NKLL2CLB9"

# Отправка на нотаризацию
echo "Отправка на нотаризацию..."
xcrun notarytool submit "$PKG_NAME" \
    --apple-id "$APPLE_ID" \
    --password "$APP_PASSWORD" \
    --team-id "$TEAM_ID" \
    --wait

# Прикрепление тикета нотаризации
echo "Прикрепление тикета нотаризации..."
xcrun stapler staple "$PKG_NAME"

# Проверка нотаризации
echo "Проверка нотаризации..."
xcrun stapler validate "$PKG_NAME"
spctl --assess --type install "$PKG_NAME"

echo "Нотаризация завершена успешно"
```

### 2. Создание app-specific password
1. Войдите в [Apple ID](https://appleid.apple.com)
2. Перейдите в "App-Specific Passwords"
3. Создайте новый пароль для "Nexy Notarization"
4. Сохраните пароль в безопасном месте

## 🚀 Автоматизация сборки

### 1. Создание Makefile
```makefile
# Makefile для автоматизации сборки

APP_NAME = Nexy
VERSION = 1.0.0
BUNDLE_ID = com.nexy.app
DEVELOPER_ID = "Developer ID Application: Your Name (TEAM_ID)"
INSTALLER_ID = "Developer ID Installer: Your Name (TEAM_ID)"

.PHONY: clean build sign notarize package

clean:
	rm -rf $(APP_NAME).app
	rm -f *.pkg
	rm -f *.dmg

build: clean
	./create_app_structure.sh
	./create_executable.sh

sign: build
	./sign_app.sh

notarize: sign
	./notarize.sh

package: notarize
	./create_pkg.sh

all: package
	@echo "Сборка завершена: signed_$(APP_NAME)-$(VERSION).pkg"
	@echo "ВАЖНО: Убедитесь, что пользователи настроили разрешения экрана!"
```

### 2. Создание GitHub Actions workflow
```yaml
# .github/workflows/build-macos.yml

name: Build macOS App with Screenshot Capture

on:
  push:
    tags:
      - 'v*'

jobs:
  build:
    runs-on: macos-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Build app
      run: |
        make build
    
    - name: Code sign
      env:
        DEVELOPER_ID: ${{ secrets.DEVELOPER_ID }}
      run: |
        make sign
    
    - name: Notarize
      env:
        APPLE_ID: ${{ secrets.APPLE_ID }}
        APP_PASSWORD: ${{ secrets.APP_PASSWORD }}
        TEAM_ID: ${{ secrets.TEAM_ID }}
      run: |
        make notarize
    
    - name: Create package
      run: |
        make package
    
    - name: Upload artifacts
      uses: actions/upload-artifact@v3
      with:
        name: Nexy-macOS-Screenshot
        path: |
          signed_Nexy-*.pkg
```

## ⚠️ Требования к модулю screenshot_capture

### 1. Зависимости
```python
# requirements.txt
asyncio>=3.4.3
logging>=0.4.9.6
typing>=3.7.4
dataclasses>=0.6
# macOS специфичные зависимости
pyobjc-framework-CoreGraphics>=8.0  # Для захвата экрана
pyobjc-framework-Quartz>=8.0        # Для работы с дисплеями
```

### 2. Разрешения (Permissions)
- **Запись экрана** (Screen Recording) - КРИТИЧЕСКИ ВАЖНО
- **Микрофон** - для голосовых команд
- **Камера** - для визуального ввода
- **Автоматизация** - для управления другими приложениями
- **Файловая система** - для сохранения скриншотов

### 3. Безопасность
```python
# Безопасная работа с файлами
import os
from pathlib import Path

def get_safe_screenshot_path(filename):
    """Получение безопасного пути для скриншотов"""
    home = Path.home()
    screenshots_dir = home / "Library" / "Caches" / "Nexy" / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return screenshots_dir / filename

# Безопасное логирование
def setup_secure_logging():
    """Настройка безопасного логирования"""
    log_dir = Path.home() / "Library" / "Logs" / "Nexy"
    log_dir.mkdir(exist_ok=True)
    
    # Ограничение размера логов
    logging.basicConfig(
        handlers=[
            logging.handlers.RotatingFileHandler(
                log_dir / "nexy.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            )
        ]
    )
```

## 🧪 Тестирование упаковки

### 1. Локальное тестирование
```bash
# Тестирование подписи
codesign --verify --verbose Nexy.app
spctl --assess --verbose Nexy.app

# Тестирование установки
sudo installer -pkg Nexy-1.0.0.pkg -target /

# Тестирование разрешений
# 1. Установите приложение
# 2. Запустите приложение
# 3. Проверьте запрос разрешений
# 4. Предоставьте разрешения в системных настройках
# 5. Протестируйте захват скриншотов
```

### 2. Тестирование на чистой системе
```bash
# Создание виртуальной машины macOS
# Установка приложения
# Проверка всех функций включая скриншоты
```

## 📋 Чек-лист упаковки

### ✅ Подготовка:
- [ ] Apple Developer Account активен
- [ ] Сертификаты установлены
- [ ] App-specific password создан
- [ ] Все зависимости определены
- [ ] Разрешения экрана протестированы

### ✅ Сборка:
- [ ] Структура .app создана
- [ ] Info.plist настроен с разрешениями экрана
- [ ] Entitlements.plist создан с screen-capture
- [ ] Исполняемый файл создан
- [ ] screenshot_capture модуль включен

### ✅ Подпись:
- [ ] Все файлы подписаны
- [ ] Подпись проверена
- [ ] Hardened Runtime включен
- [ ] Entitlements применены

### ✅ Нотаризация:
- [ ] PKG отправлен на нотаризацию
- [ ] Нотаризация успешна
- [ ] Тикет прикреплен
- [ ] Проверка Gatekeeper пройдена

### ✅ Распространение:
- [ ] PKG протестирован
- [ ] Инструкции по разрешениям включены
- [ ] Документация обновлена
- [ ] Версия увеличена

## 🚨 Частые проблемы

### 1. Проблема: "Code signature is invalid"
**Решение**: Проверьте цепочку сертификатов и переподпишите

### 2. Проблема: "Notarization failed"
**Решение**: Проверьте логи нотаризации и исправьте ошибки

### 3. Проблема: "App is damaged and can't be opened"
**Решение**: Проверьте подпись и нотаризацию

### 4. Проблема: "Permission denied" для скриншотов
**Решение**: 
- Проверьте entitlements.plist
- Убедитесь в наличии `com.apple.security.device.screen-capture`
- Проверьте настройки пользователя в Системных настройках

### 5. Проблема: Скриншоты не работают после установки
**Решение**:
- Покажите пользователю инструкции по настройке разрешений
- Добавьте проверку разрешений в приложение
- Предоставьте fallback режим без скриншотов

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи сборки
2. Убедитесь в правильности сертификатов
3. Проверьте статус нотаризации
4. Проверьте настройки разрешений экрана
5. Обратитесь к Apple Developer Support
6. Консультируйтесь с командой разработки

---

**Версия документа**: 1.0  
**Дата обновления**: 2025-09-13  
**Автор**: Nexy Team
