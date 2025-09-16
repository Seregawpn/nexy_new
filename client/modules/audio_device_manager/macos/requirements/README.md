# 📦 macOS Packaging Requirements для Audio Device Manager

## 🎯 Обзор

Данная папка содержит **полные требования** для упаковки, подписания, сертификации и нотаризации модуля `audio_device_manager` для macOS.

## 📚 Документация

### Основные документы:
- **`PACKAGING_GUIDE.md`** - Полное руководство по упаковке (пошаговые инструкции)
- **`QUICK_CHECKLIST.md`** - Быстрый чеклист для опытных разработчиков
- **`CERTIFICATION_REQUIREMENTS.md`** - Требования для сертификации Apple

### Дополнительные файлы:
- **`packaging_requirements.md`** - Детальные технические требования
- **`quick_checklist.md`** - Краткий список действий

## 🚀 Быстрый старт

### Для новичков:
1. 📖 Прочитайте `PACKAGING_GUIDE.md` - полное руководство
2. 🔍 Изучите `CERTIFICATION_REQUIREMENTS.md` - требования Apple
3. ⚡ Используйте `QUICK_CHECKLIST.md` - для повторных сборок

### Для опытных разработчиков:
1. ⚡ Следуйте `QUICK_CHECKLIST.md` - быстрый процесс
2. 🔍 Проверьте `CERTIFICATION_REQUIREMENTS.md` - соответствие требованиям

## 📋 Предварительные требования

### Обязательные:
- ✅ **Apple Developer Account** ($99/год)
- ✅ **macOS 10.15+** (Catalina или новее)
- ✅ **Xcode Command Line Tools**
- ✅ **Python 3.9+**
- ✅ **PyInstaller** для создания bundle
- ✅ **SwitchAudioSource** для управления аудио

### Сертификаты:
- ✅ **Developer ID Application** - для подписания приложения
- ✅ **Developer ID Installer** - для подписания PKG
- ✅ **App-Specific Password** - для нотаризации

## 🔧 Процесс упаковки

### 1. Подготовка
```bash
# Установка зависимостей
brew install switchaudio-osx
pip3 install pyinstaller pyobjc-framework-CoreAudio
```

### 2. Сборка
```bash
# Создание .spec файла и сборка
pyinstaller audio_device_manager.spec --clean --noconfirm
```

### 3. Подписание
```bash
# Подписание приложения
codesign --force --sign "Developer ID Application: Your Name" --entitlements entitlements.plist "AudioDeviceManager.app"
```

### 4. Создание PKG
```bash
# Создание установочного пакета
pkgbuild --root dist --identifier com.yourcompany.audio-device-manager --version 1.0.0 "AudioDeviceManager.pkg"
```

### 5. Нотаризация
```bash
# Отправка на нотаризацию
xcrun notarytool submit "AudioDeviceManager.pkg" --apple-id "your-id@example.com" --password "app-password" --team-id "TEAM_ID" --wait
```

## ✅ Результат

После успешного выполнения всех шагов вы получите:
- 📦 **Подписанный PKG пакет** готовый к распространению
- 🏛️ **Нотаризованное приложение** прошедшее проверку Apple
- 🔒 **Безопасный код** соответствующий требованиям Gatekeeper
- 🚀 **Готовое к продакшену** решение

## 🆘 Поддержка

### Полезные ресурсы:
- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Apple Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [PyInstaller Documentation](https://pyinstaller.readthedocs.io/)

### Команды для диагностики:
```bash
# Проверка подписи
codesign --verify --verbose "AudioDeviceManager.app"

# Проверка Gatekeeper
spctl --assess --verbose "AudioDeviceManager.app"

# Проверка нотаризации
xcrun stapler validate "AudioDeviceManager.pkg"
```

---

**Готово к созданию профессионального macOS приложения!** 🎉