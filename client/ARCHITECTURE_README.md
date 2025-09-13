# Новая архитектура модулей Nexy

## 🏗️ Обзор архитектуры

Новая архитектура разделяет ответственности между модулями и обеспечивает четкую интеграцию с существующими компонентами.

## 📁 Структура модулей

```
client/
├── input_processing/           # Обработка ввода (рефакторинг существующих)
│   ├── keyboard/              # Клавиатура (из improved_input_handler.py)
│   ├── speech/                # Речь (из stt_recognizer.py)
│   └── config/                # Конфигурация ввода
│
├── interrupt_management/       # Управление прерываниями (НОВЫЙ)
│   ├── core/                  # Основная логика
│   ├── handlers/              # Обработчики прерываний
│   └── config/                # Конфигурация прерываний
│
├── mode_management/           # Управление режимами (НОВЫЙ)
│   ├── core/                  # Основная логика
│   ├── modes/                 # Режимы приложения
│   └── config/                # Конфигурация режимов
│
├── integration/               # Интеграция модулей (НОВЫЙ)
│   ├── core/                  # Координатор модулей
│   └── handlers/              # Обработчики событий
│
├── speech_playback/           # ✅ УЖЕ РЕАЛИЗОВАН - НЕ ТРОГАЕМ
├── audio_device_manager/      # ✅ УЖЕ РЕАЛИЗОВАН - НЕ ТРОГАЕМ
└── legacy/                    # Старые модули (для совместимости)
    ├── improved_input_handler.py
    └── stt_recognizer.py
```

## 🔄 Поток событий

```
1. KeyboardMonitor → KeyEvent (SHORT_PRESS/LONG_PRESS/RELEASE)
2. ModuleCoordinator получает KeyEvent
3. Определяет тип нажатия и текущий режим
4. Выполняет соответствующее действие:
   - SHORT_PRESS + SPEAKING → speech_player.stop_playback()
   - LONG_PRESS + SPEAKING → speech_player.stop_playback() + switch_to_recording()
   - LONG_PRESS + IDLE → switch_to_recording()
   - RELEASE + RECORDING → speech_recognizer.stop_recording() + switch_to_processing()
5. ModeController переключает режим
6. InterruptCoordinator выполняет прерывания через существующие модули
7. EventBus уведомляет все модули об изменениях
```

## 🎯 Основные принципы

### 1. Разделение ответственностей
- **input_processing/** - обработка ввода (клавиатура + речь)
- **interrupt_management/** - управление прерываниями
- **mode_management/** - управление режимами приложения
- **integration/** - координация всех модулей

### 2. Интеграция с существующими модулями
- **speech_playback/** - используется напрямую
- **audio_device_manager/** - используется напрямую
- **improved_input_handler.py** - рефакторинг в input_processing/keyboard/
- **stt_recognizer.py** - рефакторинг в input_processing/speech/

### 3. Thread-safe операции
- Все модули используют asyncio для асинхронных операций
- Блокировки для thread-safety
- Callback система для уведомлений

### 4. Конфигурируемость
- Каждый модуль имеет свою конфигурацию
- Возможность настройки через конфигурационные файлы
- Значения по умолчанию для всех параметров

## 🚀 Использование

### Базовое использование

```python
from integration import ModuleCoordinator, ModuleDependencies
from speech_playback import SequentialSpeechPlayer, PlayerConfig
from audio_device_manager import DeviceManager

# Создаем зависимости
dependencies = ModuleDependencies(
    speech_player=speech_player,
    audio_device_manager=audio_device_manager,
    grpc_client=grpc_client,
    state_manager=state_manager,
    screen_capture=screen_capture
)

# Создаем координатор
coordinator = ModuleCoordinator()

# Инициализируем
coordinator.initialize(dependencies)

# Запускаем
await coordinator.start()

# Останавливаем
await coordinator.stop()
```

### Обработка событий

```python
# Короткое нажатие пробела - прерывание речи
# Долгое нажатие пробела - прерывание речи + запись
# Отпускание пробела - остановка записи + обработка
```

## 🧪 Тестирование

Запустите тестовый скрипт:

```bash
python test_integration.py
```

Тест проверяет:
- Мониторинг клавиатуры
- Распознавание речи
- Интеграцию модулей

## 📊 Мониторинг

Каждый модуль предоставляет статус:

```python
# Статус координатора
status = coordinator.get_status()

# Статус мониторинга клавиатуры
keyboard_status = coordinator.keyboard_monitor.get_status()

# Статус распознавания речи
speech_status = coordinator.speech_recognizer.get_status()

# Статус прерываний
interrupt_status = coordinator.interrupt_coordinator.get_status()

# Статус режимов
mode_status = coordinator.mode_controller.get_status()
```

## 🔧 Конфигурация

### Конфигурация клавиатуры

```python
from input_processing import KeyboardConfig

config = KeyboardConfig(
    key_to_monitor="space",
    short_press_threshold=0.6,
    long_press_threshold=2.0,
    event_cooldown=0.1,
    hold_check_interval=0.05,
    debounce_time=0.1
)
```

### Конфигурация речи

```python
from input_processing import SpeechConfig

config = SpeechConfig(
    sample_rate=16000,
    chunk_size=1024,
    channels=1,
    energy_threshold=100,
    dynamic_energy_threshold=True,
    pause_threshold=0.5,
    phrase_threshold=0.3,
    non_speaking_duration=0.3,
    max_duration=30.0,
    auto_start=True
)
```

### Конфигурация прерываний

```python
from interrupt_management import InterruptConfig

config = InterruptConfig(
    max_concurrent_interrupts=5,
    interrupt_timeout=10.0,
    retry_attempts=3,
    retry_delay=1.0,
    enable_logging=True,
    enable_metrics=True
)
```

## 🐛 Отладка

### Логирование

Все модули используют стандартное логирование Python:

```python
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Метрики

Каждый модуль предоставляет метрики:

```python
# Метрики прерываний
metrics = coordinator.interrupt_coordinator.get_metrics()

# Метрики режимов
metrics = coordinator.mode_controller.get_metrics()
```

## 🔄 Миграция

### Из старой архитектуры

1. **improved_input_handler.py** → **input_processing/keyboard/**
2. **stt_recognizer.py** → **input_processing/speech/**
3. **speech_playback/** - используется напрямую
4. **audio_device_manager/** - используется напрямую

### Обратная совместимость

Старые модули перемещены в папку `legacy/` для обратной совместимости.

## 📈 Производительность

### Оптимизации

- Асинхронные операции для неблокирующей работы
- Thread-safe операции с минимальными блокировками
- Эффективная система callbacks
- Метрики для мониторинга производительности

### Мониторинг

- Время обработки событий
- Количество прерываний
- Успешность переходов между режимами
- Статус всех модулей

## 🚀 Развитие

### Планы развития

1. **Дополнительные клавиши** - поддержка других клавиш кроме пробела
2. **Голосовые команды** - интеграция с голосовыми командами
3. **Гестures** - поддержка жестов мыши
4. **Плагины** - система плагинов для расширения функциональности

### API для разработчиков

Каждый модуль предоставляет четкий API для интеграции:

```python
# API клавиатуры
monitor = KeyboardMonitor(config)
monitor.register_callback(KeyEventType.SHORT_PRESS, callback)
monitor.start_monitoring()

# API речи
recognizer = SpeechRecognizer(config)
recognizer.register_callback(SpeechState.RECORDING, callback)
await recognizer.start_recording()

# API прерываний
coordinator = InterruptCoordinator()
coordinator.register_handler(InterruptType.SPEECH_STOP, handler)
await coordinator.trigger_interrupt(event)

# API режимов
controller = ModeController()
controller.register_transition(transition)
await controller.switch_mode(AppMode.RECORDING)
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи модулей
2. Убедитесь в правильности конфигурации
3. Проверьте статус всех модулей
4. Обратитесь к документации модулей

## 📄 Лицензия

Copyright © 2024 Nexy. All rights reserved.
