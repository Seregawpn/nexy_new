# Настройка сертификатов для voice_recognition

## 🔐 **ТРЕБУЕМЫЕ СЕРТИФИКАТЫ**

### 1. **Developer ID Application Certificate**
- **Назначение**: Подпись приложения для распространения вне App Store
- **Тип**: Developer ID Application
- **Срок действия**: 1 год
- **Где получить**: Apple Developer Portal → Certificates, Identifiers & Profiles

### 2. **Developer ID Installer Certificate**
- **Назначение**: Подпись PKG пакетов
- **Тип**: Developer ID Installer
- **Срок действия**: 1 год
- **Где получить**: Apple Developer Portal → Certificates, Identifiers & Profiles

## 📋 **ПОШАГОВАЯ НАСТРОЙКА**

### Шаг 1: Создание сертификатов в Apple Developer Portal

1. **Войдите в Apple Developer Portal**
   - Перейдите на https://developer.apple.com
   - Войдите в свой аккаунт

2. **Создайте Developer ID Application Certificate**
   - Certificates, Identifiers & Profiles → Certificates
   - Нажмите "+" для создания нового сертификата
   - Выберите "Developer ID Application"
   - Следуйте инструкциям для создания CSR

3. **Создайте Developer ID Installer Certificate**
   - Certificates, Identifiers & Profiles → Certificates
   - Нажмите "+" для создания нового сертификата
   - Выберите "Developer ID Installer"
   - Следуйте инструкциям для создания CSR

### Шаг 2: Установка сертификатов в Keychain

1. **Скачайте сертификаты**
   - Скачайте .cer файлы из Apple Developer Portal
   - Дважды кликните для установки в Keychain

2. **Проверьте установку**
   ```bash
   security find-identity -v -p codesigning
   ```

3. **Экспортируйте приватные ключи**
   - Откройте Keychain Access
   - Найдите установленные сертификаты
   - Экспортируйте как .p12 файлы с паролем

### Шаг 3: Настройка переменных окружения

```bash
# Добавьте в ~/.zshrc или ~/.bash_profile
export DEVELOPER_ID="Developer ID Application: Your Name (TEAM_ID)"
export INSTALLER_ID="Developer ID Installer: Your Name (TEAM_ID)"
export APPLE_ID="your@email.com"
export APP_PASSWORD="app-specific-password"
export TEAM_ID="YOUR_TEAM_ID"
```

### Шаг 4: Создание App-Specific Password

1. **Войдите в Apple ID**
   - Перейдите на https://appleid.apple.com
   - Войдите в свой аккаунт

2. **Создайте App-Specific Password**
   - Sign-In and Security → App-Specific Passwords
   - Нажмите "Generate Password"
   - Введите описание: "Nexy Voice Recognition Notarization"
   - Сохраните пароль

## 🔧 **КОМАНДЫ ДЛЯ ПРОВЕРКИ**

### Проверка сертификатов
```bash
# Список всех сертификатов
security find-identity -v -p codesigning

# Проверка конкретного сертификата
security find-identity -v -p codesigning | grep "Developer ID Application"

# Проверка Keychain
security list-keychains
```

### Проверка подписи
```bash
# Проверка подписи приложения
codesign --verify --verbose "Voice Recognition.app"

# Проверка подписи PKG
pkgutil --check-signature "Voice Recognition.pkg"
```

### Проверка нотаризации
```bash
# Проверка тикета нотаризации
xcrun stapler validate "Voice Recognition.app"

# Проверка истории нотаризации
xcrun notarytool history --apple-id "$APPLE_ID" --password "$APP_PASSWORD" --team-id "$TEAM_ID"
```

## ⚠️ **ВАЖНЫЕ ЗАМЕЧАНИЯ**

### Безопасность
- **Никогда не коммитьте** сертификаты в Git
- **Используйте** .gitignore для .p12 файлов
- **Храните** пароли в безопасном месте
- **Регулярно обновляйте** сертификаты

### Сроки действия
- **Developer ID Application**: 1 год
- **Developer ID Installer**: 1 год
- **App-Specific Password**: Без срока действия
- **Team ID**: Постоянный

### Troubleshooting
- **Ошибка подписи**: Проверьте сертификат в Keychain
- **Ошибка нотаризации**: Проверьте App-Specific Password
- **Ошибка валидации**: Проверьте entitlements.plist

## 📚 **ДОПОЛНИТЕЛЬНЫЕ РЕСУРСЫ**

- [Apple Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
- [Entitlements Reference](https://developer.apple.com/documentation/bundleresources/entitlements)
- [Info.plist Reference](https://developer.apple.com/documentation/bundleresources/information_property_list)
