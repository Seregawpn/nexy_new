# Настройка сертификатов для модуля hardware_id

## Обзор

Модуль `hardware_id` требует подписи и нотаризации для корректной работы на macOS. Этот документ описывает процесс настройки необходимых сертификатов.

## Необходимые сертификаты

### 1. Developer ID Application Certificate
- **Назначение**: Подпись приложения для распространения вне App Store
- **Тип**: `Developer ID Application`
- **Срок действия**: 1 год
- **Где получить**: Apple Developer Portal

### 2. Apple ID и App-Specific Password
- **Назначение**: Аутентификация для нотаризации
- **Требования**: Активный Apple ID с двухфакторной аутентификацией
- **Где получить**: Apple ID настройки

## Пошаговая настройка

### Шаг 1: Получение Developer ID Application Certificate

1. Войдите в [Apple Developer Portal](https://developer.apple.com)
2. Перейдите в раздел "Certificates, Identifiers & Profiles"
3. Выберите "Certificates" → "Create a Certificate"
4. Выберите "Developer ID Application"
5. Следуйте инструкциям для создания CSR (Certificate Signing Request)
6. Загрузите и установите сертификат в Keychain Access

### Шаг 2: Настройка App-Specific Password

1. Войдите в [Apple ID настройки](https://appleid.apple.com)
2. Перейдите в раздел "App-Specific Passwords"
3. Создайте новый пароль для нотаризации
4. Сохраните пароль в безопасном месте

### Шаг 3: Настройка переменных окружения

Создайте файл `.env` в корневой директории проекта:

```bash
# Apple ID для нотаризации
APPLE_ID="your_apple_id@example.com"

# App-Specific Password
APP_SPECIFIC_PASSWORD="your_app_specific_password"

# Team ID (найти в Apple Developer Portal)
TEAM_ID="5NKLL2CLB9"

# Имя сертификата (как в Keychain Access)
DEVELOPER_ID_APPLICATION_CERT_NAME="Developer ID Application: Sergiy Zasorin (5NKLL2CLB9)"
```

### Шаг 4: Проверка установки

Запустите команду для проверки сертификатов:

```bash
# Проверка сертификатов
security find-identity -v -p codesigning

# Проверка notarytool
xcrun notarytool --help
```

## Конфигурация для hardware_id

### Entitlements

Модуль `hardware_id` требует следующие entitlements:

```xml
<key>com.apple.security.app-sandbox</key>
<true/>
<key>com.apple.security.automation.apple-events</key>
<true/>
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
<key>com.apple.security.network.client</key>
<true/>
<key>com.apple.security.device.usb</key>
<true/>
<key>com.apple.security.temporary-exception.apple-events</key>
<true/>
<key>com.apple.security.temporary-exception.system-information</key>
<true/>
```

### Info.plist

Основные настройки для `Info.plist`:

```xml
<key>CFBundleIdentifier</key>
<string>com.nexy.hardware.id</string>
<key>NSAppleEventsUsageDescription</key>
<string>This app needs access to Apple Events for hardware information retrieval.</string>
<key>NSSystemAdministrationUsageDescription</key>
<string>This app needs access to system information for hardware identification.</string>
```

## Процесс сборки и подписи

### 1. Сборка приложения

```bash
cd /Users/sergiyzasorin/Desktop/Development/Nexy
./client/hardware_id/macos/scripts/build_macos.sh
```

### 2. Подпись и нотаризация

```bash
./client/hardware_id/macos/scripts/sign_and_notarize.sh
```

## Устранение неполадок

### Ошибка: "No identity found"
- Убедитесь, что сертификат установлен в Keychain Access
- Проверьте правильность имени сертификата в переменной `DEVELOPER_ID_APPLICATION_CERT_NAME`

### Ошибка: "Invalid credentials"
- Проверьте правильность `APPLE_ID` и `APP_SPECIFIC_PASSWORD`
- Убедитесь, что App-Specific Password действителен

### Ошибка: "Team ID not found"
- Проверьте правильность `TEAM_ID` в Apple Developer Portal
- Убедитесь, что ваш Apple ID имеет доступ к команде

### Ошибка: "Entitlements not found"
- Убедитесь, что файл entitlements существует и корректен
- Проверьте права доступа к файлу entitlements

## Безопасность

### Рекомендации по безопасности

1. **Никогда не коммитьте файл `.env`** в репозиторий
2. **Используйте App-Specific Password** вместо основного пароля Apple ID
3. **Регулярно обновляйте сертификаты** (каждый год)
4. **Храните сертификаты в безопасном месте**

### Ротация сертификатов

- Сертификаты Developer ID действуют 1 год
- Начните процесс обновления за 30 дней до истечения
- Обновите переменные окружения после получения нового сертификата

## Поддержка

При возникновении проблем:

1. Проверьте логи сборки и подписи
2. Убедитесь, что все зависимости установлены
3. Проверьте права доступа к файлам
4. Обратитесь к документации Apple Developer

## Дополнительные ресурсы

- [Apple Developer Documentation](https://developer.apple.com/documentation)
- [Code Signing Guide](https://developer.apple.com/library/archive/documentation/Security/Conceptual/CodeSigningGuide/)
- [Notarization Guide](https://developer.apple.com/documentation/security/notarizing_macos_software_before_distribution)
