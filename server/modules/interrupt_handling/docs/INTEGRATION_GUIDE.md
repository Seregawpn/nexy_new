# Interrupt Handling Module - Инструкция по Интеграции

## 🎯 Обзор

Interrupt Handling Module - это универсальный модуль для обработки прерываний и отмены операций в реальном времени. Обеспечивает мгновенную отмену всех процессов генерации и управление глобальными флагами прерывания.

## 🏗️ Архитектура

### Универсальный Стандарт Взаимодействия

```
Interrupt Request → InterruptManager → GlobalFlagProvider + SessionTrackerProvider → All Modules → Cleanup
```

### Компоненты

1. **InterruptManager** - основной координатор прерываний
2. **GlobalFlagProvider** - управление глобальными флагами
3. **SessionTrackerProvider** - отслеживание активных сессий
4. **Universal Module Interface** - стандартный интерфейс модуля

## 📋 Функциональность

### Основные операции

- **interrupt_session** - прерывание сессии для hardware_id
- **register_module** - регистрация модуля для прерывания
- **register_callback** - регистрация callback функций
- **check_interrupt** - проверка необходимости прерывания

### Управление сессиями

- **register_session** - регистрация активной сессии
- **unregister_session** - отмена регистрации сессии
- **cleanup_sessions** - очистка сессий для hardware_id

### Глобальные флаги

- **set_interrupt_flag** - установка глобального флага прерывания
- **reset_flags** - сброс глобальных флагов
- **check_flag** - проверка статуса флага

## 🔧 Использование

### Инициализация

```python
from modules.interrupt_handling import InterruptManager
from modules.interrupt_handling.config import InterruptHandlingConfig

# Создание конфигурации
config = InterruptHandlingConfig()

# Создание менеджера
interrupt_manager = InterruptManager(config)

# Инициализация
await interrupt_manager.initialize()
```

### Прерывание сессии

```python
# Прерывание сессии
hardware_id = "unique_hardware_id_123"
result = await interrupt_manager.interrupt_session(hardware_id)

if result["success"]:
    print(f"Interrupted {len(result['interrupted_modules'])} modules")
    print(f"Cleaned {len(result['cleaned_sessions'])} sessions")
    print(f"Total time: {result['total_time_ms']:.1f}ms")
else:
    print(f"Error: {result['error']}")
```

### Регистрация модулей

```python
# Регистрация модуля для прерывания
await interrupt_manager.register_module("text_processing", text_processor)
await interrupt_manager.register_module("audio_generation", audio_generator)

# Регистрация callback функции
async def my_interrupt_callback(hardware_id: str):
    print(f"Custom interrupt callback for {hardware_id}")

await interrupt_manager.register_callback(my_interrupt_callback)
```

### Проверка прерывания

```python
# Проверка необходимости прерывания
hardware_id = "unique_hardware_id_123"
should_interrupt = interrupt_manager.should_interrupt(hardware_id)

if should_interrupt:
    print("Operation should be interrupted")
    # Прерываем текущую операцию
else:
    print("Operation can continue")
```

### Управление сессиями

```python
# Регистрация сессии
session_id = "session_456"
session_data = {"prompt": "Hello", "user_id": "user_123"}
interrupt_manager.register_session(session_id, hardware_id, session_data)

# Отмена регистрации сессии
interrupt_manager.unregister_session(session_id)
```

## ⚙️ Конфигурация

### Переменные окружения

```bash
# Настройки глобальных флагов
GLOBAL_INTERRUPT_ENABLED=true
INTERRUPT_CHECK_INTERVAL=0.1
INTERRUPT_TIMEOUT=5.0

# Настройки сессий
SESSION_CLEANUP_DELAY=2.0
MAX_ACTIVE_SESSIONS=100
SESSION_TIMEOUT=300

# Настройки логирования
LOG_INTERRUPTS=true
LOG_TIMING=true

# Настройки производительности
INTERRUPT_PRIORITY=high
CLEANUP_ON_INTERRUPT=true
FORCE_CLEANUP=true
```

### Конфигурация модулей

```python
# В config.py можно настроить прерывание для каждого модуля
modules = {
    "text_processing": {
        "enabled": True,
        "interrupt_methods": ["cancel_generation", "clear_buffers"],
        "timeout": 2.0
    },
    "audio_generation": {
        "enabled": True,
        "interrupt_methods": ["stop_generation"],
        "timeout": 1.0
    },
    "session_management": {
        "enabled": True,
        "interrupt_methods": ["interrupt_session"],
        "timeout": 1.0
    }
}
```

## 🧪 Тестирование

### Unit тесты

```python
# Тестирование InterruptManager
pytest modules/interrupt_handling/tests/test_interrupt_manager.py

# Тестирование провайдеров
pytest modules/interrupt_handling/tests/test_global_flag_provider.py
pytest modules/interrupt_handling/tests/test_session_tracker_provider.py
```

### Integration тесты

```python
# Тестирование полного цикла прерывания
pytest modules/interrupt_handling/tests/test_integration.py
```

### Universal тесты

```python
# Тестирование соответствия универсальным стандартам
pytest modules/interrupt_handling/universal_tests/test_universal_compliance.py
```

## 📊 Мониторинг

### Статистика прерываний

```python
# Получение статистики
stats = interrupt_manager.get_statistics()
print(f"Total interrupts: {stats['total_interrupts']}")
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Active sessions: {stats['active_sessions']}")
print(f"Registered modules: {stats['registered_modules']}")
```

### Статус провайдеров

```python
# Статус глобальных флагов
flag_status = await global_flag_provider.get_flag_status()
print(f"Global flag: {flag_status['global_interrupt_flag']}")
print(f"Interrupt hardware ID: {flag_status['interrupt_hardware_id']}")

# Статус трекера сессий
tracker_status = await session_tracker_provider.get_tracker_status()
print(f"Active sessions: {tracker_status['active_sessions']}")
print(f"Total created: {tracker_status['total_created']}")
```

## 🔒 Безопасность

### Мгновенное прерывание

- Глобальный флаг прерывания для мгновенной отмены
- Проверка прерывания в каждой итерации
- Автоматическая очистка ресурсов при прерывании

### Таймауты

- Максимальное время прерывания: 5 секунд
- Таймауты для каждого модуля
- Автоматический сброс флагов при превышении лимитов

### Защита от зависания

- Автоматическая очистка сессий по таймауту
- Ограничение максимального количества активных сессий
- Принудительная очистка ресурсов

## 🚀 Развертывание

### Запуск модуля

```python
# В main.py или gRPC сервере
from modules.interrupt_handling import InterruptManager

async def main():
    interrupt_manager = InterruptManager()
    await interrupt_manager.initialize()
    
    # Регистрация в gRPC сервере
    # (код интеграции)
```

### Интеграция с gRPC сервером

```python
# В StreamingServicer
class StreamingServicer:
    def __init__(self):
        self.interrupt_manager = InterruptManager()
        await self.interrupt_manager.initialize()
        
        # Регистрация модулей
        await self.interrupt_manager.register_module("text_processing", self.text_processor)
        await self.interrupt_manager.register_module("audio_generation", self.audio_generator)
    
    def InterruptSession(self, request, context):
        hardware_id = request.hardware_id
        
        # Используем InterruptManager
        result = await self.interrupt_manager.interrupt_session(hardware_id)
        
        return streaming_pb2.InterruptResponse(
            success=result["success"],
            interrupted_sessions=result["interrupted_modules"],
            message=result.get("message", "Interrupt completed")
        )
```

## 🔄 Обновления

### Добавление нового модуля

1. Убедиться, что модуль имеет методы прерывания
2. Добавить конфигурацию в `config.py`
3. Зарегистрировать модуль в `InterruptManager`
4. Написать тесты для интеграции

### Модификация существующего модуля

1. Обновить методы прерывания, сохранив совместимость
2. Обновить конфигурацию при необходимости
3. Обновить тесты
4. Проверить интеграцию с `InterruptManager`

## 📞 Поддержка

### Отладка

```python
# Включение детального логирования
import logging
logging.getLogger("modules.interrupt_handling").setLevel(logging.DEBUG)

# Проверка статуса
stats = interrupt_manager.get_statistics()
print(json.dumps(stats, indent=2))
```

### Мониторинг производительности

```python
# Метрики прерываний
stats = interrupt_manager.get_statistics()
print(f"Success rate: {stats['success_rate']:.2%}")
print(f"Average interrupt time: {stats.get('avg_time_ms', 0):.1f}ms")
```

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: Interrupt Handling Module v1.0
