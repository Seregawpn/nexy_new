# Руководство по интеграции модуля interrupt_management

## 📋 Обзор

Модуль `interrupt_management` предоставляет централизованную систему управления прерываниями для приложения Nexy. Данное руководство описывает требования, процесс интеграции и возможные проблемы.

## 🏗️ Архитектура интеграции

### Основные компоненты для интеграции:
- **InterruptCoordinator** - центральный координатор
- **SpeechInterruptHandler** - обработчик прерываний речи
- **RecordingInterruptHandler** - обработчик прерываний записи
- **InterruptModuleConfig** - конфигурация модуля

### Зависимости модуля:
- `speech_playback` - для управления воспроизведением речи
- `speech_recognizer` - для управления записью речи
- `grpc_client` - для отправки прерываний на сервер
- `state_manager` - для управления состоянием приложения

## 🔧 Требования к интеграции

### 1. Системные требования
```python
# Минимальные версии Python
Python >= 3.8
asyncio >= 3.4.3
logging >= 0.4.9.6
```

### 2. Зависимости модулей
```python
# Обязательные модули для интеграции
speech_playback: {
    "methods": ["stop_playback()", "pause_playback()", "resume_playback()"],
    "return_types": ["bool"]
}

speech_recognizer: {
    "methods": ["start_recording()", "stop_recording()"],
    "return_types": ["bool", "str"]
}

grpc_client: {
    "methods": ["interrupt_session()"],
    "return_types": ["None"]
}

state_manager: {
    "methods": ["clear_session()", "reset_state()"],
    "return_types": ["bool"]
}
```

### 3. Конфигурационные требования
```yaml
# app_config.yaml
interrupt_management:
  coordinator:
    max_concurrent_interrupts: 5
    interrupt_timeout: 10.0
    retry_attempts: 3
    retry_delay: 1.0
    enable_logging: true
    enable_metrics: true
  enable_speech_interrupts: true
  enable_recording_interrupts: true
  enable_session_interrupts: true
  enable_full_reset: true
  speech_interrupt_timeout: 5.0
  recording_interrupt_timeout: 3.0
  session_interrupt_timeout: 10.0
  full_reset_timeout: 15.0
```

## 🚀 Пошаговая интеграция

### Шаг 1: Импорт модуля
```python
from interrupt_management import (
    InterruptCoordinator, InterruptDependencies,
    InterruptEvent, InterruptType, InterruptPriority,
    SpeechInterruptHandler, RecordingInterruptHandler,
    InterruptModuleConfig, DEFAULT_INTERRUPT_CONFIG
)
```

### Шаг 2: Инициализация координатора
```python
# Создание координатора с конфигурацией
config = InterruptModuleConfig.from_dict(app_config['interrupt_management'])
coordinator = InterruptCoordinator(config.coordinator)

# Настройка зависимостей
dependencies = InterruptDependencies(
    speech_player=speech_player_instance,
    speech_recognizer=speech_recognizer_instance,
    grpc_client=grpc_client_instance,
    state_manager=state_manager_instance
)

coordinator.initialize(dependencies)
```

### Шаг 3: Регистрация обработчиков
```python
# Создание обработчиков
speech_handler = SpeechInterruptHandler(speech_player, grpc_client)
recording_handler = RecordingInterruptHandler(speech_recognizer)

# Регистрация обработчиков
coordinator.register_handler(InterruptType.SPEECH_STOP, speech_handler.handle_speech_stop)
coordinator.register_handler(InterruptType.SPEECH_PAUSE, speech_handler.handle_speech_pause)
coordinator.register_handler(InterruptType.RECORDING_STOP, recording_handler.handle_recording_stop)
```

### Шаг 4: Использование в приложении
```python
# Создание события прерывания
event = InterruptEvent(
    type=InterruptType.SPEECH_STOP,
    priority=InterruptPriority.HIGH,
    source="user_input",
    timestamp=time.time()
)

# Запуск прерывания
result = await coordinator.trigger_interrupt(event)
```

## 🔗 Интеграция с существующими модулями

### 1. Интеграция с speech_playback
```python
# В speech_playback модуле
class SpeechPlayer:
    def __init__(self, interrupt_coordinator=None):
        self.interrupt_coordinator = interrupt_coordinator
    
    def stop_playback(self) -> bool:
        """Останавливает воспроизведение"""
        try:
            # Логика остановки
            self.is_playing = False
            return True
        except Exception as e:
            logger.error(f"Ошибка остановки воспроизведения: {e}")
            return False
```

### 2. Интеграция с speech_recognizer
```python
# В speech_recognizer модуле
class SpeechRecognizer:
    def __init__(self, interrupt_coordinator=None):
        self.interrupt_coordinator = interrupt_coordinator
    
    async def stop_recording(self) -> Optional[str]:
        """Останавливает запись и возвращает распознанный текст"""
        try:
            # Логика остановки записи
            text = self.process_audio()
            self.is_recording = False
            return text
        except Exception as e:
            logger.error(f"Ошибка остановки записи: {e}")
            return None
```

### 3. Интеграция с grpc_client
```python
# В grpc_client модуле
class GrpcClient:
    def __init__(self, interrupt_coordinator=None):
        self.interrupt_coordinator = interrupt_coordinator
    
    async def interrupt_session(self):
        """Отправляет прерывание на сервер"""
        try:
            # Отправка прерывания через gRPC
            await self.stub.InterruptSession(InterruptRequest())
        except Exception as e:
            logger.error(f"Ошибка отправки прерывания: {e}")
            raise
```

## ⚠️ Возможные ошибки и их решения

### 1. Ошибки инициализации
```python
# Проблема: ModuleNotFoundError
# Решение: Проверить импорты и PYTHONPATH
import sys
sys.path.append('/path/to/interrupt_management')

# Проблема: AttributeError при инициализации
# Решение: Проверить версии зависимостей
pip install --upgrade asyncio logging
```

### 2. Ошибки конфигурации
```python
# Проблема: KeyError в конфигурации
# Решение: Использовать значения по умолчанию
config = InterruptModuleConfig.from_dict(
    app_config.get('interrupt_management', {})
)

# Проблема: ValidationError
# Решение: Проверить типы данных в конфигурации
assert isinstance(config.coordinator.max_concurrent_interrupts, int)
```

### 3. Ошибки выполнения
```python
# Проблема: RuntimeError при параллельных прерываниях
# Решение: Проверить thread-safety
async with coordinator._lock:
    # Критическая секция

# Проблема: TimeoutError
# Решение: Увеличить таймауты в конфигурации
config.coordinator.interrupt_timeout = 15.0
```

### 4. Ошибки интеграции
```python
# Проблема: AttributeError в обработчиках
# Решение: Проверить интерфейсы модулей
assert hasattr(speech_player, 'stop_playback')
assert callable(speech_player.stop_playback)

# Проблема: TypeError при вызове методов
# Решение: Проверить сигнатуры методов
if asyncio.iscoroutinefunction(handler):
    result = await handler(event)
else:
    result = handler(event)
```

## 🧪 Тестирование интеграции

### 1. Unit тесты
```python
# Тест инициализации
def test_coordinator_initialization():
    coordinator = InterruptCoordinator()
    assert coordinator is not None
    assert len(coordinator.active_interrupts) == 0

# Тест регистрации обработчиков
def test_handler_registration():
    coordinator = InterruptCoordinator()
    coordinator.register_handler(InterruptType.SPEECH_STOP, mock_handler)
    assert InterruptType.SPEECH_STOP in coordinator.interrupt_handlers
```

### 2. Integration тесты
```python
# Тест полной интеграции
async def test_full_integration():
    # Настройка всех компонентов
    coordinator = setup_interrupt_coordinator()
    
    # Тест прерывания
    event = create_test_event()
    result = await coordinator.trigger_interrupt(event)
    
    assert result == True
    assert event.status == InterruptStatus.COMPLETED
```

### 3. Performance тесты
```python
# Тест производительности
async def test_performance():
    start_time = time.time()
    
    # Запуск множественных прерываний
    tasks = [coordinator.trigger_interrupt(create_event()) for _ in range(100)]
    results = await asyncio.gather(*tasks)
    
    execution_time = time.time() - start_time
    assert execution_time < 5.0  # Должно выполняться менее 5 секунд
    assert all(results)  # Все прерывания должны быть успешными
```

## 📊 Мониторинг и отладка

### 1. Логирование
```python
# Настройка логирования
import logging
logging.basicConfig(level=logging.INFO)

# Логирование в модуле
logger = logging.getLogger('interrupt_management')
logger.info(f"Прерывание {event.type.value} запущено")
```

### 2. Метрики
```python
# Получение метрик
metrics = coordinator.get_metrics()
print(f"Всего прерываний: {metrics.total_interrupts}")
print(f"Успешных: {metrics.successful_interrupts}")
print(f"Проваленных: {metrics.failed_interrupts}")
print(f"Среднее время: {metrics.average_processing_time:.2f}s")
```

### 3. Статус системы
```python
# Проверка статуса
status = coordinator.get_status()
print(f"Активных прерываний: {status['active_interrupts']}")
print(f"Успешность: {status['success_rate']:.1f}%")
```

## 🔒 Безопасность

### 1. Валидация входных данных
```python
# Проверка событий прерываний
def validate_interrupt_event(event: InterruptEvent) -> bool:
    if not isinstance(event.type, InterruptType):
        raise ValueError("Неверный тип прерывания")
    if not isinstance(event.priority, InterruptPriority):
        raise ValueError("Неверный приоритет")
    return True
```

### 2. Ограничения ресурсов
```python
# Настройка лимитов
config = InterruptConfig(
    max_concurrent_interrupts=5,  # Максимум 5 одновременных прерываний
    interrupt_timeout=10.0,       # Таймаут 10 секунд
    retry_attempts=3              # Максимум 3 попытки
)
```

## 📝 Чек-лист интеграции

- [ ] Импортированы все необходимые модули
- [ ] Создан экземпляр InterruptCoordinator
- [ ] Настроены зависимости (speech_player, speech_recognizer, grpc_client)
- [ ] Зарегистрированы обработчики для всех типов прерываний
- [ ] Добавлена конфигурация в app_config.yaml
- [ ] Настроено логирование
- [ ] Написаны unit тесты
- [ ] Написаны integration тесты
- [ ] Проведено тестирование производительности
- [ ] Настроен мониторинг и метрики

## 🆘 Поддержка

При возникновении проблем:
1. Проверьте логи приложения
2. Убедитесь в корректности конфигурации
3. Проверьте версии зависимостей
4. Запустите тесты для диагностики
5. Обратитесь к документации модулей-зависимостей

---
*Документ создан: 2025-09-13*  
*Версия модуля: 1.0.0*  
*Автор: AI Assistant*
