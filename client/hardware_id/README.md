# Модуль Hardware ID

Упрощенный модуль для получения Hardware UUID на macOS. Предназначен для идентификации устройства в системе Nexy.

## Особенности

- ✅ **Только macOS** - оптимизирован для macOS
- ✅ **Только Hardware UUID** - получает только UUID оборудования
- ✅ **Кэширование** - быстрый доступ к сохраненному UUID
- ✅ **Валидация** - проверка корректности UUID
- ✅ **Fallback** - генерация случайного UUID при необходимости
- ✅ **macOS требования** - полная поддержка подписи и нотаризации

## Структура модуля

```
hardware_id/
├── core/                    # Основные компоненты
│   ├── types.py            # Типы данных
│   ├── hardware_identifier.py # Главный класс
│   └── config.py           # Конфигурация
├── macos/                  # macOS компоненты
│   ├── system_profiler.py  # system_profiler bridge
│   └── hardware_detector.py # Детектор оборудования
├── utils/                  # Утилиты
│   ├── caching.py          # Кэширование
│   └── validation.py       # Валидация
├── tests/                  # Тесты
│   └── test_hardware_id.py
├── macos/                  # macOS требования
│   ├── entitlements/       # Entitlements
│   ├── info/              # Info.plist
│   ├── scripts/           # Скрипты сборки
│   ├── packaging/         # Зависимости
│   └── notarization/      # Конфигурация нотаризации
└── README.md
```

## Быстрый старт

### Установка

```python
# Импорт модуля
from hardware_id import get_hardware_id, get_hardware_id_result

# Получение Hardware ID
hardware_id = get_hardware_id()
print(f"Hardware ID: {hardware_id}")

# Получение полного результата
result = get_hardware_id_result()
print(f"Status: {result.status}")
print(f"Source: {result.source}")
print(f"Cached: {result.cached}")
```

### Расширенное использование

```python
from hardware_id import HardwareIdentifier, HardwareIdConfig

# Создание с кастомной конфигурацией
config = HardwareIdConfig(
    cache_enabled=True,
    cache_ttl_seconds=86400 * 7,  # 7 дней
    validate_uuid_format=True,
    fallback_to_random=True
)

identifier = HardwareIdentifier(config)

# Получение Hardware ID
result = identifier.get_hardware_id()

# Получение информации об оборудовании
hardware_info = identifier.get_hardware_info()

# Валидация UUID
is_valid = identifier.validate_hardware_id("12345678-1234-1234-1234-123456789012")
```

## API Reference

### Основные функции

#### `get_hardware_id(force_regenerate: bool = False) -> str`
Получает Hardware ID с кэшированием.

**Параметры:**
- `force_regenerate` - принудительно пересоздать ID

**Возвращает:**
- `str` - Hardware ID

#### `get_hardware_id_result(force_regenerate: bool = False) -> HardwareIdResult`
Получает полный результат получения Hardware ID.

**Параметры:**
- `force_regenerate` - принудительно пересоздать ID

**Возвращает:**
- `HardwareIdResult` - полный результат

#### `get_hardware_info() -> dict`
Получает информацию об оборудовании.

**Возвращает:**
- `dict` - информация об оборудовании

#### `clear_hardware_id_cache()`
Очищает кэш Hardware ID.

#### `validate_hardware_id(uuid_str: str) -> bool`
Валидирует Hardware ID.

**Параметры:**
- `uuid_str` - UUID для валидации

**Возвращает:**
- `bool` - True если UUID валиден

### Типы данных

#### `HardwareIdResult`
Результат получения Hardware ID.

```python
@dataclass
class HardwareIdResult:
    uuid: str                                    # Hardware UUID
    status: HardwareIdStatus                     # Статус получения
    source: str                                  # Источник (cache, system_profiler, fallback)
    cached: bool                                 # Загружен из кэша
    error_message: Optional[str] = None          # Сообщение об ошибке
    metadata: Optional[Dict[str, Any]] = None    # Дополнительные данные
```

#### `HardwareIdStatus`
Статус получения Hardware ID.

```python
class HardwareIdStatus(Enum):
    SUCCESS = "success"      # Успешно получен
    CACHED = "cached"        # Загружен из кэша
    ERROR = "error"          # Ошибка
    NOT_FOUND = "not_found"  # Не найден
```

#### `HardwareIdConfig`
Конфигурация модуля.

```python
@dataclass
class HardwareIdConfig:
    cache_enabled: bool = True                    # Включить кэширование
    cache_file_path: str = "~/.voice_assistant/hardware_id_cache.json"
    cache_ttl_seconds: int = 86400 * 30          # TTL кэша (30 дней)
    system_profiler_timeout: int = 5              # Таймаут system_profiler
    validate_uuid_format: bool = True             # Валидировать формат UUID
    fallback_to_random: bool = False              # Fallback на случайный UUID
```

## Конфигурация

### Файл конфигурации

Модуль автоматически создает файл конфигурации в `~/.voice_assistant/hardware_id_config.json`:

```json
{
  "hardware_id": {
    "cache_enabled": true,
    "cache_file_path": "~/.voice_assistant/hardware_id_cache.json",
    "cache_ttl_seconds": 2592000,
    "system_profiler_timeout": 5,
    "validate_uuid_format": true,
    "fallback_to_random": false
  }
}
```

### Кэш

Hardware ID кэшируется в файле `~/.voice_assistant/hardware_id_cache.json`:

```json
{
  "uuid": "12345678-1234-1234-1234-123456789012",
  "cached_at": "2024-01-01T00:00:00",
  "ttl_seconds": 2592000,
  "version": "1.0",
  "metadata": {
    "source": "system_profiler",
    "detection_method": "system_profiler"
  }
}
```

## Тестирование

### Запуск тестов

```bash
cd client/hardware_id
python -m pytest tests/test_hardware_id.py -v
```

### Тестирование вручную

```python
# Тест получения Hardware ID
from hardware_id import get_hardware_id, get_hardware_id_result

# Получение ID
hardware_id = get_hardware_id()
print(f"Hardware ID: {hardware_id}")

# Получение результата
result = get_hardware_id_result()
print(f"Status: {result.status}")
print(f"Source: {result.source}")
print(f"Cached: {result.cached}")

# Валидация
from hardware_id import validate_hardware_id
is_valid = validate_hardware_id(hardware_id)
print(f"Valid: {is_valid}")
```

## macOS требования

### Entitlements

Модуль требует следующие entitlements:

- `com.apple.security.app-sandbox` - App Sandbox
- `com.apple.security.automation.apple-events` - Apple Events
- `com.apple.security.files.user-selected.read-write` - Файловый доступ
- `com.apple.security.network.client` - Сетевой доступ
- `com.apple.security.device.usb` - USB устройства
- `com.apple.security.temporary-exception.apple-events` - Временное исключение для Apple Events
- `com.apple.security.temporary-exception.system-information` - Временное исключение для системной информации

### Сборка и подпись

```bash
# Сборка
./client/hardware_id/macos/scripts/build_macos.sh

# Подпись и нотаризация
./client/hardware_id/macos/scripts/sign_and_notarize.sh
```

## Устранение неполадок

### Ошибка: "system_profiler не найден"
- Убедитесь, что вы на macOS
- Проверьте, что system_profiler доступен в PATH

### Ошибка: "Hardware UUID не найден"
- Проверьте права доступа к system_profiler
- Убедитесь, что система поддерживает Hardware UUID

### Ошибка: "Кэш недоступен"
- Проверьте права доступа к директории `~/.voice_assistant/`
- Убедитесь, что достаточно места на диске

### Ошибка: "UUID невалиден"
- Проверьте формат UUID
- Убедитесь, что UUID не является случайным

## Логирование

Модуль использует стандартное логирование Python:

```python
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Получение Hardware ID
from hardware_id import get_hardware_id
hardware_id = get_hardware_id()
```

## Производительность

### Кэширование

- Первый запрос: ~100-500ms (зависит от системы)
- Последующие запросы: ~1-5ms (из кэша)
- TTL кэша: 30 дней по умолчанию

### Оптимизация

- Используйте кэширование для быстрого доступа
- Настройте подходящий TTL для вашего случая
- Отключите валидацию для максимальной производительности

## Безопасность

### Приватность

- Модуль не собирает личные данные
- Hardware UUID не содержит личной информации
- Кэш хранится локально

### Безопасность

- Использует system_profiler для получения UUID
- Валидирует полученные данные
- Поддерживает sandbox на macOS

## Лицензия

Модуль является частью проекта Nexy и распространяется под той же лицензией.

## Поддержка

При возникновении проблем:

1. Проверьте логи модуля
2. Убедитесь, что все зависимости установлены
3. Проверьте права доступа к файлам
4. Обратитесь к документации Apple Developer

## Changelog

### v1.0.0
- Первоначальная версия
- Поддержка только Hardware UUID
- Кэширование и валидация
- macOS требования и подпись
