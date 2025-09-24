# gRPC Service Module - Инструкция по Интеграции

## 🎯 Обзор

gRPC Service Module - это универсальный сервис для интеграции всех модулей через стандартизированный gRPC протокол. Обеспечивает единообразное взаимодействие между клиентом и сервером.

## 🏗️ Архитектура

### Универсальный Стандарт Взаимодействия

```
Client → gRPC Request → GrpcServiceManager → Universal Integrations → Modules → Response
```

### Компоненты

1. **GrpcServiceManager** - основной координатор
2. **Universal Integrations** - стандартизированные интеграции для каждого модуля
3. **Universal Module Interface** - универсальный интерфейс для всех модулей
4. **Universal gRPC Integration** - универсальный интерфейс для gRPC интеграций

## 📋 Протокол gRPC

### StreamAudio (StreamRequest → StreamResponse)

**Входящие данные:**
- `prompt` (string) - текстовая команда пользователя
- `screenshot` (optional string) - Base64 WebP скриншот экрана
- `screen_width/height` (optional int32) - размеры экрана
- `hardware_id` (string) - уникальный ID оборудования (ОБЯЗАТЕЛЬНО)
- `session_id` (optional string) - ID сессии для отслеживания

**Исходящие данные:**
- `text_chunk` (string) - текстовый чанк от LLM
- `audio_chunk` (AudioChunk) - аудио данные
- `end_message` (string) - сообщение о завершении
- `error_message` (string) - сообщение об ошибке

### InterruptSession (InterruptRequest → InterruptResponse)

**Входящие данные:**
- `hardware_id` (string) - ID оборудования для прерывания

**Исходящие данные:**
- `success` (bool) - успешность операции
- `interrupted_sessions` (repeated string) - список прерванных сессий
- `message` (string) - сообщение о результате

## 🔧 Использование

### Инициализация

```python
from modules.grpc_service import GrpcServiceManager
from modules.grpc_service.config import GrpcServiceConfig

# Создание конфигурации
config = GrpcServiceConfig()

# Создание менеджера
grpc_manager = GrpcServiceManager(config)

# Инициализация
await grpc_manager.initialize()
```

### Обработка StreamRequest

```python
# Данные запроса
request_data = {
    "prompt": "Привет, как дела?",
    "hardware_id": "unique_hardware_id_123",
    "screenshot": "base64_screenshot_data",
    "screen_width": 1920,
    "screen_height": 1080,
    "session_id": "session_456"
}

# Обработка через менеджер
async for result in grpc_manager.process_stream_request(request_data):
    if result["type"] == "text_chunk":
        print(f"Text: {result['content']}")
    elif result["type"] == "audio_chunk":
        print(f"Audio: {result['content']['audio_data']}")
    elif result["type"] == "error":
        print(f"Error: {result['content']}")
```

### Прерывание сессии

```python
# Прерывание сессии
interrupt_result = await grpc_manager.interrupt_session("unique_hardware_id_123")
print(f"Interrupt success: {interrupt_result['success']}")
print(f"Interrupted sessions: {interrupt_result['interrupted_sessions']}")
```

## 🔗 Интеграция с Модулями

### Text Processing Integration

```python
# Автоматически интегрируется при инициализации
# Обрабатывает промпт и возвращает текстовые чанки
```

### Audio Generation Integration

```python
# Автоматически интегрируется при инициализации
# Генерирует аудио из текста и возвращает аудио чанки
```

### Session Management Integration

```python
# Автоматически интегрируется при инициализации
# Управляет сессиями и Hardware ID
```

### Database Integration

```python
# Автоматически интегрируется при инициализации
# Сохраняет и извлекает данные пользователя
```

### Memory Management Integration

```python
# Автоматически интегрируется при инициализации
# Управляет памятью и контекстом пользователя
```

## ⚙️ Конфигурация

### Переменные окружения

```bash
# gRPC настройки
GRPC_HOST=0.0.0.0
GRPC_PORT=50051
USE_TLS=false

# Настройки сессий
MAX_SESSIONS=100
SESSION_TIMEOUT=300

# Настройки прерывания
INTERRUPT_CHECK_INTERVAL=0.1
MAX_PROCESSING_TIME=30

# Настройки логирования
LOG_LEVEL=INFO
LOG_REQUESTS=true

# Настройки производительности
MAX_CONCURRENT_REQUESTS=10
REQUEST_TIMEOUT=60
```

### Конфигурация модулей

```python
# В config.py можно настроить включение/выключение модулей
modules = {
    "text_processing": {"enabled": True, "timeout": 30},
    "audio_generation": {"enabled": True, "timeout": 15},
    "session_management": {"enabled": True, "timeout": 5},
    "database": {"enabled": True, "timeout": 10},
    "memory_management": {"enabled": True, "timeout": 10}
}
```

## 🧪 Тестирование

### Unit тесты

```python
# Тестирование GrpcServiceManager
pytest modules/grpc_service/tests/test_grpc_service_manager.py

# Тестирование интеграций
pytest modules/grpc_service/tests/test_integrations.py
```

### Integration тесты

```python
# Тестирование полного цикла
pytest modules/grpc_service/tests/test_integration.py
```

### Universal тесты

```python
# Тестирование соответствия универсальным стандартам
pytest modules/grpc_service/universal_tests/test_universal_compliance.py
```

## 📊 Мониторинг

### Статус сервиса

```python
# Получение статуса
status = grpc_manager.get_status()
print(f"Active sessions: {status['active_sessions']}")
print(f"Modules: {status['modules']}")
print(f"Integrations: {status['integrations']}")
```

### Метрики

```python
# Каждый модуль и интеграция предоставляют метрики
for module_name, module in grpc_manager.modules.items():
    metrics = module.get_metrics()
    print(f"{module_name}: {metrics}")
```

## 🔒 Безопасность

### Прерывание сессий

- Глобальный флаг прерывания для мгновенной отмены
- Проверка прерывания в каждой итерации
- Автоматическая очистка ресурсов при прерывании

### Таймауты

- Максимальное время обработки: 30 секунд
- Таймауты для каждого модуля
- Автоматическое прерывание при превышении лимитов

## 🚀 Развертывание

### Запуск сервера

```python
# В main.py
from modules.grpc_service import GrpcServiceManager

async def main():
    grpc_manager = GrpcServiceManager()
    await grpc_manager.initialize()
    
    # Запуск gRPC сервера
    # (код запуска сервера)
```

### Docker

```dockerfile
# В Dockerfile
COPY modules/grpc_service/ /app/modules/grpc_service/
COPY integration/core/ /app/integration/core/
```

## 📝 Логирование

### Уровни логирования

- **INFO** - общая информация о работе
- **WARNING** - предупреждения и прерывания
- **ERROR** - ошибки обработки
- **DEBUG** - детальная отладочная информация

### Формат логов

```
2025-01-15 14:30:00 - gRPC Service - INFO - Session session_123 registered
2025-01-15 14:30:01 - gRPC Service - WARNING - Interrupting session for hardware_id: abc123
2025-01-15 14:30:02 - gRPC Service - ERROR - Text processing error: Connection timeout
```

## 🔄 Обновления

### Добавление нового модуля

1. Создать модуль по `UniversalModuleInterface`
2. Создать интеграцию по `UniversalGrpcIntegration`
3. Добавить в `GrpcServiceManager._create_integration()`
4. Добавить конфигурацию в `config.py`
5. Написать тесты

### Модификация существующего модуля

1. Обновить модуль, сохранив совместимость с интерфейсом
2. Обновить интеграцию при необходимости
3. Обновить тесты
4. Проверить совместимость с клиентом

## 📞 Поддержка

### Отладка

```python
# Включение детального логирования
import logging
logging.getLogger("modules.grpc_service").setLevel(logging.DEBUG)

# Проверка статуса
status = grpc_manager.get_status()
print(json.dumps(status, indent=2))
```

### Мониторинг производительности

```python
# Метрики каждого модуля
for name, module in grpc_manager.modules.items():
    metrics = module.get_metrics()
    print(f"{name}: {metrics['success_rate']:.2%} success rate")
```

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: gRPC Service Module v1.0
