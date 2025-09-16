# Руководство по интеграции модуля mode_management

## 📋 Обзор

Данное руководство описывает правильную интеграцию модуля `mode_management` с остальными компонентами системы Nexy. Модуль управляет тремя основными режимами: SLEEPING, PROCESSING, LISTENING.

## 🏗️ Архитектура интеграции

### Основные компоненты
```
mode_management/
├── ModeController          # Центральный контроллер режимов
├── SleepingMode           # Режим сна/ожидания
├── ProcessingMode         # Режим обработки команд
└── ListeningMode          # Режим прослушивания речи
```

### Внешние зависимости
- `speech_recognizer` - для режима прослушивания
- `grpc_client` - для режима обработки
- `state_manager` - для управления состоянием
- `audio_device_manager` - для управления аудио

## 🔗 Интеграция с модулями

### 1. Интеграция с speech_recognizer

#### ✅ Правильная интеграция:
```python
from mode_management import ModeController, AppMode, ListeningMode
from speech_recognition import SpeechRecognizer

# Создание компонентов
speech_recognizer = SpeechRecognizer()
listening_mode = ListeningMode(speech_recognizer, audio_device_manager)
controller = ModeController()

# Регистрация обработчика
async def listening_handler():
    await listening_mode.enter_mode()

controller.register_mode_handler(AppMode.LISTENING, listening_handler)
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - прямая работа с speech_recognizer
speech_recognizer.start_recording()  # Обход mode_management
```

#### ⚠️ Потенциальные проблемы:
- **Проблема**: Конфликт состояний между `mode_management` и `speech_recognizer`
- **Решение**: Всегда используйте `ModeController` для переключения режимов
- **Проблема**: Утечки ресурсов при неправильном завершении режима
- **Решение**: Используйте `exit_mode()` для корректного завершения

### 2. Интеграция с grpc_client

#### ✅ Правильная интеграция:
```python
from mode_management import ProcessingMode
from grpc_client import GrpcClient

# Создание компонентов
grpc_client = GrpcClient()
processing_mode = ProcessingMode(grpc_client, state_manager)

# Обработка команд через режим
response = await processing_mode.process_command("test_command", {"data": "test"})
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - прямая работа с grpc_client
await grpc_client.process_command("command")  # Обход mode_management
```

#### ⚠️ Потенциальные проблемы:
- **Проблема**: Обработка команд без учета текущего режима
- **Решение**: Проверяйте `controller.get_current_mode()` перед обработкой
- **Проблема**: Блокировка UI при длительной обработке
- **Решение**: Используйте асинхронные вызовы и таймауты

### 3. Интеграция с state_manager

#### ✅ Правильная интеграция:
```python
from mode_management import ModeController, AppMode
# state_management удален - используйте основной StateManager из main.py

# Создание компонентов
state_manager = StateManager()
controller = ModeController()

# Синхронизация состояния
async def on_mode_change(event):
    await state_manager.set_current_mode(event.mode.value)

controller.register_mode_change_callback(on_mode_change)
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - ручная синхронизация состояния
state_manager.set_current_mode("listening")  # Может быть несинхронизировано
```

### 4. Интеграция с audio_device_manager

#### ✅ Правильная интеграция:
```python
from mode_management import ListeningMode
from audio_device_manager import AudioDeviceManager

# Создание компонентов
audio_manager = AudioDeviceManager()
listening_mode = ListeningMode(speech_recognizer, audio_manager)

# Автоматическое переключение аудио устройств
await controller.switch_mode(AppMode.LISTENING)
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - ручное управление аудио
audio_manager.switch_to_best_device()  # Может конфликтовать с режимами
```

## 🔄 Жизненный цикл интеграции

### 1. Инициализация
```python
async def initialize_mode_management():
    # Создание контроллера
    config = ModeConfig(default_mode=AppMode.SLEEPING)
    controller = ModeController(config)
    
    # Создание режимов
    sleeping_mode = SleepingMode()
    processing_mode = ProcessingMode(grpc_client, state_manager)
    listening_mode = ListeningMode(speech_recognizer, audio_manager)
    
    # Регистрация обработчиков
    controller.register_mode_handler(AppMode.SLEEPING, sleeping_mode.enter_mode)
    controller.register_mode_handler(AppMode.PROCESSING, processing_mode.enter_mode)
    controller.register_mode_handler(AppMode.LISTENING, listening_mode.enter_mode)
    
    # Регистрация переходов
    register_transitions(controller)
    
    return controller
```

### 2. Регистрация переходов
```python
def register_transitions(controller):
    # SLEEPING -> LISTENING
    transition = ModeTransition(
        from_mode=AppMode.SLEEPING,
        to_mode=AppMode.LISTENING,
        transition_type=ModeTransitionType.AUTOMATIC,
        priority=1,
        timeout=2.0
    )
    controller.register_transition(transition)
    
    # LISTENING -> PROCESSING
    transition = ModeTransition(
        from_mode=AppMode.LISTENING,
        to_mode=AppMode.PROCESSING,
        transition_type=ModeTransitionType.AUTOMATIC,
        priority=1,
        timeout=3.0
    )
    controller.register_transition(transition)
    
    # PROCESSING -> SLEEPING
    transition = ModeTransition(
        from_mode=AppMode.PROCESSING,
        to_mode=AppMode.SLEEPING,
        transition_type=ModeTransitionType.AUTOMATIC,
        priority=1,
        timeout=2.0
    )
    controller.register_transition(transition)
```

### 3. Обработка событий
```python
async def handle_user_input(controller, input_data):
    current_mode = controller.get_current_mode()
    
    if current_mode == AppMode.SLEEPING:
        # Пробуждение для прослушивания
        await controller.switch_mode(AppMode.LISTENING)
    elif current_mode == AppMode.LISTENING:
        # Обработка распознанной речи
        await controller.switch_mode(AppMode.PROCESSING)
    elif current_mode == AppMode.PROCESSING:
        # Завершение обработки
        await controller.switch_mode(AppMode.SLEEPING)
```

## ⚠️ Частые проблемы и решения

### 1. Проблема: Зависание при переключении режимов
**Симптомы**: Приложение не отвечает при смене режима
**Причины**: 
- Блокирующие операции в обработчиках режимов
- Отсутствие таймаутов
- Неправильная обработка исключений

**Решение**:
```python
# Используйте асинхронные операции
async def safe_mode_handler():
    try:
        await asyncio.wait_for(process_data(), timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("Таймаут обработки режима")
    except Exception as e:
        logger.error(f"Ошибка обработки режима: {e}")
```

### 2. Проблема: Конфликт состояний
**Симптомы**: Несоответствие между `mode_management` и другими модулями
**Причины**: 
- Прямая работа с зависимыми модулями
- Отсутствие синхронизации

**Решение**:
```python
# Всегда используйте ModeController для переключения
await controller.switch_mode(AppMode.LISTENING)

# НЕ делайте так:
# speech_recognizer.start_recording()  # Обход контроллера
```

### 3. Проблема: Утечки ресурсов
**Симптомы**: Увеличение потребления памяти, медленная работа
**Причины**: 
- Неправильное завершение режимов
- Отсутствие очистки ресурсов

**Решение**:
```python
# Всегда завершайте режимы правильно
try:
    await mode.enter_mode()
    # Работа с режимом
finally:
    await mode.exit_mode()
```

### 4. Проблема: Некорректные переходы
**Симптомы**: Ошибки при переключении между режимами
**Причины**: 
- Неправильная регистрация переходов
- Отсутствие необходимых переходов

**Решение**:
```python
# Проверяйте доступные переходы
available_transitions = controller.get_available_transitions()
if target_mode in available_transitions:
    await controller.switch_mode(target_mode)
else:
    logger.warning(f"Переход в {target_mode} недоступен")
```

## 🧪 Тестирование интеграции

### 1. Unit тесты
```python
async def test_mode_switching():
    controller = ModeController()
    # Тестирование переключения режимов
    assert await controller.switch_mode(AppMode.LISTENING) == True
    assert controller.get_current_mode() == AppMode.LISTENING
```

### 2. Интеграционные тесты
```python
async def test_full_integration():
    # Тестирование полного цикла с реальными модулями
    controller = await initialize_mode_management()
    
    # Тест полного цикла
    await controller.switch_mode(AppMode.LISTENING)
    await controller.switch_mode(AppMode.PROCESSING)
    await controller.switch_mode(AppMode.SLEEPING)
    
    # Проверка состояния
    assert controller.get_current_mode() == AppMode.SLEEPING
```

### 3. Нагрузочные тесты
```python
async def test_concurrent_switching():
    # Тестирование параллельных переключений
    tasks = []
    for i in range(100):
        task = asyncio.create_task(controller.switch_mode(AppMode.LISTENING))
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Проверка результатов
```

## 📊 Мониторинг и отладка

### 1. Логирование
```python
import logging

# Настройка логирования для mode_management
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mode_management')

# Логирование переходов
async def log_mode_change(event):
    logger.info(f"Переход: {event.mode.value} (тип: {event.transition_type.value})")

controller.register_mode_change_callback(log_mode_change)
```

### 2. Метрики
```python
# Получение метрик
metrics = controller.get_metrics()
print(f"Всего переходов: {metrics.total_transitions}")
print(f"Успешных переходов: {metrics.successful_transitions}")
print(f"Время в режимах: {metrics.time_in_modes}")
```

### 3. Статус системы
```python
# Получение статуса
status = controller.get_status()
print(f"Текущий режим: {status['current_mode']}")
print(f"Доступные переходы: {status['available_transitions']}")
print(f"Успешность: {status['success_rate']}%")
```

## 🔧 Конфигурация

### 1. Настройка таймаутов
```python
config = ModeConfig(
    transition_timeout=5.0,  # Таймаут перехода
    max_transition_attempts=3,  # Максимум попыток
    enable_logging=True,  # Включить логирование
    enable_metrics=True  # Включить метрики
)
```

### 2. Настройка приоритетов
```python
# Высокий приоритет для критических переходов
transition = ModeTransition(
    from_mode=AppMode.PROCESSING,
    to_mode=AppMode.SLEEPING,
    transition_type=ModeTransitionType.INTERRUPT,
    priority=1,  # Высший приоритет
    timeout=1.0
)
```

## 📝 Чек-лист интеграции

### ✅ Перед началом:
- [ ] Изучить архитектуру `mode_management`
- [ ] Определить необходимые зависимости
- [ ] Спланировать переходы между режимами
- [ ] Настроить логирование и мониторинг

### ✅ При интеграции:
- [ ] Использовать `ModeController` для всех переключений
- [ ] Регистрировать все необходимые переходы
- [ ] Обрабатывать исключения в режимах
- [ ] Синхронизировать состояние с `state_manager`

### ✅ После интеграции:
- [ ] Протестировать все переходы режимов
- [ ] Проверить обработку ошибок
- [ ] Настроить мониторинг
- [ ] Документировать изменения

## 🚨 Критические моменты

1. **Никогда не обходите `ModeController`** - все переключения должны идти через него
2. **Всегда обрабатывайте исключения** - режимы могут падать
3. **Синхронизируйте состояние** - `mode_management` должен быть источником истины
4. **Тестируйте граничные случаи** - прерывания, таймауты, ошибки
5. **Мониторьте производительность** - переходы не должны блокировать UI

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи `mode_management`
2. Убедитесь в правильности регистрации переходов
3. Проверьте состояние зависимых модулей
4. Используйте метрики для диагностики
5. Обратитесь к команде разработки

---

**Версия документа**: 1.0  
**Дата обновления**: 2025-09-13  
**Автор**: Nexy Team
