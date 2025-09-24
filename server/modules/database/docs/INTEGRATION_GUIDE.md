# 📚 Database Module - Руководство по Интеграции

## 🎯 Обзор

Database Module - это модуль для управления базой данных PostgreSQL. Модуль обеспечивает все CRUD операции для таблиц: users, sessions, commands, llm_answers, screenshots, performance_metrics, а также управление памятью пользователей.

## 🏗️ Архитектура

### Компоненты модуля:
- **DatabaseManager** - основной координатор
- **PostgreSQLProvider** - провайдер для работы с PostgreSQL
- **Config** - конфигурация модуля

### Принципы работы:
1. **CRUD операции** - создание, чтение, обновление, удаление записей
2. **Управление соединениями** - пул соединений для производительности
3. **Транзакции** - поддержка транзакций с rollback
4. **Управление памятью** - работа с short_term_memory и long_term_memory

## 🔧 Установка и Настройка

### 1. Установка зависимостей

```bash
# Основные зависимости
pip install psycopg2-binary

# Для разработки
pip install pytest pytest-asyncio
```

### 2. Базовая конфигурация

```python
config = {
    # Настройки подключения
    'host': 'localhost',
    'port': 5432,
    'database': 'voice_assistant_db',
    'username': 'postgres',
    'password': 'password',
    
    # Настройки пула соединений
    'min_connections': 1,
    'max_connections': 10,
    'connection_timeout': 30,
    'command_timeout': 60,
    
    # Настройки retry
    'retry_attempts': 3,
    'retry_delay': 1,
    'retry_backoff': 2,
    
    # Настройки производительности
    'fetch_size': 1000,
    'batch_size': 100,
    'enable_prepared_statements': True,
    'enable_connection_pooling': True
}
```

## 🚀 Использование

### Базовое использование

```python
from modules.database.core.database_manager import DatabaseManager

# Создание менеджера
manager = DatabaseManager(config)

# Инициализация
await manager.initialize()

# Создание пользователя
user_id = await manager.create_user(
    hardware_id_hash="abc123def456",
    metadata={"os": "macOS", "version": "14.0"}
)

print(f"User created: {user_id}")

# Очистка ресурсов
await manager.cleanup()
```

### Управление пользователями

```python
# Создание пользователя
user_id = await manager.create_user(
    hardware_id_hash="hardware_hash_123",
    metadata={
        "hardware_info": {
            "mac_address": "00:11:22:33:44:55",
            "serial_number": "C02ABC123DEF"
        },
        "system_info": {
            "os_version": "macOS 14.0",
            "app_version": "1.0.0"
        }
    }
)

# Получение пользователя
user = await manager.get_user_by_hardware_id("hardware_hash_123")
print(f"User found: {user['id']}")
```

### Управление сессиями

```python
# Создание сессии
session_id = await manager.create_session(
    user_id=user_id,
    metadata={
        "app_version": "1.0.0",
        "start_method": "push_to_talk"
    }
)

# Завершение сессии
success = await manager.end_session(session_id)
print(f"Session ended: {success}")
```

### Управление командами

```python
# Создание команды
command_id = await manager.create_command(
    session_id=session_id,
    prompt="Привет, как дела?",
    metadata={
        "input_method": "voice",
        "duration_ms": 2500,
        "confidence": 0.95
    },
    language="ru"
)

# Создание ответа LLM
answer_id = await manager.create_llm_answer(
    command_id=command_id,
    prompt="Привет, как дела?",
    response="Привет! У меня все хорошо, спасибо что спросил.",
    model_info={
        "model_name": "gemini-2.0-flash-exp",
        "provider": "google"
    },
    performance_metrics={
        "response_time_ms": 1200,
        "tokens_generated": 50
    }
)
```

### Управление скриншотами

```python
# Создание скриншота
screenshot_id = await manager.create_screenshot(
    session_id=session_id,
    file_path="/path/to/screenshot.png",
    file_url="https://example.com/screenshot.png",
    metadata={
        "dimensions": {"width": 1440, "height": 900},
        "format": "webp",
        "size_bytes": 250000
    }
)
```

### Управление метриками

```python
# Создание метрики производительности
metric_id = await manager.create_performance_metric(
    session_id=session_id,
    metric_type="response_time",
    metric_value={
        "total_time_ms": 1500,
        "processing_time_ms": 1200,
        "network_time_ms": 300
    }
)
```

## 📊 Аналитические запросы

### Статистика пользователя

```python
# Получение статистики пользователя
stats = await manager.get_user_statistics(user_id)
print(f"Total sessions: {stats['total_sessions']}")
print(f"Total commands: {stats['total_commands']}")
print(f"Total screenshots: {stats['total_screenshots']}")
print(f"Avg session duration: {stats['avg_session_duration_seconds']} seconds")
```

### Команды сессии

```python
# Получение всех команд сессии с ответами LLM
commands = await manager.get_session_commands(session_id)
for command in commands:
    print(f"Command: {command['prompt']}")
    print(f"Response: {command['llm_response']}")
    print(f"Model: {command['model_info']}")
    print(f"Performance: {command['performance_metrics']}")
```

## 🧠 Управление памятью

### Получение памяти пользователя

```python
# Получение памяти пользователя
memory = await manager.get_user_memory("hardware_hash_123")
print(f"Short-term memory: {memory['short']}")
print(f"Long-term memory: {memory['long']}")
```

### Обновление памяти пользователя

```python
# Обновление памяти пользователя
success = await manager.update_user_memory(
    hardware_id_hash="hardware_hash_123",
    short_memory="Current conversation context...",
    long_memory="Important user preferences and information..."
)
print(f"Memory updated: {success}")
```

### Очистка устаревшей памяти

```python
# Очистка краткосрочной памяти старше 24 часов
cleaned_count = await manager.cleanup_expired_short_term_memory(24)
print(f"Cleaned {cleaned_count} expired memory records")
```

### Статистика памяти

```python
# Получение статистики памяти
memory_stats = await manager.get_memory_statistics()
print(f"Total users: {memory_stats['total_users']}")
print(f"Users with memory: {memory_stats['users_with_memory']}")
print(f"Avg short memory size: {memory_stats['avg_short_memory_size']}")
print(f"Avg long memory size: {memory_stats['avg_long_memory_size']}")
```

### Пользователи с активной памятью

```python
# Получение пользователей с активной памятью
active_users = await manager.get_users_with_active_memory(limit=50)
for user in active_users:
    print(f"Hardware ID: {user['hardware_id_hash']}")
    print(f"Last update: {user['memory_updated_at']}")
    print(f"Short memory size: {user['short_memory_size']}")
    print(f"Long memory size: {user['long_memory_size']}")
```

## 🔧 Универсальные методы

### Выполнение произвольных запросов

```python
# Создание записи
result = await manager.execute_query(
    operation='create',
    table='users',
    data={
        'hardware_id_hash': 'test_hash',
        'metadata': {'test': 'data'}
    }
)

# Чтение записей
result = await manager.execute_query(
    operation='read',
    table='users',
    filters={'hardware_id_hash': 'test_hash'}
)

# Обновление записи
result = await manager.execute_query(
    operation='update',
    table='users',
    data={'metadata': {'updated': 'data'}},
    filters={'id': 'user-id-123'}
)

# Удаление записи
result = await manager.execute_query(
    operation='delete',
    table='users',
    filters={'id': 'user-id-123'}
)
```

## ⚙️ Конфигурация

### Полная конфигурация

```python
config = {
    # Настройки подключения
    'connection_string': 'postgresql://user:pass@host:port/db',
    'host': 'localhost',
    'port': 5432,
    'database': 'voice_assistant_db',
    'username': 'postgres',
    'password': 'password',
    
    # Настройки пула соединений
    'min_connections': 1,
    'max_connections': 10,
    'connection_timeout': 30,
    'command_timeout': 60,
    
    # Настройки retry
    'retry_attempts': 3,
    'retry_delay': 1,
    'retry_backoff': 2,
    
    # Настройки транзакций
    'autocommit': False,
    'isolation_level': 'READ_COMMITTED',
    'transaction_timeout': 300,
    
    # Настройки производительности
    'fetch_size': 1000,
    'batch_size': 100,
    'enable_prepared_statements': True,
    'enable_connection_pooling': True,
    
    # Настройки логирования
    'log_level': 'INFO',
    'log_queries': False,
    'log_slow_queries': True,
    'slow_query_threshold': 1000,
    
    # Настройки безопасности
    'ssl_mode': 'prefer',
    'ssl_cert': None,
    'ssl_key': None,
    'ssl_ca': None,
    'verify_ssl': True,
    
    # Настройки мониторинга
    'enable_metrics': True,
    'health_check_interval': 300,
    'connection_health_check': True,
    
    # Настройки очистки
    'cleanup_interval': 3600,
    'cleanup_batch_size': 1000,
    'enable_auto_cleanup': True,
    
    # Настройки схемы БД
    'schema_name': 'public',
    'table_prefix': '',
    'enable_migrations': True,
    'migration_path': 'database/migrations'
}
```

### Валидация конфигурации

```python
from modules.database.config import DatabaseConfig

config = DatabaseConfig(your_config)
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration validation failed")
```

## 📊 Мониторинг и Отладка

### Статус менеджера

```python
# Получение статуса менеджера
status = manager.get_status()
print(f"Initialized: {status['is_initialized']}")
print(f"PostgreSQL Provider: {status['postgresql_provider']['is_available']}")
print(f"Host: {status['postgresql_provider']['host']}")
print(f"Port: {status['postgresql_provider']['port']}")
print(f"Database: {status['postgresql_provider']['database']}")
```

### Метрики производительности

```python
# Получение метрик
metrics = manager.get_metrics()
postgresql_metrics = metrics['postgresql_provider']

print(f"Total requests: {postgresql_metrics['total_requests']}")
print(f"Successful requests: {postgresql_metrics['successful_requests']}")
print(f"Failed requests: {postgresql_metrics['failed_requests']}")
print(f"Success rate: {postgresql_metrics['success_rate']:.2%}")
print(f"Average response time: {postgresql_metrics['avg_response_time']:.2f}ms")
```

### Настройки конфигурации

```python
# Получение настроек безопасности
security_settings = manager.get_security_settings()
print(f"SSL Mode: {security_settings['ssl_mode']}")
print(f"Verify SSL: {security_settings['verify_ssl']}")
print(f"Password set: {security_settings['password_set']}")

# Получение настроек производительности
performance_settings = manager.get_performance_settings()
print(f"Fetch size: {performance_settings['fetch_size']}")
print(f"Batch size: {performance_settings['batch_size']}")
print(f"Max connections: {performance_settings['max_connections']}")

# Получение настроек мониторинга
monitoring_settings = manager.get_monitoring_settings()
print(f"Enable metrics: {monitoring_settings['enable_metrics']}")
print(f"Health check interval: {monitoring_settings['health_check_interval']}")
print(f"Log slow queries: {monitoring_settings['log_slow_queries']}")
```

## 🔒 Безопасность

### Настройки SSL

```python
# Конфигурация SSL
ssl_config = {
    'ssl_mode': 'require',
    'ssl_cert': '/path/to/client.crt',
    'ssl_key': '/path/to/client.key',
    'ssl_ca': '/path/to/ca.crt',
    'verify_ssl': True
}

manager = DatabaseManager(ssl_config)
await manager.initialize()
```

### Переменные окружения

```python
# Использование переменных окружения
import os

config = {
    'connection_string': os.getenv('DATABASE_URL'),
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5432)),
    'database': os.getenv('DB_NAME', 'voice_assistant_db'),
    'username': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', ''),
    'ssl_mode': os.getenv('DB_SSL_MODE', 'prefer')
}

manager = DatabaseManager(config)
await manager.initialize()
```

## ⚠️ Обработка Ошибок

### Типы ошибок:
1. **Подключение**: проблемы с подключением к БД
2. **Транзакции**: ошибки commit/rollback
3. **Запросы**: SQL ошибки, неверные данные
4. **Пул соединений**: превышение лимитов

### Обработка в коде:

```python
try:
    user_id = await manager.create_user(hardware_id_hash, metadata)
    if user_id:
        print(f"User created: {user_id}")
    else:
        print("Failed to create user")
except Exception as e:
    logger.error(f"Database error: {e}")
    # Fallback или уведомление об ошибке
```

### Обработка транзакций:

```python
try:
    # Создание пользователя
    user_id = await manager.create_user(hardware_id_hash)
    
    # Создание сессии
    session_id = await manager.create_session(user_id)
    
    # Создание команды
    command_id = await manager.create_command(session_id, prompt)
    
    print("All operations completed successfully")
    
except Exception as e:
    logger.error(f"Transaction error: {e}")
    # Автоматический rollback через провайдер
```

## 🧪 Тестирование

### Запуск тестов:

```bash
# Все тесты модуля
python -m pytest modules/database/tests/

# Конкретный тест
python -m pytest modules/database/tests/test_database_manager.py

# С покрытием
python -m pytest modules/database/tests/ --cov=modules.database
```

### Тестирование с реальной БД:

```python
# Тест с реальной БД
import asyncio
from modules.database.core.database_manager import DatabaseManager

async def test_real_database():
    config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'username': 'test_user',
        'password': 'test_pass'
    }
    
    manager = DatabaseManager(config)
    await manager.initialize()
    
    try:
        # Создание пользователя
        user_id = await manager.create_user('test_hash')
        assert user_id is not None
        
        # Получение пользователя
        user = await manager.get_user_by_hardware_id('test_hash')
        assert user is not None
        assert user['id'] == user_id
        
        print("Database test passed")
        
    finally:
        await manager.cleanup()

# Запуск теста
asyncio.run(test_real_database())
```

### Тестирование с моками:

```python
# Тест с моками
from unittest.mock import AsyncMock, patch

async def test_with_mocks():
    with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
        mock_provider = AsyncMock()
        mock_provider.initialize = AsyncMock(return_value=True)
        mock_provider.create_user = AsyncMock(return_value='user-id-123')
        mock_provider_class.return_value = mock_provider
        
        manager = DatabaseManager({})
        await manager.initialize()
        
        user_id = await manager.create_user('test_hash')
        assert user_id == 'user-id-123'
        
        print("Mock test passed")

asyncio.run(test_with_mocks())
```

## 🔄 Интеграция с существующим кодом

### Замена существующего DatabaseManager:

```python
# Старый код
from database.database_manager import DatabaseManager as OldDatabaseManager

# Новый код
from modules.database.core.database_manager import DatabaseManager

# Инициализация
manager = DatabaseManager(config)
await manager.initialize()

# Использование (API остается тем же)
user_id = manager.create_user(hardware_id_hash, metadata)
session_id = manager.create_session(user_id, metadata)
command_id = manager.create_command(session_id, prompt, metadata, language)
```

### Использование в gRPC сервере:

```python
# В grpc_server.py
from modules.database.core.database_manager import DatabaseManager

class StreamingService:
    def __init__(self):
        self.db_manager = DatabaseManager(config)
    
    async def initialize(self):
        await self.db_manager.initialize()
    
    async def StreamAudio(self, request, context):
        # Создание пользователя
        user = await self.db_manager.get_user_by_hardware_id(request.hardware_id)
        if not user:
            user_id = await self.db_manager.create_user(request.hardware_id)
        else:
            user_id = user['id']
        
        # Создание сессии
        session_id = await self.db_manager.create_session(user_id)
        
        try:
            # Выполнение операции
            async for audio_chunk in self.process_audio(request.text):
                yield audio_chunk
                
        finally:
            # Завершение сессии
            await self.db_manager.end_session(session_id)
```

## 🚨 Устранение Неполадок

### Частые проблемы:

1. **"DatabaseManager not initialized"**
   - Проверьте вызов `await manager.initialize()`
   - Проверьте валидность конфигурации

2. **"Connection refused"**
   - Проверьте настройки host, port, database
   - Проверьте доступность PostgreSQL сервера
   - Проверьте права доступа пользователя

3. **"Pool exhausted"**
   - Увеличьте max_connections
   - Проверьте правильность закрытия соединений
   - Проверьте длительность операций

4. **"Transaction timeout"**
   - Увеличьте transaction_timeout
   - Оптимизируйте медленные запросы
   - Проверьте блокировки в БД

### Логирование:

```python
import logging

# Включение подробного логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('modules.database')
```

### Диагностика:

```python
# Проверка статуса всех компонентов
status = manager.get_status()
print(f"Manager status: {status['is_initialized']}")
print(f"Provider status: {status['postgresql_provider']['is_available']}")
print(f"Pool status: {status['postgresql_provider']['pool_available']}")

# Проверка метрик
metrics = manager.get_metrics()
print(f"Total requests: {metrics['postgresql_provider']['total_requests']}")
print(f"Success rate: {metrics['postgresql_provider']['success_rate']:.2%}")

# Проверка здоровья провайдера
health = await manager.postgresql_provider.health_check()
print(f"Provider healthy: {health}")
```

## 🔄 Обновления

### Обновление модуля:
1. Остановите менеджер: `await manager.cleanup()`
2. Обновите код
3. Перезапустите: `await manager.initialize()`

### Обновление конфигурации:
1. Измените конфигурацию
2. Перезапустите менеджер
3. Проверьте статус: `manager.get_status()`

### Миграция данных:
```python
# При изменении структуры БД
async def migrate_data():
    # Получение старых данных
    old_data = await manager.execute_query('read', 'old_table', {})
    
    # Преобразование данных
    new_data = transform_data(old_data['data'])
    
    # Сохранение в новую таблицу
    for record in new_data:
        await manager.execute_query('create', 'new_table', record)
```

## 📞 Поддержка

### Полезные команды:

```python
# Получение сводки
summary = manager.get_summary()
print(summary)

# Сброс метрик
manager.reset_metrics()

# Получение всех настроек
security = manager.get_security_settings()
performance = manager.get_performance_settings()
monitoring = manager.get_monitoring_settings()
cleanup = manager.get_cleanup_settings()
schema = manager.get_schema_settings()
```

### Контакты:
- Документация: `modules/database/docs/`
- Тесты: `modules/database/tests/`
- Логи: проверьте логи приложения

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: Python 3.11+, AsyncIO, PostgreSQL 15+
