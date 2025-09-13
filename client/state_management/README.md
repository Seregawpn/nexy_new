# State Management Module

Модуль управления состояниями приложения для Nexy AI Voice Assistant.

## Описание

Этот модуль предоставляет централизованное управление состояниями приложения, включая:

- **Управление состояниями** - SLEEPING, LISTENING, PROCESSING, ERROR, SHUTDOWN
- **Валидация переходов** - проверка корректности переходов между состояниями
- **Мониторинг** - отслеживание метрик и истории состояний
- **Восстановление** - автоматическое восстановление после ошибок
- **Конфигурация** - гибкая настройка поведения модуля

## Архитектура

```
state_management/
├── core/                    # Основные компоненты
│   ├── state_manager.py     # Главный менеджер состояний
│   ├── state_validator.py   # Валидатор состояний
│   └── types.py             # Типы данных
├── monitoring/              # Мониторинг и метрики
│   └── state_monitor.py     # Монитор состояний
├── recovery/                # Система восстановления
│   └── state_recovery.py    # Восстановление после ошибок
├── config/                  # Конфигурация
│   └── state_config.py      # Настройки модуля
├── utils/                   # Утилиты
│   └── state_utils.py       # Вспомогательные функции
├── tests/                   # Тесты
│   └── test_state_manager.py # Тесты модуля
├── macos/                   # macOS требования
│   ├── entitlements/        # Права доступа
│   ├── info/               # Info.plist
│   ├── scripts/            # Скрипты сборки
│   ├── packaging/          # Требования для упаковки
│   ├── notarization/       # Конфигурация нотаризации
│   └── certificates/       # Настройка сертификатов
└── __init__.py             # Главный модуль
```

## Установка

### Требования

- Python 3.8+
- macOS 10.15+ (для macOS сборки)

### Установка зависимостей

```bash
pip install -r macos/packaging/requirements.txt
```

## Использование

### Базовое использование

```python
from state_management import StateManager, AppState

# Создание менеджера состояний
state_manager = StateManager()

# Проверка текущего состояния
print(f"Текущее состояние: {state_manager.get_state_name()}")

# Переходы между состояниями
await state_manager.start_listening()    # SLEEPING → LISTENING
await state_manager.start_processing()   # LISTENING → PROCESSING
await state_manager.stop_processing()    # PROCESSING → SLEEPING
```

### Конфигурация

```python
from state_management import create_config, StateManager

# Создание конфигурации
config = create_config("high_performance", max_history_size=50)

# Создание менеджера с конфигурацией
state_manager = StateManager(config)
```

### Callback'и

```python
def on_state_changed(from_state, to_state, reason):
    print(f"Состояние изменилось: {from_state.value} → {to_state.value} ({reason})")

def on_error(error, context):
    print(f"Ошибка в {context}: {error}")

def on_recovery(state):
    print(f"Восстановление в состояние: {state.value}")

# Установка callback'ов
state_manager.set_state_changed_callback(on_state_changed)
state_manager.set_error_callback(on_error)
state_manager.set_recovery_callback(on_recovery)
```

### Мониторинг

```python
# Получение метрик
metrics = state_manager.get_metrics()
print(f"Всего переходов: {metrics.total_transitions}")
print(f"Успешных: {metrics.successful_transitions}")

# Получение истории состояний
history = state_manager.get_state_history(limit=10)
for state_info in history:
    print(f"{state_info.timestamp}: {state_info.state.value}")
```

## Состояния приложения

| Состояние | Описание | Переходы |
|-----------|----------|----------|
| **SLEEPING** | Сон - ничего не делает | → LISTENING, ERROR, SHUTDOWN |
| **LISTENING** | Прослушивание команд | → PROCESSING, SLEEPING, ERROR, SHUTDOWN |
| **PROCESSING** | Обработка команды | → SLEEPING, ERROR, SHUTDOWN |
| **ERROR** | Ошибка | → SLEEPING, SHUTDOWN |
| **SHUTDOWN** | Завершение работы | - |

## Конфигурации

### DefaultStateConfig
- Максимальная история: 100 записей
- Таймаут перехода: 30 секунд
- Попытки восстановления: 3
- Задержка восстановления: 1 секунда

### HighPerformanceConfig
- Максимальная история: 50 записей
- Таймаут перехода: 15 секунд
- Попытки восстановления: 2
- Задержка восстановления: 0.5 секунды

### DebugConfig
- Максимальная история: 500 записей
- Таймаут перехода: 60 секунд
- Попытки восстановления: 5
- Задержка восстановления: 2 секунды

## Тестирование

```bash
# Запуск всех тестов
python -m pytest tests/ -v

# Запуск конкретного теста
python -m pytest tests/test_state_manager.py::TestStateManager -v

# Запуск с покрытием
python -m pytest tests/ --cov=state_management --cov-report=html
```

## macOS Сборка

### Сборка модуля

```bash
# Сборка для macOS
chmod +x macos/scripts/build_macos.sh
./macos/scripts/build_macos.sh
```

### Подписание и нотаризация

```bash
# Подписание и нотаризация
chmod +x macos/scripts/sign_and_notarize.sh
./macos/scripts/sign_and_notarize.sh
```

### Требования для сборки

1. **Xcode Command Line Tools**
2. **Apple Developer Account** (для подписания)
3. **Сертификаты** (см. `macos/certificates/certificate_setup.md`)

## API Reference

### StateManager

#### Методы управления состояниями

- `start_listening()` - Начать прослушивание
- `stop_listening()` - Остановить прослушивание
- `start_processing()` - Начать обработку
- `stop_processing()` - Остановить обработку
- `sleep()` - Перейти в режим сна
- `error(error, context)` - Перейти в состояние ошибки
- `shutdown()` - Завершить работу

#### Методы проверки состояний

- `is_listening()` - Проверка прослушивания
- `is_processing()` - Проверка обработки
- `is_sleeping()` - Проверка сна
- `is_error()` - Проверка ошибки
- `is_shutdown()` - Проверка завершения

#### Методы мониторинга

- `get_metrics()` - Получить метрики
- `get_state_history(limit)` - Получить историю состояний

### StateValidator

- `can_transition(from_state, to_state)` - Проверка возможности перехода
- `validate_state(state)` - Валидация состояния
- `get_transition_type(from_state, to_state)` - Получение типа перехода

### StateMonitor

- `record_transition(from_state, to_state, duration, success, reason)` - Запись перехода
- `record_error(error, context)` - Запись ошибки
- `record_recovery()` - Запись восстановления
- `get_metrics()` - Получение метрик
- `get_state_history(limit)` - Получение истории

### StateRecovery

- `attempt_recovery(current_state, error)` - Попытка восстановления
- `recover_with_retry(current_state, error)` - Восстановление с повторными попытками

## Примеры использования

### Простой пример

```python
import asyncio
from state_management import StateManager

async def main():
    # Создание менеджера состояний
    state_manager = StateManager()
    
    # Начинаем прослушивание
    await state_manager.start_listening()
    print(f"Состояние: {state_manager.get_state_name()}")
    
    # Переходим к обработке
    await state_manager.start_processing()
    print(f"Состояние: {state_manager.get_state_name()}")
    
    # Завершаем обработку
    await state_manager.stop_processing()
    print(f"Состояние: {state_manager.get_state_name()}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Пример с callback'ами

```python
import asyncio
from state_management import StateManager, AppState

async def main():
    state_manager = StateManager()
    
    # Настройка callback'ов
    def on_state_changed(from_state, to_state, reason):
        print(f"🔄 {from_state.value} → {to_state.value} ({reason})")
    
    def on_error(error, context):
        print(f"❌ Ошибка в {context}: {error}")
    
    state_manager.set_state_changed_callback(on_state_changed)
    state_manager.set_error_callback(on_error)
    
    # Работа с состояниями
    await state_manager.start_listening()
    await state_manager.start_processing()
    await state_manager.stop_processing()

if __name__ == "__main__":
    asyncio.run(main())
```

## Лицензия

Proprietary - Copyright © 2024 Nexy AI. All rights reserved.

## Поддержка

- Документация: [https://docs.nexy.ai](https://docs.nexy.ai)
- Поддержка: [https://support.nexy.ai](https://support.nexy.ai)
- Веб-сайт: [https://nexy.ai](https://nexy.ai)
