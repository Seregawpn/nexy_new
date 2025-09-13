# macOS Требования для Screenshot Capture

## 📋 **ОБЗОР**

Данный документ описывает все требования к macOS для модуля `screenshot_capture`, включая упаковку, подпись, нотаризацию и распространение.

## 🗂️ **СТРУКТУРА macOS ТРЕБОВАНИЙ**

```
macos/
├── entitlements/
│   └── screenshot_capture.entitlements    # Права доступа
├── info/
│   └── Info.plist                         # Метаданные приложения
├── scripts/
│   ├── build_macos.sh                     # Скрипт сборки
│   └── sign_and_notarize.sh               # Скрипт подписи и нотаризации
├── certificates/
│   └── certificate_setup.md               # Документация по сертификатам
├── notarization/
│   └── notarization_config.json           # Конфигурация нотаризации
├── packaging/
│   └── requirements.txt                   # Зависимости для упаковки
└── README.md                              # Данный файл
```

## 🔐 **ПРАВА ДОСТУПА (ENTITLEMENTS)**

### **Основные права:**
- ✅ **Screen Recording** - `com.apple.security.device.screen-capture`
- ✅ **Camera Access** - `com.apple.security.device.camera`
- ✅ **Apple Events** - `com.apple.security.automation.apple-events`
- ✅ **File Access** - `com.apple.security.files.user-selected.read-write`

### **Дополнительные права:**
- ✅ **USB Devices** - `com.apple.security.device.usb`
- ✅ **Audio Units** - `com.apple.security.device.audio-unit`
- ✅ **Downloads** - `com.apple.security.files.downloads.read-write`

## 📱 **МЕТАДАННЫЕ ПРИЛОЖЕНИЯ (Info.plist)**

### **Основная информация:**
- **Bundle ID**: `com.nexy.screenshot.capture`
- **Версия**: `1.0.0`
- **Минимальная macOS**: `10.15`
- **Архитектуры**: `arm64`, `x86_64`

### **Описания прав:**
- **Screen Capture**: "This app needs access to screen capture for screenshot functionality and visual analysis."
- **Camera**: "This app needs access to screen recording for screenshot functionality."
- **Apple Events**: "This app needs access to system events for screenshot coordination and management."

## 🛠️ **ЗАВИСИМОСТИ ДЛЯ УПАКОВКИ**

### **Основные зависимости:**
```bash
PyInstaller>=5.0.0
pyobjc-framework-Cocoa>=9.0
pyobjc-framework-CoreGraphics>=9.0
pyobjc-framework-Foundation>=9.0
pyobjc-framework-Quartz>=9.0
Pillow>=9.0.0
PyYAML>=6.0
```

### **macOS специфичные:**
```bash
pyobjc-framework-AppKit>=9.0
pyobjc-framework-ApplicationServices>=9.0
```

## 🚀 **ПРОЦЕСС СБОРКИ И УПАКОВКИ**

### **1. Подготовка окружения**

```bash
# Установка зависимостей
pip install -r packaging/requirements.txt

# Настройка переменных окружения
export DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_ID="your@email.com"
export APP_PASSWORD="app-specific-password"
export TEAM_ID="YOUR_TEAM_ID"
```

### **2. Сборка приложения**

```bash
cd scripts
chmod +x build_macos.sh
./build_macos.sh
```

**Результат**: `dist/Screenshot Capture.app`

### **3. Подпись и нотаризация**

```bash
chmod +x sign_and_notarize.sh
./sign_and_notarize.sh
```

**Результат**: Подписанное и нотаризованное приложение

### **4. Создание PKG пакета**

```bash
# PKG создается автоматически в процессе нотаризации
# Результат: Screenshot Capture_com.nexy.screenshot.capture.pkg
```

## 🔧 **КОНФИГУРАЦИЯ**

### **Переменные окружения:**
```bash
# Apple Developer Account
APPLE_ID="your@email.com"
TEAM_ID="YOUR_TEAM_ID"
APP_PASSWORD="app-specific-password"

# Developer ID Certificates
DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
INSTALLER_ID="Developer ID Installer: Your Name (TEAM_ID)"

# Bundle Identifiers
BUNDLE_ID="com.nexy.screenshot.capture"
```

### **Конфигурация нотаризации:**
```json
{
  "apple_id": "your@email.com",
  "team_id": "YOUR_TEAM_ID",
  "bundle_id": "com.nexy.screenshot.capture",
  "app_name": "Nexy Screenshot Capture",
  "version": "1.0.0"
}
```

## 📊 **ХАРАКТЕРИСТИКИ ПРИЛОЖЕНИЯ**

### **Размер и производительность:**
- **Размер приложения**: ~2-5 MB
- **Время сборки**: ~2-5 минут
- **Время подписи**: ~1-2 минуты
- **Время нотаризации**: ~5-15 минут

### **Совместимость:**
- **macOS**: 10.15+ (Catalina и новее)
- **Архитектуры**: Intel (x86_64), Apple Silicon (arm64)
- **Python**: 3.8+

## ⚠️ **ВАЖНЫЕ ЗАМЕЧАНИЯ**

### **Безопасность:**
- **Никогда не коммитьте** сертификаты в Git
- **Используйте** .gitignore для .p12 файлов
- **Храните** пароли в безопасном месте

### **Обновление:**
- **Проверяйте** срок действия сертификатов
- **Обновляйте** зависимости регулярно
- **Тестируйте** после обновлений

### **Устранение проблем:**
- **Проверяйте** права доступа к файлам
- **Очищайте** Keychain при проблемах
- **Переустанавливайте** сертификаты при необходимости

## 🧪 **ТЕСТИРОВАНИЕ**

### **Проверка подписи:**
```bash
codesign --verify --verbose "dist/Screenshot Capture.app"
```

### **Проверка нотаризации:**
```bash
xcrun stapler validate "dist/Screenshot Capture.app"
```

### **Проверка прав:**
```bash
codesign --display --entitlements - "dist/Screenshot Capture.app"
```

## 📚 **ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ**

- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)
- [PyObjC Documentation](https://pyobjc.readthedocs.io/)

## 🆘 **ПОДДЕРЖКА**

При возникновении проблем:

1. **Проверьте** установку сертификатов
2. **Проверьте** переменные окружения
3. **Проверьте** права доступа
4. **Обратитесь** к документации Apple

---

**Версия**: 1.0.0  
**Дата**: 2024-09-12  
**Автор**: Nexy Development Team
