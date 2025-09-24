# 📚 Session Management Module - Руководство по Интеграции

## 🎯 Обзор

Session Management Module - это модуль для управления активными сессиями пользователей, отслеживания Hardware ID и обеспечения прерывания операций. Модуль обеспечивает централизованное управление сессиями с поддержкой глобальных прерываний.

## 🏗️ Архитектура

### Компоненты модуля:
- **SessionManager** - основной координатор
- **HardwareIDProvider** - генерация и управление Hardware ID
- **SessionTracker** - отслеживание активных сессий
- **Config** - конфигурация модуля

### Принципы работы:
1. **Уникальные Hardware ID** - генерация на основе аппаратных характеристик
2. **Управление сессиями** - создание, отслеживание и прерывание сессий
3. **Глобальные прерывания** - возможность прервать все активные сессии
4. **Автоматическая очистка** - удаление устаревших сессий

## 🔧 Установка и Настройка

### 1. Установка зависимостей

```bash
# Основные зависимости (уже включены в Python)
# uuid, platform, hashlib, asyncio

# Для разработки
pip install pytest pytest-asyncio
```

### 2. Базовая конфигурация

```python
config = {
    # Hardware ID настройки
    'hardware_id_cache_file': 'hardware_id.cache',
    'hardware_id_length': 32,
    'hardware_id_charset': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    
    # Настройки сессий
    'session_timeout': 3600,  # 1 час
    'session_cleanup_interval': 300,  # 5 минут
    'max_concurrent_sessions': 100,
    'session_heartbeat_interval': 30,  # 30 секунд
    
    # Настройки прерываний
    'interrupt_timeout': 5,  # 5 секунд
    'interrupt_cleanup_delay': 10,  # 10 секунд
    'global_interrupt_enabled': True,
    
    # Настройки отслеживания
    'tracking_enabled': True,
    'track_user_agents': True,
    'track_ip_addresses': False,
    'track_timestamps': True
}
```

## 🚀 Использование

### Базовое использование

```python
from modules.session_management.core.session_manager import SessionManager

# Создание менеджера
manager = SessionManager(config)

# Инициализация
await manager.initialize()

# Создание сессии
session_data = await manager.create_session(
    user_agent="Mozilla/5.0...",
    ip_address="192.168.1.1",
    context={"user_preferences": {"language": "en"}}
)

print(f"Session created: {session_data['session_id']}")
print(f"Hardware ID: {session_data['hardware_id']}")

# Очистка ресурсов
await manager.cleanup()
```

### Управление сессиями

```python
# Получение статуса сессии
status = await manager.get_session_status(session_id)
print(f"Session status: {status['status']}")
print(f"Last activity: {status['last_activity']}")

# Прерывание конкретной сессии
success = await manager.interrupt_session(session_id, "user_request")
print(f"Session interrupted: {success}")

# Прерывание всех сессий
count = await manager.interrupt_all_sessions("system_shutdown")
print(f"Interrupted {count} sessions")
```

### Получение Hardware ID

```python
# Получение Hardware ID
hardware_id = await manager.get_hardware_id()
print(f"Hardware ID: {hardware_id}")

# Hardware ID генерируется автоматически при первом запросе
# и кэшируется для последующего использования
```

## 📊 Мониторинг и Отладка

### Статус менеджера

```python
# Получение статуса менеджера
status = manager.get_status()
print(f"Initialized: {status['is_initialized']}")
print(f"Hardware ID available: {status['hardware_id_provider']['is_available']}")
print(f"Session tracker available: {status['session_tracker']['is_available']}")
```

### Статистика сессий

```python
# Получение статистики сессий
stats = manager.get_session_statistics()
print(f"Active sessions: {stats['active_sessions']}")
print(f"Total sessions: {stats['total_sessions']}")
print(f"Interrupted sessions: {stats['interrupted_sessions']}")
print(f"Global interrupt flag: {stats['global_interrupt_flag']}")
```

### Метрики производительности

```python
# Получение метрик
metrics = manager.get_metrics()
hardware_metrics = metrics['hardware_id_provider']
tracker_metrics = metrics['session_tracker']

print(f"Hardware ID requests: {hardware_metrics['total_requests']}")
print(f"Session requests: {tracker_metrics['total_requests']}")
print(f"Success rate: {tracker_metrics['success_rate']:.2%}")
```

## 🎛️ Конфигурация

### Полная конфигурация

```python
config = {
    # Hardware ID настройки
    'hardware_id_cache_file': 'hardware_id.cache',
    'hardware_id_length': 32,
    'hardware_id_charset': 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789',
    
    # Настройки сессий
    'session_timeout': 3600,
    'session_cleanup_interval': 300,
    'max_concurrent_sessions': 100,
    'session_heartbeat_interval': 30,
    
    # Настройки прерываний
    'interrupt_timeout': 5,
    'interrupt_cleanup_delay': 10,
    'global_interrupt_enabled': True,
    
    # Настройки отслеживания
    'tracking_enabled': True,
    'track_user_agents': True,
    'track_ip_addresses': False,
    'track_timestamps': True,
    
    # Настройки производительности
    'max_session_history': 1000,
    'session_data_retention': 86400,  # 24 часа
    'cleanup_batch_size': 50,
    
    # Настройки безопасности
    'require_hardware_id': True,
    'validate_session_ownership': True,
    'encrypt_session_data': False,
    
    # Настройки логирования
    'log_level': 'INFO',
    'log_sessions': True,
    'log_interrupts': True,
    'log_hardware_ids': False  # Безопасность
}
```

### Валидация конфигурации

```python
from modules.session_management.config import SessionManagementConfig

config = SessionManagementConfig(your_config)
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration validation failed")
```

## 🔒 Безопасность

### Настройки безопасности

```python
# Получение настроек безопасности
security_settings = manager.get_security_settings()
print(f"Require Hardware ID: {security_settings['require_hardware_id']}")
print(f"Validate session ownership: {security_settings['validate_session_ownership']}")
print(f"Encrypt session data: {security_settings['encrypt_session_data']}")
print(f"Track IP addresses: {security_settings['track_ip_addresses']}")
print(f"Log Hardware IDs: {security_settings['log_hardware_ids']}")
```

### Hardware ID безопасность

```python
# Hardware ID генерируется на основе аппаратных характеристик
# и кэшируется локально для персистентности

# Регенерация Hardware ID (при необходимости)
provider = manager.hardware_id_provider
success = provider.regenerate_hardware_id()
if success:
    # Перезапустить менеджер для генерации нового ID
    await manager.cleanup()
    await manager.initialize()
```

## ⚙️ Производительность

### Настройки производительности

```python
# Получение настроек производительности
performance_settings = manager.get_performance_settings()
print(f"Max concurrent sessions: {performance_settings['max_concurrent_sessions']}")
print(f"Session timeout: {performance_settings['session_timeout']}")
print(f"Cleanup interval: {performance_settings['session_cleanup_interval']}")
print(f"Heartbeat interval: {performance_settings['session_heartbeat_interval']}")
```

### Оптимизация:

1. **Автоматическая очистка** - удаление устаревших сессий
2. **Heartbeat мониторинг** - отслеживание активности сессий
3. **Batch cleanup** - пакетная очистка для производительности
4. **Session history limit** - ограничение истории сессий

### Мониторинг:

```python
# Получение статистики производительности
stats = manager.get_session_statistics()
print(f"Active sessions: {stats['active_sessions']}")
print(f"Session history: {stats['session_history_count']}")
print(f"Cleanup batch size: {performance_settings['cleanup_batch_size']}")
```

## ⚠️ Обработка Ошибок

### Типы ошибок:
1. **Инициализация**: невалидная конфигурация, проблемы с кэшем
2. **Создание сессий**: превышение лимита, проблемы с Hardware ID
3. **Прерывания**: сессия не найдена, проблемы с очисткой

### Обработка в коде:

```python
try:
    session_data = await manager.create_session()
    print(f"Session created: {session_data['session_id']}")
except Exception as e:
    logger.error(f"Session creation error: {e}")
    # Fallback или уведомление об ошибке
```

### Обработка прерываний:

```python
try:
    # Проверка флага прерывания перед операцией
    if manager.session_tracker.global_interrupt_flag:
        raise Exception("Global interrupt active")
    
    # Выполнение операции
    result = await some_operation()
    
except asyncio.CancelledError:
    logger.info("Operation cancelled")
except Exception as e:
    logger.error(f"Operation error: {e}")
```

## 🧪 Тестирование

### Запуск тестов:

```bash
# Все тесты модуля
python -m pytest modules/session_management/tests/

# Конкретный тест
python -m pytest modules/session_management/tests/test_session_manager.py

# С покрытием
python -m pytest modules/session_management/tests/ --cov=modules.session_management
```

### Тестирование Hardware ID:

```python
# Тест Hardware ID провайдера
from modules.session_management.providers.hardware_id_provider import HardwareIDProvider

config = {
    'cache_file': 'test.cache',
    'length': 16
}

provider = HardwareIDProvider(config)
await provider.initialize()

hardware_id = None
async for result in provider.process(None):
    hardware_id = result
    break

assert hardware_id is not None
assert len(hardware_id) == 16
```

### Тестирование Session Tracker:

```python
# Тест Session Tracker
from modules.session_management.providers.session_tracker import SessionTracker

config = {
    'session_timeout': 60,
    'max_concurrent_sessions': 10
}

tracker = SessionTracker(config)
await tracker.initialize()

# Создание сессии
session_data = {
    'hardware_id': 'test-hardware-id',
    'user_agent': 'Test Agent'
}

session_result = None
async for result in tracker.process(session_data):
    session_result = result
    break

assert session_result is not None
assert session_result['session_id'] is not None
```

## 🔄 Интеграция с существующим gRPC сервером

### Замена существующего кода:

```python
# Старый код в grpc_server.py
self.active_sessions = {}
self.global_interrupt_flag = False

# Новый код
from modules.session_management.core.session_manager import SessionManager

self.session_manager = SessionManager(config)
await self.session_manager.initialize()
```

### Использование в gRPC методах:

```python
async def StreamAudio(self, request, context):
    # Создание сессии
    session_data = await self.session_manager.create_session(
        user_agent=context.user_agent,
        ip_address=context.peer(),
        context={'request_type': 'audio_stream'}
    )
    
    session_id = session_data['session_id']
    hardware_id = session_data['hardware_id']
    
    try:
        # Выполнение операции
        async for audio_chunk in self.process_audio(request.text):
            # Проверка прерывания
            if session_data['interrupt_flag']:
                break
            yield audio_chunk
            
    finally:
        # Очистка сессии при завершении
        await self.session_manager.interrupt_session(session_id, "completed")
```

### Глобальные прерывания:

```python
# Прерывание всех сессий при shutdown
async def shutdown(self):
    count = await self.session_manager.interrupt_all_sessions("server_shutdown")
    logger.info(f"Interrupted {count} sessions during shutdown")
    await self.session_manager.cleanup()
```

## 🚨 Устранение Неполадок

### Частые проблемы:

1. **"SessionManager not initialized"**
   - Проверьте вызов `await manager.initialize()`
   - Проверьте валидность конфигурации

2. **"Maximum concurrent sessions reached"**
   - Увеличьте `max_concurrent_sessions`
   - Проверьте работу автоматической очистки

3. **"Hardware ID generation failed"**
   - Проверьте права доступа к кэш-файлу
   - Проверьте аппаратную информацию системы

4. **"Session not found"**
   - Проверьте корректность session_id
   - Проверьте, не истекла ли сессия

### Логирование:

```python
import logging

# Включение подробного логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('modules.session_management')
```

### Диагностика:

```python
# Проверка статуса всех компонентов
status = manager.get_status()
print(f"Hardware ID status: {status['hardware_id_provider']['status']}")
print(f"Session tracker status: {status['session_tracker']['status']}")

# Проверка статистики
stats = manager.get_session_statistics()
print(f"Active sessions: {stats['active_sessions']}")
print(f"Global interrupt: {stats['global_interrupt_flag']}")

# Проверка здоровья провайдеров
hardware_health = await manager.hardware_id_provider.health_check()
tracker_health = await manager.session_tracker.health_check()
print(f"Hardware ID healthy: {hardware_health}")
print(f"Session tracker healthy: {tracker_health}")
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

### Миграция сессий:
```python
# При изменении структуры сессий
old_sessions = manager.session_tracker.active_sessions
for session_id, session in old_sessions.items():
    # Миграция данных сессии
    new_session = migrate_session_data(session)
    # Обновление сессии
```

## 📞 Поддержка

### Полезные команды:

```python
# Получение сводки
summary = manager.get_summary()
print(summary)

# Сброс метрик
manager.reset_metrics()

# Получение настроек
security = manager.get_security_settings()
performance = manager.get_performance_settings()
tracking = manager.get_tracking_settings()
```

### Контакты:
- Документация: `modules/session_management/docs/`
- Тесты: `modules/session_management/tests/`
- Логи: проверьте логи приложения

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: Python 3.11+, AsyncIO
