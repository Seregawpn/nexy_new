# Screenshot Capture Module для macOS

## 📋 **ОБЗОР**

Модуль `screenshot_capture` предоставляет функциональность захвата скриншотов на macOS с полной поддержкой упаковки, подписи и нотаризации.

## 🗂️ **СТРУКТУРА МОДУЛЯ**

```
screenshot_capture/
├── core/
│   ├── types.py              # Типы данных
│   ├── screenshot_capture.py # Основной API
│   └── config.py             # Конфигурация
├── macos/
│   ├── core_graphics_bridge.py # Core Graphics API
│   ├── entitlements/         # Права доступа
│   ├── info/                 # Info.plist
│   ├── scripts/              # Скрипты сборки
│   └── packaging/            # Требования
├── utils/
│   ├── image_utils.py        # Обработка изображений
│   └── base64_utils.py       # Base64 утилиты
├── tests/
│   └── test_screenshot.py    # Тесты
└── README.md                 # Документация
```

## 🚀 **БЫСТРЫЙ СТАРТ**

### 1. Установка зависимостей
```bash
cd screenshot_capture/macos
pip install -r packaging/requirements.txt
```

### 2. Простое использование
```python
from screenshot_capture import ScreenshotCapture

# Создание модуля
capture = ScreenshotCapture()

# Захват скриншота
result = await capture.capture_screenshot()

if result.success:
    base64_data = result.data.base64_data
    # Готово для отправки через gRPC
else:
    print(f"Ошибка: {result.error}")
```

### 3. С конфигурацией
```python
from screenshot_capture import ScreenshotCapture, ScreenshotConfig, ScreenshotFormat, ScreenshotQuality

config = ScreenshotConfig(
    format=ScreenshotFormat.JPEG,
    quality=ScreenshotQuality.HIGH,
    max_width=1920,
    max_height=1080
)

capture = ScreenshotCapture(config)
result = await capture.capture_screenshot()
```

## 🔐 **ПРАВА ДОСТУПА**

### macOS Entitlements (по необходимости):
- ✅ **System Events** — `com.apple.security.automation.apple-events` (если отправляете Apple Events)
- ✅ **Microphone** — `com.apple.security.device.audio-input` (если модуль использует микрофон и включён Sandbox)

Примечание: для Screen Recording/Screen Capture отдельного entitlement нет. Доступ выдаётся пользователем в Системных настройках → Конфиденциальность и безопасность → Запись экрана.

### Info.plist:
- **NSScreenCaptureUsageDescription**: "This app needs access to screen capture for screenshot functionality and visual analysis."
- (Опционально) **NSMicrophoneUsageDescription**: если используете микрофон в связке с захватом экрана

## 📱 **ИНТЕГРАЦИЯ С СУЩЕСТВУЮЩИМИ МОДУЛЯМИ**

### С ModuleCoordinator:
```python
def _initialize_screen_capture(self):
    from ...screenshot_capture import ScreenshotCapture, ScreenshotConfig
    
    config = ScreenshotConfig(
        format="jpeg",
        quality=85,
        max_width=1920,
        max_height=1080
    )
    
    self.screen_capture = ScreenshotCapture(config)
```

### С text_processor:
```python
# В generate_response_stream:
if self.screen_capture:
    screenshot_result = await self.screen_capture.capture_screenshot()
    if screenshot_result.success:
        screenshot_base64 = screenshot_result.data.base64_data
        # Передача в text_processor
```

## 🛠️ **API МЕТОДЫ**

### Основные методы:
```python
# Захват скриншота
result = await capture.capture_screenshot()

# Захват области
region = (100, 100, 800, 600)  # x, y, width, height
result = await capture.capture_region(region)

# Тест возможности захвата
can_capture = await capture.test_capture()

# Информация об экране
screen_info = capture.get_screen_info()

# Статус модуля
status = capture.get_status()
```

### Результат:
```python
if result.success:
    base64_data = result.data.base64_data
    width = result.data.width
    height = result.data.height
    mime_type = result.data.mime_type  # "image/jpeg"
else:
    error = result.error
```

## 📦 **ТРЕБОВАНИЯ ДЛЯ УПАКОВКИ**

### Основные зависимости:
- **PyInstaller** >= 5.0.0
- **pyobjc-framework-Cocoa** >= 9.0
- **pyobjc-framework-CoreGraphics** >= 9.0
- **Pillow** >= 9.0.0
- **PyYAML** >= 6.0

### macOS специфичные:
- **pyobjc-framework-AppKit** >= 9.0
- **pyobjc-framework-Foundation** >= 9.0
- **pyobjc-framework-Quartz** >= 9.0

## 🧪 **ТЕСТИРОВАНИЕ**

### Запуск тестов:
```bash
cd screenshot_capture
python -m pytest tests/test_screenshot.py -v
```

### Тестовые сценарии:
- ✅ **Инициализация** модуля
- ✅ **Захват скриншота** полного экрана
- ✅ **Захват области** экрана
- ✅ **Тест возможности** захвата
- ✅ **Информация об экране**
- ✅ **Статус модуля**

## 🔧 **КОНФИГУРАЦИЯ**

### Настройки по умолчанию:
```python
DEFAULT_CONFIG = ScreenshotConfig(
    format=ScreenshotFormat.JPEG,
    quality=ScreenshotQuality.MEDIUM,
    region=ScreenshotRegion.FULL_SCREEN,
    include_cursor=False,
    compress=True,
    max_width=1920,
    max_height=1080,
    timeout=5.0
)
```

### Загрузка из app_config.yaml:
```yaml
screen_capture:
  quality: 85
  format: "jpeg"
  max_width: 1920
  max_height: 1080
```

## 🚀 **СБОРКА И УПАКОВКА**

### 1. Сборка приложения:
```bash
cd screenshot_capture/macos/scripts
chmod +x build_macos.sh
./build_macos.sh
```

### 2. Подпись и нотаризация:
```bash
chmod +x sign_and_notarize.sh
./sign_and_notarize.sh
```

### 3. Переменные окружения:
```bash
export DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_ID="your@email.com"
export APP_PASSWORD="app-specific-password"
export TEAM_ID="5NKLL2CLB9"
```

## ⚠️ **ВАЖНЫЕ ЗАМЕЧАНИЯ**

### Безопасность:
- **Никогда не коммитьте** сертификаты в Git
- **Используйте** .gitignore для .p12 файлов
- **Храните** пароли в безопасном месте

### Производительность:
- **Время захвата**: < 500ms для 1920x1080
- **Размер JPEG**: ~200KB для 1920x1080
- **Память**: Минимальное использование

### Совместимость:
- **macOS**: 10.15+
- **Архитектуры**: arm64, x86_64
- **Python**: 3.8+

## 📚 **ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ**

- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Core Graphics Documentation](https://developer.apple.com/documentation/coregraphics)
- [PyObjC Documentation](https://pyobjc.readthedocs.io/)

## 🆘 **ПОДДЕРЖКА**

При возникновении проблем:

1. **Проверьте права** Screen Recording в System Preferences
2. **Проверьте сертификаты** в Keychain
3. **Проверьте логи** модуля
4. **Запустите тесты** для диагностики

---

**Версия**: 1.0.0  
**Дата**: 2024-09-12  
**Автор**: Nexy Development Team
