# macOS Требования для Input Processing

## 📋 **ОБЗОР**

Этот модуль содержит все необходимые файлы и конфигурации для упаковки, подписи, сертификации и нотаризации модуля `input_processing` на macOS.

## 🗂️ **СТРУКТУРА ПАПКИ**

```
macos/
├── entitlements/           # Права доступа
│   └── input_processing.entitlements
├── info/                   # Информация о приложении
│   └── Info.plist
├── scripts/                # Скрипты сборки и подписи
│   ├── build_macos.sh
│   └── sign_and_notarize.sh
├── packaging/              # Требования для упаковки
│   └── requirements.txt
└── README.md              # Этот файл
```

## 🚀 **БЫСТРЫЙ СТАРТ**

### 1. Установка зависимостей
```bash
cd input_processing/macos
pip install -r packaging/requirements.txt
```

### 2. Настройка сертификатов
```bash
# Следуйте инструкциям в voice_recognition/macos/certificates/certificate_setup.md
export DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
export APPLE_ID="your@email.com"
export APP_PASSWORD="app-specific-password"
export TEAM_ID="YOUR_TEAM_ID"
```

### 3. Сборка приложения
```bash
chmod +x scripts/build_macos.sh
./scripts/build_macos.sh
```

### 4. Подпись и нотаризация
```bash
chmod +x scripts/sign_and_notarize.sh
./scripts/sign_and_notarize.sh
```

## 🔐 **ПРАВА ДОСТУПА (ENTITLEMENTS)**

### Основные права:
- ✅ **Клавиатура** - `com.apple.security.device.usb`
- ✅ **Системные события** - `com.apple.security.automation.apple-events`
- ✅ **Микрофон** - `com.apple.security.device.microphone`
- ✅ **Аудио ввод** - `com.apple.security.device.audio-input`
- ✅ **Сеть** - `com.apple.security.network.client`
- ✅ **Песочница** - `com.apple.security.app-sandbox`

### Дополнительные права:
- ✅ **Файловая система** - `com.apple.security.files.user-selected.read-write`
- ✅ **Временные файлы** - `com.apple.security.temporary-exception.files.absolute-path.read-write`
- ✅ **Аудио юниты** - `com.apple.security.device.audio-unit`

## 📱 **ИНФОРМАЦИЯ О ПРИЛОЖЕНИИ (Info.plist)**

### Основные параметры:
- **Bundle ID**: `com.nexy.input.processing`
- **Версия**: `1.0.0`
- **Минимальная macOS**: `10.15`
- **Архитектуры**: `arm64`, `x86_64`

### Описания прав:
- **Клавиатура**: "This app needs access to keyboard input for spacebar press detection and input processing."
- **Микрофон**: "This app needs access to your microphone for voice recognition functionality."
- **Аудио**: "This app needs access to audio devices for voice recognition and playback."
- **Сеть**: "This app needs network access for Google Speech Recognition API."
- **Системные события**: "This app needs access to system events for keyboard monitoring and input processing."

## 🛠️ **СКРИПТЫ**

### build_macos.sh
- Сборка приложения с PyInstaller
- Создание .spec файла
- Проверка зависимостей
- Создание .app пакета

### sign_and_notarize.sh
- Подпись приложения
- Проверка подписи
- Создание архива
- Отправка на нотаризацию
- Прикрепление тикета
- Создание PKG пакета

## 📦 **ТРЕБОВАНИЯ ДЛЯ УПАКОВКИ**

### Основные зависимости:
- **PyInstaller** >= 5.0.0
- **pynput** >= 1.7.6
- **SpeechRecognition** >= 3.10.0
- **pyaudio** >= 0.2.11
- **numpy** >= 1.21.0

### macOS специфичные:
- **pyobjc-framework-CoreAudio** >= 9.0
- **pyobjc-framework-AudioToolbox** >= 9.0
- **pyobjc-framework-AVFoundation** >= 9.0

## 🧪 **ТЕСТИРОВАНИЕ**

### Тестовые сценарии:
- ✅ Клавиатура разрешена
- ✅ Клавиатура запрещена
- ✅ Микрофон разрешен
- ✅ Микрофон запрещен
- ✅ Сеть доступна
- ✅ Сеть недоступна
- ✅ Распознавание речи успешно
- ✅ Распознавание речи неудачно

### Тестовые устройства:
- MacBook Air M1
- MacBook Pro Intel
- Mac Studio M1

## ⚠️ **ВАЖНЫЕ ЗАМЕЧАНИЯ**

### Безопасность:
- **Никогда не коммитьте** сертификаты в Git
- **Используйте** .gitignore для .p12 файлов
- **Храните** пароли в безопасном месте

### Сроки действия:
- **Developer ID Application**: 1 год
- **Developer ID Installer**: 1 год
- **App-Specific Password**: Без срока действия

### Troubleshooting:
- **Ошибка подписи**: Проверьте сертификат в Keychain
- **Ошибка нотаризации**: Проверьте App-Specific Password
- **Ошибка валидации**: Проверьте entitlements.plist

## 📚 **ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ**

- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Entitlements Reference](https://developer.apple.com/documentation/bundleresources/entitlements)
- [Info.plist Reference](https://developer.apple.com/documentation/bundleresources/information_property_list)

## 🆘 **ПОДДЕРЖКА**

Если у вас возникли проблемы:

1. **Проверьте** переменные окружения
2. **Проверьте** сертификаты в Keychain
3. **Проверьте** права доступа в entitlements.plist
4. **Проверьте** логи сборки и подписи
5. **Обратитесь** к документации Apple Developer

---

**Версия**: 1.0.0  
**Дата**: 2024-09-12  
**Автор**: Nexy Development Team
