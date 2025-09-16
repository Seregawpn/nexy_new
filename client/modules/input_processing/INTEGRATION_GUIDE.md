# 🔌 Input Processing - Руководство по интеграции

## 📋 Статус готовности

✅ **СИСТЕМА ГОТОВА К ВНЕДРЕНИЮ**
- ✅ Модульная архитектура реализована
- ✅ Обработка клавиатуры протестирована
- ✅ Распознавание речи реализовано
- ✅ Thread-safe операции работают
- ✅ macOS интеграция готова
- ✅ API стабильно и готово

## 🔌 Точки интеграции с проектом

### 1. **Главный файл** (`client/main.py`)

```python
from input_processing import KeyboardMonitor, KeyboardConfig, SpeechRecognizer, SpeechConfig
import asyncio

class MainApplication:
    def __init__(self):
        # Конфигурация клавиатуры
        self.keyboard_config = KeyboardConfig(
            key_to_monitor="space",
            short_press_threshold=0.6,
            long_press_threshold=2.0,
            event_cooldown=0.1,
            hold_check_interval=0.05,
            debounce_time=0.1
        )
        
        # Конфигурация речи
        self.speech_config = SpeechConfig(
            language="ru-RU",
            timeout=5.0,
            phrase_timeout=0.3,
            non_speaking_duration=0.3,
            max_duration=30.0,
            auto_start=True
        )
        
        # Создание мониторов
        self.keyboard_monitor = KeyboardMonitor(self.keyboard_config)
        self.speech_recognizer = SpeechRecognizer(self.speech_config)
        
    async def start(self):
        # Регистрация обработчиков событий
        self.setup_event_handlers()
        
        # Запуск мониторинга
        self.keyboard_monitor.start_monitoring()
        await self.speech_recognizer.start()
        
    def setup_event_handlers(self):
        """Настройка обработчиков событий"""
        from input_processing.keyboard.types import KeyEventType
        from input_processing.speech.types import SpeechEventType
        
        # Обработчики клавиатуры
        self.keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, self.on_short_press)
        self.keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, self.on_long_press)
        
        # Обработчики речи
        self.speech_recognizer.register_callback(SpeechEventType.STARTED, self.on_speech_started)
        self.speech_recognizer.register_callback(SpeechEventType.RECOGNIZED, self.on_speech_recognized)
        self.speech_recognizer.register_callback(SpeechEventType.ERROR, self.on_speech_error)
        
    def on_short_press(self, event):
        """Обработка короткого нажатия пробела"""
        print(f"🔑 Короткое нажатие пробела: {event.duration:.3f}с")
        # Логика прерывания речи
        
    def on_long_press(self, event):
        """Обработка длинного нажатия пробела"""
        print(f"🔑 Длинное нажатие пробела: {event.duration:.3f}с")
        # Логика начала записи речи
        
    def on_speech_started(self, event):
        """Обработка начала речи"""
        print("🎤 Начало распознавания речи")
        
    def on_speech_recognized(self, event):
        """Обработка распознанной речи"""
        print(f"🎤 Распознано: {event.text}")
        
    def on_speech_error(self, event):
        """Обработка ошибки распознавания"""
        print(f"❌ Ошибка распознавания: {event.error_message}")
```

### 2. **State Management** (основной StateManager в `main.py`)

```python
from input_processing import KeyboardMonitor, KeyboardConfig, SpeechRecognizer, SpeechConfig
from input_processing.keyboard.types import KeyEventType
from input_processing.speech.types import SpeechEventType

class SimpleStateManager:
    def __init__(self):
        # Конфигурация
        self.keyboard_config = KeyboardConfig(
            key_to_monitor="space",
            short_press_threshold=0.6,
            long_press_threshold=2.0
        )
        
        self.speech_config = SpeechConfig(
            language="ru-RU",
            timeout=5.0,
            auto_start=True
        )
        
        # Мониторы
        self.keyboard_monitor = KeyboardMonitor(self.keyboard_config)
        self.speech_recognizer = SpeechRecognizer(self.speech_config)
        
        # Состояние
        self.current_state = "SLEEPING"
        self.is_recording = False
        
    async def start(self):
        # Регистрация обработчиков
        self.keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, self.handle_short_press)
        self.keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, self.handle_long_press)
        
        self.speech_recognizer.register_callback(SpeechEventType.RECOGNIZED, self.handle_speech_recognized)
        
        # Запуск мониторинга
        self.keyboard_monitor.start_monitoring()
        await self.speech_recognizer.start()
        
    def handle_short_press(self, event):
        """Обработка короткого нажатия - прерывание"""
        if self.current_state == "LISTENING":
            self.current_state = "SLEEPING"
            print("🔑 Речь прервана коротким нажатием")
            
    def handle_long_press(self, event):
        """Обработка длинного нажатия - начало записи"""
        if self.current_state == "SLEEPING":
            self.current_state = "LISTENING"
            print("🔑 Начало записи речи")
            
    def handle_speech_recognized(self, event):
        """Обработка распознанной речи"""
        if self.current_state == "LISTENING":
            self.current_state = "PROCESSING"
            print(f"🎤 Обработка: {event.text}")
```

### 3. **Module Coordinator** (`client/integration/core/module_coordinator.py`)

```python
from input_processing import KeyboardMonitor, SpeechRecognizer, KeyboardConfig, SpeechConfig

class ModuleCoordinator:
    def __init__(self):
        self.keyboard_monitor = None
        self.speech_recognizer = None
        
    async def initialize_modules(self):
        # Инициализация клавиатуры
        keyboard_config = KeyboardConfig(
            key_to_monitor="space",
            short_press_threshold=0.6,
            long_press_threshold=2.0
        )
        self.keyboard_monitor = KeyboardMonitor(keyboard_config)
        
        # Инициализация речи
        speech_config = SpeechConfig(
            language="ru-RU",
            timeout=5.0,
            auto_start=True
        )
        self.speech_recognizer = SpeechRecognizer(speech_config)
        
        # Запуск
        self.keyboard_monitor.start_monitoring()
        await self.speech_recognizer.start()
        
    def get_system_status(self):
        """Получение статуса системы"""
        return {
            'keyboard_monitoring': self.keyboard_monitor.is_monitoring if self.keyboard_monitor else False,
            'speech_recognition': self.speech_recognizer.is_running if self.speech_recognizer else False,
            'keyboard_status': self.keyboard_monitor.get_status() if self.keyboard_monitor else None,
            'speech_status': self.speech_recognizer.get_status() if self.speech_recognizer else None
        }
```

## 🚀 Быстрый старт

### Базовое использование

```python
import asyncio
from input_processing import KeyboardMonitor, KeyboardConfig, SpeechRecognizer, SpeechConfig

async def main():
    # Конфигурация клавиатуры
    keyboard_config = KeyboardConfig(
        key_to_monitor="space",
        short_press_threshold=0.6,
        long_press_threshold=2.0
    )
    
    # Конфигурация речи
    speech_config = SpeechConfig(
        language="ru-RU",
        timeout=5.0,
        auto_start=True
    )
    
    # Создание мониторов
    keyboard_monitor = KeyboardMonitor(keyboard_config)
    speech_recognizer = SpeechRecognizer(speech_config)
    
    # Обработчики событий
    def on_short_press(event):
        print(f"Короткое нажатие: {event.duration:.3f}с")
        
    def on_long_press(event):
        print(f"Длинное нажатие: {event.duration:.3f}с")
        
    def on_speech_recognized(event):
        print(f"Распознано: {event.text}")
    
    # Регистрация обработчиков
    from input_processing.keyboard.types import KeyEventType
    from input_processing.speech.types import SpeechEventType
    
    keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, on_short_press)
    keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, on_long_press)
    speech_recognizer.register_callback(SpeechEventType.RECOGNIZED, on_speech_recognized)
    
    # Запуск
    keyboard_monitor.start_monitoring()
    await speech_recognizer.start()
    
    # Ожидание
    await asyncio.sleep(30)
    
    # Остановка
    keyboard_monitor.stop_monitoring()
    await speech_recognizer.stop()

asyncio.run(main())
```

## ⚙️ API методы

### KeyboardMonitor

```python
# Создание
monitor = KeyboardMonitor(config)

# Управление
monitor.start_monitoring()           # Запуск мониторинга
monitor.stop_monitoring()            # Остановка мониторинга
monitor.is_monitoring                # Проверка статуса

# Callbacks
monitor.register_callback(event_type, callback)  # Регистрация обработчика

# Статус
status = monitor.get_status()        # Получение статуса
```

### SpeechRecognizer

```python
# Создание
recognizer = SpeechRecognizer(config)

# Управление
await recognizer.start()             # Запуск распознавания
await recognizer.stop()              # Остановка распознавания
recognizer.is_running                # Проверка статуса

# Callbacks
recognizer.register_callback(event_type, callback)  # Регистрация обработчика

# Статус
status = recognizer.get_status()     # Получение статуса
```

## 📊 Типы данных

### KeyEvent

```python
@dataclass
class KeyEvent:
    key: str                         # Клавиша
    event_type: KeyEventType         # Тип события
    timestamp: float                 # Время события
    duration: Optional[float] = None # Длительность нажатия
    data: Optional[Dict[str, Any]] = None  # Дополнительные данные
```

### SpeechEvent

```python
@dataclass
class SpeechEvent:
    event_type: SpeechEventType      # Тип события
    text: Optional[str] = None       # Распознанный текст
    confidence: Optional[float] = None  # Уверенность
    timestamp: float = 0.0           # Время события
    error_message: Optional[str] = None  # Сообщение об ошибке
    data: Optional[Dict[str, Any]] = None  # Дополнительные данные
```

### Конфигурации

```python
@dataclass
class KeyboardConfig:
    key_to_monitor: str = "space"           # Клавиша для мониторинга
    short_press_threshold: float = 0.6      # Порог короткого нажатия
    long_press_threshold: float = 2.0       # Порог длинного нажатия
    event_cooldown: float = 0.1             # Задержка между событиями
    hold_check_interval: float = 0.05       # Интервал проверки удержания
    debounce_time: float = 0.1              # Время дебаунса

@dataclass
class SpeechConfig:
    language: str = "ru-RU"                 # Язык распознавания
    timeout: float = 5.0                    # Таймаут распознавания
    phrase_timeout: float = 0.3             # Таймаут фразы
    non_speaking_duration: float = 0.3      # Длительность тишины
    max_duration: float = 30.0              # Максимальная длительность
    auto_start: bool = True                 # Автозапуск
```

## 🔗 Интеграция с другими модулями

### Audio Device Manager

```python
class AudioService:
    def __init__(self):
        self.keyboard_monitor = KeyboardMonitor(KeyboardConfig())
        self.audio_manager = AudioDeviceManager()
        
    def setup_handlers(self):
        from input_processing.keyboard.types import KeyEventType
        
        self.keyboard_monitor.register_callback(
            KeyEventType.LONG_PRESS, 
            self.start_audio_recording
        )
        
    def start_audio_recording(self, event):
        """Начало записи аудио при длинном нажатии"""
        device = self.audio_manager.get_current_device()
        # Логика записи аудио
```

### gRPC Client

```python
class CommunicationService:
    def __init__(self):
        self.keyboard_monitor = KeyboardMonitor(KeyboardConfig())
        self.grpc_client = GrpcClient()
        
    def setup_handlers(self):
        from input_processing.keyboard.types import KeyEventType
        
        self.keyboard_monitor.register_callback(
            KeyEventType.SHORT_PRESS,
            self.send_interrupt_signal
        )
        
    def send_interrupt_signal(self, event):
        """Отправка сигнала прерывания"""
        self.grpc_client.send_interrupt()
```

### Hardware ID

```python
class DeviceService:
    def __init__(self):
        self.keyboard_monitor = KeyboardMonitor(KeyboardConfig())
        self.hardware_id = get_hardware_id()
        
    def setup_handlers(self):
        from input_processing.keyboard.types import KeyEventType
        
        self.keyboard_monitor.register_callback(
            KeyEventType.LONG_PRESS,
            self.log_device_interaction
        )
        
    def log_device_interaction(self, event):
        """Логирование взаимодействия с устройством"""
        print(f"Устройство {self.hardware_id}: длинное нажатие {event.duration:.3f}с")
```

## ⚠️ Требования

### 1. Python зависимости

```txt
# requirements.txt
pynput>=1.7.6
speechrecognition>=3.10.0
pyaudio>=0.2.11
sounddevice>=0.4.5
numpy>=1.21.0
```

### 2. macOS зависимости

```bash
# Установка зависимостей
brew install portaudio
pip3 install pynput speechrecognition pyaudio sounddevice numpy
```

### 3. Права доступа

```xml
<!-- entitlements.plist -->
<key>com.apple.security.app-sandbox</key>
<true/>
<key>com.apple.security.automation.apple-events</key>
<true/>
<key>com.apple.security.files.user-selected.read-write</key>
<true/>
<key>com.apple.security.network.client</key>
<true/>
<key>com.apple.security.device.audio-input</key>
<true/>
<key>com.apple.security.device.audio-output</key>
<true/>
<key>com.apple.security.temporary-exception.apple-events</key>
<true/>
<key>com.apple.security.temporary-exception.audio-unit-host</key>
<true/>
```

## 🐛 Обработка ошибок

### Обработка ошибок клавиатуры

```python
def on_keyboard_error(error, context):
    print(f"Ошибка клавиатуры в {context}: {error}")

# Регистрация обработчика ошибок
monitor.set_error_callback(on_keyboard_error)
```

### Обработка ошибок речи

```python
def on_speech_error(event):
    print(f"Ошибка распознавания: {event.error_message}")

# Регистрация обработчика ошибок
recognizer.register_callback(SpeechEventType.ERROR, on_speech_error)
```

### Общая обработка ошибок

```python
try:
    monitor.start_monitoring()
    await recognizer.start()
except KeyboardInterrupt:
    print("Прерывание пользователем")
except Exception as e:
    print(f"Критическая ошибка: {e}")
finally:
    monitor.stop_monitoring()
    await recognizer.stop()
```

## 📈 Мониторинг

### Статус клавиатуры

```python
status = monitor.get_status()
print(f"Мониторинг активен: {status['is_monitoring']}")
print(f"Клавиша нажата: {status['key_pressed']}")
print(f"Время последнего события: {status['last_event_time']}")
```

### Статус речи

```python
status = recognizer.get_status()
print(f"Распознавание активно: {status['is_running']}")
print(f"Текущее состояние: {status['current_state']}")
print(f"Время последнего события: {status['last_event_time']}")
```

## 💡 Примеры использования

### Полная интеграция

```python
class NexyApplication:
    def __init__(self):
        # Инициализация всех компонентов
        self.keyboard_monitor = KeyboardMonitor(KeyboardConfig())
        self.speech_recognizer = SpeechRecognizer(SpeechConfig())
        self.audio_manager = AudioDeviceManager()
        self.grpc_client = GrpcClient()
        self.hardware_id = get_hardware_id()
        
    async def start(self):
        # Настройка обработчиков
        self.setup_event_handlers()
        
        # Запуск всех компонентов
        self.keyboard_monitor.start_monitoring()
        await self.speech_recognizer.start()
        await self.audio_manager.start()
        await self.grpc_client.connect()
        
    def setup_event_handlers(self):
        """Настройка всех обработчиков событий"""
        from input_processing.keyboard.types import KeyEventType
        from input_processing.speech.types import SpeechEventType
        
        # Клавиатура
        self.keyboard_monitor.register_callback(KeyEventType.SHORT_PRESS, self.handle_short_press)
        self.keyboard_monitor.register_callback(KeyEventType.LONG_PRESS, self.handle_long_press)
        
        # Речь
        self.speech_recognizer.register_callback(SpeechEventType.RECOGNIZED, self.handle_speech_recognized)
        self.speech_recognizer.register_callback(SpeechEventType.ERROR, self.handle_speech_error)
        
    def handle_short_press(self, event):
        """Короткое нажатие - прерывание"""
        print(f"🔑 Прерывание: {event.duration:.3f}с")
        # Логика прерывания
        
    def handle_long_press(self, event):
        """Длинное нажатие - начало записи"""
        print(f"🔑 Начало записи: {event.duration:.3f}с")
        # Логика начала записи
        
    def handle_speech_recognized(self, event):
        """Распознанная речь"""
        print(f"🎤 Распознано: {event.text}")
        # Отправка на сервер
        self.grpc_client.send_text(event.text)
        
    def handle_speech_error(self, event):
        """Ошибка распознавания"""
        print(f"❌ Ошибка: {event.error_message}")
        # Обработка ошибки
```

## ⚠️ Типичные ошибки и антипаттерны

### ❌ НЕ ДЕЛАЙТЕ ТАК

#### 1. **Неправильная инициализация**

```python
# ❌ ПЛОХО - создание в неправильном месте
class MyApp:
    def __init__(self):
        self.keyboard_monitor = None  # Не инициализирован
        
    async def start(self):
        # Создание в async методе - плохо
        self.keyboard_monitor = KeyboardMonitor(config)
        self.keyboard_monitor.start_monitoring()
```

```python
# ✅ ХОРОШО - правильная инициализация
class MyApp:
    def __init__(self):
        self.keyboard_monitor = KeyboardMonitor(config)  # Создаем сразу
        
    async def start(self):
        # Только запускаем
        self.keyboard_monitor.start_monitoring()
```

#### 2. **Игнорирование async/await**

```python
# ❌ ПЛОХО - игнорирование async
def start_speech():
    recognizer = SpeechRecognizer(config)
    recognizer.start()  # Ошибка! start() - async метод
```

```python
# ✅ ХОРОШО - правильное использование async
async def start_speech():
    recognizer = SpeechRecognizer(config)
    await recognizer.start()  # Правильно с await
```

#### 3. **Неправильная обработка ошибок**

```python
# ❌ ПЛОХО - нет обработки ошибок
def start_monitoring():
    monitor.start_monitoring()  # Может упасть
    recognizer.start()  # Может упасть
```

```python
# ✅ ХОРОШО - с обработкой ошибок
async def start_monitoring():
    try:
        monitor.start_monitoring()
        await recognizer.start()
    except Exception as e:
        print(f"Ошибка запуска: {e}")
```

#### 4. **Неправильное управление жизненным циклом**

```python
# ❌ ПЛОХО - забыли остановить
async def process_data():
    monitor.start_monitoring()
    await recognizer.start()
    # Забыли остановить - утечка ресурсов!
```

```python
# ✅ ХОРОШО - правильное управление ресурсами
async def process_data():
    try:
        monitor.start_monitoring()
        await recognizer.start()
        # Ваша логика здесь
    finally:
        monitor.stop_monitoring()
        await recognizer.stop()
```

### 🚨 Критические ошибки

#### 1. **Множественные экземпляры мониторов**

```python
# ❌ КРИТИЧЕСКАЯ ОШИБКА - несколько мониторов
class App:
    def __init__(self):
        self.monitor1 = KeyboardMonitor(config)  # Плохо!
        self.monitor2 = KeyboardMonitor(config)  # Плохо!
```

```python
# ✅ ПРАВИЛЬНО - один монитор (Singleton pattern)
class App:
    _keyboard_monitor = None
    
    @classmethod
    def get_keyboard_monitor(cls):
        if cls._keyboard_monitor is None:
            cls._keyboard_monitor = KeyboardMonitor(config)
        return cls._keyboard_monitor
```

#### 2. **Блокирующие операции в main thread**

```python
# ❌ КРИТИЧЕСКАЯ ОШИБКА - блокировка UI
def on_button_click():
    monitor.start_monitoring()  # Блокирует UI!
    asyncio.run(recognizer.start())  # Блокирует UI!
```

```python
# ✅ ПРАВИЛЬНО - неблокирующий вызов
async def on_button_click():
    monitor.start_monitoring()  # Не блокирует
    await recognizer.start()  # Не блокирует
```

### 🔧 Лучшие практики

#### 1. **Правильная инициализация**

```python
class InputService:
    def __init__(self):
        self.keyboard_monitor = KeyboardMonitor(KeyboardConfig())
        self.speech_recognizer = SpeechRecognizer(SpeechConfig())
        self.is_running = False
        
    async def start(self):
        if not self.is_running:
            self.keyboard_monitor.start_monitoring()
            await self.speech_recognizer.start()
            self.is_running = True
            
    async def stop(self):
        if self.is_running:
            self.keyboard_monitor.stop_monitoring()
            await self.speech_recognizer.stop()
            self.is_running = False
```

#### 2. **Обработка всех типов ошибок**

```python
async def safe_input_processing():
    monitor = KeyboardMonitor(config)
    recognizer = SpeechRecognizer(config)
    
    try:
        monitor.start_monitoring()
        await recognizer.start()
        
        # Основная логика
        await process_events()
        
    except KeyboardInterrupt:
        print("Прерывание пользователем")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
    finally:
        try:
            monitor.stop_monitoring()
            await recognizer.stop()
        except Exception as e:
            print(f"Ошибка при остановке: {e}")
```

### 📋 Чеклист проверки

Перед интеграцией убедитесь:

- [ ] ✅ Используете `await` с async методами
- [ ] ✅ Обрабатываете все возможные ошибки
- [ ] ✅ Останавливаете мониторы в `finally` блоке
- [ ] ✅ Не создаете множественные экземпляры
- [ ] ✅ Проверяете статус перед операциями
- [ ] ✅ Настроили правильные конфигурации
- [ ] ✅ Регистрируете callbacks для мониторинга
- [ ] ✅ Настроили правильные entitlements для macOS

## ✅ Готовность к продакшену

**МОДУЛЬ ГОТОВ К ВНЕДРЕНИЮ!**

- ✅ Модульная архитектура реализована
- ✅ Обработка клавиатуры протестирована
- ✅ Распознавание речи реализовано
- ✅ Thread-safe операции работают
- ✅ macOS интеграция готова
- ✅ API стабильно и готово

## 🚀 Следующие шаги

1. **Интегрировать в main.py** - добавить инициализацию
2. **Подключить к основному StateManager** - для управления состоянием
3. **Связать с audio_device_manager** - для аудио записи
4. **Настроить в module_coordinator** - для общего управления
5. **Добавить в упаковку** - включить в macOS bundle

---

**Система готова к использованию в продакшене!** 🎉
