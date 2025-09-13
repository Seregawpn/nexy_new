# 🔧 ТЕХНИЧЕСКИЕ СПЕЦИФИКАЦИИ ДЛЯ MACOS

## 📋 СИСТЕМНЫЕ ТРЕБОВАНИЯ

### Минимальная версия macOS:
- **macOS 10.15 (Catalina)** или новее
- **Архитектура:** arm64 (Apple Silicon) и x86_64 (Intel)

### Зависимости системы:
- **SwitchAudioSource** (устанавливается через Homebrew)
- **Core Audio Framework** (встроен в macOS)
- **Foundation Framework** (встроен в macOS)
- **AppKit Framework** (встроен в macOS)

## 🎯 КОНФИГУРАЦИЯ PYINSTALLER

### Основные параметры:
```python
# Спецификация для PyInstaller
a = Analysis(
    ['audio_device_manager/__init__.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('audio_device_manager/macos/entitlements/audio_device_manager.entitlements', 'entitlements'),
        ('audio_device_manager/macos/info/Info.plist', 'info'),
    ],
    hiddenimports=[
        'audio_device_manager.core.device_manager',
        'audio_device_manager.core.device_monitor',
        'audio_device_manager.core.device_switcher',
        'audio_device_manager.core.types',
        'audio_device_manager.config.device_priorities',
        'audio_device_manager.macos.core_audio_bridge',
        'audio_device_manager.macos.device_detector',
        'audio_device_manager.macos.switchaudio_bridge',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
```

### Параметры исполняемого файла:
```python
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='audio_device_manager',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='audio_device_manager/macos/entitlements/audio_device_manager.entitlements',
    icon='audio_device_manager/macos/info/icon.icns',
)
```

## 🔐 ENTITLEMENTS СПЕЦИФИКАЦИЯ

### Основные разрешения:
```xml
<!-- Аудио устройства -->
<key>com.apple.security.device.audio-input</key>
<true/>
<key>com.apple.security.device.audio-output</key>
<true/>
<key>com.apple.security.device.audio-unit</key>
<true/>

<!-- Bluetooth и USB -->
<key>com.apple.security.device.bluetooth</key>
<true/>
<key>com.apple.security.device.usb</key>
<true/>

<!-- Системные события -->
<key>com.apple.security.device.system-events</key>
<true/>
<key>com.apple.security.automation.apple-events</key>
<true/>

<!-- Файловая система -->
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
<key>com.apple.security.files.downloads.read-write</key>
<true/>

<!-- Hardened Runtime -->
<key>com.apple.security.cs.allow-jit</key>
<true/>
<key>com.apple.security.cs.allow-unsigned-executable-memory</key>
<true/>
<key>com.apple.security.cs.debugger</key>
<true/>
```

## 📦 PKG СПЕЦИФИКАЦИЯ

### Метаданные пакета:
- **Identifier:** `com.nexy.audio-device-manager`
- **Version:** `1.0.0`
- **Install Location:** `/usr/local/bin`
- **Minimum OS Version:** `10.15`
- **Architecture:** `arm64, x86_64`

### Структура установки:
```
/usr/local/bin/audio_device_manager
/usr/local/lib/audio_device_manager/
├── core/
├── config/
├── macos/
└── __init__.py
/usr/local/share/audio_device_manager/
├── entitlements/
├── info/
└── requirements/
```

## 🎫 НОТАРИЗАЦИЯ СПЕЦИФИКАЦИЯ

### Требования к пакету:
- **Формат:** PKG или DMG
- **Подпись:** Developer ID Application
- **Hardened Runtime:** Включен
- **Entitlements:** Валидные

### Процесс нотаризации:
1. **Загрузка:** `xcrun notarytool submit`
2. **Проверка:** `xcrun notarytool info`
3. **Прикрепление:** `xcrun stapler staple`

### Параметры команды:
```bash
# Загрузка
xcrun notarytool submit audio_device_manager.pkg \
  --apple-id "developer@example.com" \
  --password "app-specific-password" \
  --team-id "TEAM123456"

# Проверка статуса
xcrun notarytool info [SUBMISSION_ID] \
  --apple-id "developer@example.com" \
  --password "app-specific-password"

# Прикрепление тикета
xcrun stapler staple audio_device_manager.pkg
```

## 🔍 ПРОВЕРКА И ВАЛИДАЦИЯ

### Команды для проверки подписи:
```bash
# Детальная информация о подписи
codesign -dv --verbose=4 audio_device_manager

# Проверка entitlements
codesign -d --entitlements - audio_device_manager

# Проверка целостности
codesign --verify --verbose audio_device_manager

# Проверка нотаризации
spctl -a -v audio_device_manager
```

### Команды для проверки зависимостей:
```bash
# Список связанных библиотек
otool -L audio_device_manager

# Проверка архитектуры
file audio_device_manager

# Проверка символов
nm audio_device_manager
```

## ⚠️ ИЗВЕСТНЫЕ ОГРАНИЧЕНИЯ

### Sandbox ограничения:
- Ограниченный доступ к системным настройкам
- Необходимость пользовательских разрешений для Bluetooth
- Ограничения на выполнение системных команд

### Совместимость:
- Требует macOS 10.15+ для полной функциональности
- SwitchAudioSource должен быть установлен в системе
- Некоторые функции могут не работать в Sandbox режиме

### Производительность:
- Инициализация может занять 2-3 секунды
- Мониторинг устройств использует 1-2% CPU
- Переключение устройств занимает 0.5-1 секунду

---

*Версия: 1.0.0 | Дата: $(date) | Автор: Nexy Development Team*
