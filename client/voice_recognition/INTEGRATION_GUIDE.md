# Руководство по интеграции модуля Voice Recognition

## Обзор модуля

Модуль `voice_recognition` предоставляет функциональность распознавания речи с использованием библиотеки `speech_recognition` и `sounddevice`. Модуль поддерживает асинхронное распознавание, обработку аудио в реальном времени и интеграцию с различными движками распознавания.

## Архитектура модуля

```
voice_recognition/
├── core/
│   ├── speech_recognizer.py    # Основной класс SpeechRecognizer
│   └── types.py               # Типы данных и перечисления
├── config/
│   └── default_config.py      # Конфигурации по умолчанию
├── utils/
│   └── audio_utils.py         # Утилиты для работы с аудио
└── macos/                     # macOS-специфичные компоненты
```

## Основные компоненты

### 1. SpeechRecognizer
Основной класс для распознавания речи.

```python
from voice_recognition import SpeechRecognizer, RecognitionConfig

# Создание с конфигурацией по умолчанию
recognizer = SpeechRecognizer(RecognitionConfig())

# Создание с кастомной конфигурацией
config = RecognitionConfig(
    language="ru-RU",
    sample_rate=44100,
    timeout=10.0
)
recognizer = SpeechRecognizer(config)
```

### 2. RecognitionConfig
Конфигурация для настройки распознавания.

```python
from voice_recognition import RecognitionConfig

config = RecognitionConfig(
    language="en-US",           # Язык распознавания
    sample_rate=16000,          # Частота дискретизации
    chunk_size=1024,            # Размер чанка
    channels=1,                 # Количество каналов
    energy_threshold=100,       # Порог энергии
    timeout=5.0,                # Таймаут распознавания
    max_duration=30.0           # Максимальная длительность
)
```

### 3. RecognitionResult
Результат распознавания речи.

```python
@dataclass
class RecognitionResult:
    text: str                   # Распознанный текст
    confidence: float           # Уверенность (0.0-1.0)
    language: str              # Язык
    duration: float            # Длительность аудио
    timestamp: float           # Временная метка
    alternatives: List[str]    # Альтернативные варианты
```

## Интеграция с другими модулями

### 1. Интеграция с основным приложением

#### ✅ Правильная интеграция:
```python
from voice_recognition import SpeechRecognizer, RecognitionConfig
from mode_management import ModeController, AppMode

class MainApplication:
    def __init__(self):
        # Создание компонентов
        self.recognizer = SpeechRecognizer(RecognitionConfig())
        self.mode_controller = ModeController()
        
        # Настройка callbacks
        self.recognizer.set_state_callback(
            RecognitionState.LISTENING, 
            self._on_listening_start
        )
        
    async def start_voice_recognition(self):
        """Запуск распознавания речи"""
        try:
            # Переключение в режим прослушивания
            await self.mode_controller.transition_to(AppMode.LISTENING)
            
            # Запуск распознавания
            result = await self.recognizer.listen_async()
            
            if result.success:
                await self._process_recognized_text(result.text)
            
        except Exception as e:
            logger.error(f"Ошибка распознавания: {e}")
            await self.mode_controller.transition_to(AppMode.SLEEPING)
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - отсутствует обработка ошибок
recognizer = SpeechRecognizer(RecognitionConfig())
result = recognizer.listen_async()  # Может зависнуть

# НЕ ДЕЛАЙТЕ ТАК - отсутствует управление состоянием
recognizer.start_listening()
# Нет проверки состояния и остановки
```

### 2. Интеграция с audio_device_manager

#### ✅ Правильная интеграция:
```python
from voice_recognition import SpeechRecognizer, find_best_microphone
from audio_device_manager import AudioDeviceManager

class VoiceRecognitionManager:
    def __init__(self):
        self.recognizer = SpeechRecognizer(RecognitionConfig())
        self.audio_manager = AudioDeviceManager()
        
    async def setup_audio_devices(self):
        """Настройка аудио устройств"""
        # Поиск лучшего микрофона
        best_mic = find_best_microphone()
        if best_mic:
            await self.audio_manager.switch_to_device(best_mic)
            
        # Настройка распознавателя
        self.recognizer.set_audio_device(best_mic)
```

### 3. Интеграция с interrupt_management

#### ✅ Правильная интеграция:
```python
from voice_recognition import SpeechRecognizer
from interrupt_management import InterruptCoordinator, InterruptType

class VoiceRecognitionWithInterrupts:
    def __init__(self):
        self.recognizer = SpeechRecognizer(RecognitionConfig())
        self.interrupt_coordinator = InterruptCoordinator()
        
    async def handle_voice_interrupt(self):
        """Обработка прерывания по голосу"""
        # Регистрация прерывания
        await self.interrupt_coordinator.register_interrupt(
            interrupt_type=InterruptType.VOICE_INPUT,
            handler=self._process_voice_input
        )
        
    async def _process_voice_input(self):
        """Обработка голосового ввода"""
        result = await self.recognizer.listen_async()
        if result.success:
            # Обработка распознанного текста
            await self._handle_recognized_text(result.text)
```

## Требования к интеграции

### 1. Зависимости
```python
# Обязательные зависимости
speech_recognition>=3.10.0
sounddevice>=0.4.6
numpy>=1.21.0
asyncio  # Встроенная библиотека

# Опциональные зависимости для различных движков
pocketsphinx>=0.1.15  # Для Sphinx
google-cloud-speech>=2.16.0  # Для Google Cloud
azure-cognitiveservices-speech>=1.19.0  # Для Azure
```

### 2. Системные требования
- **macOS**: 10.14+ (Mojave и выше)
- **Python**: 3.8+
- **Микрофон**: Доступный аудио вход
- **Права доступа**: Разрешение на использование микрофона

### 3. Конфигурация аудио
```python
# Рекомендуемые настройки для macOS
config = RecognitionConfig(
    sample_rate=44100,      # Стандартная частота macOS
    chunk_size=1024,        # Оптимальный размер для macOS
    channels=1,             # Моно для распознавания
    dtype='int16'           # Стандартный тип данных
)
```

## Возможные ошибки и их решения

### 1. Ошибки микрофона

#### Проблема: "No microphone found"
```python
# Решение: Проверка доступности микрофона
from voice_recognition import list_audio_devices

devices = list_audio_devices()
if not devices:
    raise RuntimeError("Микрофон не найден")

# Использование первого доступного микрофона
recognizer.set_audio_device(devices[0])
```

#### Проблема: "Permission denied for microphone"
```python
# Решение: Запрос разрешений
import asyncio
from improved_permissions import PermissionManager, PermissionType

async def request_microphone_permission():
    permission_manager = PermissionManager()
    granted = await permission_manager.request_permission(PermissionType.MICROPHONE)
    if not granted:
        raise PermissionError("Нет разрешения на использование микрофона")
```

### 2. Ошибки распознавания

#### Проблема: "Recognition timeout"
```python
# Решение: Увеличение таймаута
config = RecognitionConfig(
    timeout=10.0,           # Увеличить таймаут
    phrase_timeout=1.0,     # Увеличить паузу между фразами
    max_duration=60.0       # Увеличить максимальную длительность
)
```

#### Проблема: "Low confidence recognition"
```python
# Решение: Настройка порогов
config = RecognitionConfig(
    energy_threshold=50,    # Уменьшить порог энергии
    dynamic_energy_threshold=True,  # Включить динамический порог
    pause_threshold=0.8     # Увеличить паузу
)
```

### 3. Ошибки производительности

#### Проблема: "High CPU usage"
```python
# Решение: Оптимизация конфигурации
config = RecognitionConfig(
    chunk_size=2048,        # Увеличить размер чанка
    sample_rate=16000,      # Уменьшить частоту дискретизации
    max_duration=15.0       # Ограничить длительность
)
```

#### Проблема: "Memory leak"
```python
# Решение: Правильная очистка ресурсов
async def cleanup_recognizer(recognizer):
    """Очистка ресурсов распознавателя"""
    if recognizer.is_listening:
        await recognizer.stop_listening()
    
    # Очистка аудио данных
    recognizer.clear_audio_data()
    
    # Сброс состояния
    recognizer.reset_state()
```

## Формат данных

### 1. Входные данные
```python
# Аудио данные (numpy array)
audio_data = np.array([...], dtype=np.int16)

# Конфигурация
config = RecognitionConfig(
    language="en-US",
    sample_rate=16000,
    channels=1
)
```

### 2. Выходные данные
```python
# Результат распознавания
result = RecognitionResult(
    text="Hello world",
    confidence=0.95,
    language="en-US",
    duration=2.5,
    timestamp=1640995200.0,
    alternatives=["Hello word", "Hello world"]
)

# Метрики
metrics = RecognitionMetrics(
    total_recognitions=100,
    successful_recognitions=95,
    failed_recognitions=5,
    average_confidence=0.87,
    average_duration=2.1
)
```

## Лучшие практики

### 1. Управление состоянием
```python
# Всегда проверяйте состояние перед операциями
if recognizer.state == RecognitionState.IDLE:
    await recognizer.start_listening()
elif recognizer.state == RecognitionState.LISTENING:
    await recognizer.stop_listening()
```

### 2. Обработка ошибок
```python
try:
    result = await recognizer.listen_async()
    if result.success:
        process_text(result.text)
    else:
        logger.warning(f"Распознавание неудачно: {result.error_message}")
except RecognitionError as e:
    logger.error(f"Ошибка распознавания: {e}")
    await handle_recognition_error(e)
```

### 3. Оптимизация производительности
```python
# Используйте подходящую конфигурацию для вашего случая
if use_case == "real_time":
    config = FAST_CONFIG
elif use_case == "high_quality":
    config = HIGH_QUALITY_CONFIG
else:
    config = DEFAULT_RECOGNITION_CONFIG
```

### 4. Мониторинг
```python
# Регулярно проверяйте метрики
metrics = recognizer.get_metrics()
if metrics.failed_recognitions > metrics.successful_recognitions:
    logger.warning("Высокий процент неудачных распознаваний")
    # Адаптация конфигурации
```

## Тестирование интеграции

### 1. Базовый тест
```python
import asyncio
from voice_recognition import SpeechRecognizer, RecognitionConfig

async def test_basic_recognition():
    recognizer = SpeechRecognizer(RecognitionConfig())
    
    try:
        result = await recognizer.listen_async()
        assert result.success, f"Распознавание неудачно: {result.error_message}"
        print(f"Распознано: {result.text}")
    finally:
        await recognizer.cleanup()
```

### 2. Тест производительности
```python
async def test_performance():
    recognizer = SpeechRecognizer(RecognitionConfig())
    
    start_time = time.time()
    results = []
    
    for i in range(10):
        result = await recognizer.listen_async()
        results.append(result)
    
    duration = time.time() - start_time
    success_rate = sum(1 for r in results if r.success) / len(results)
    
    print(f"Время выполнения: {duration:.2f}с")
    print(f"Успешность: {success_rate:.2%}")
```

## Заключение

Модуль `voice_recognition` предоставляет мощную и гибкую функциональность распознавания речи. При правильной интеграции он обеспечивает надежное распознавание голосовых команд и может быть легко интегрирован в существующую архитектуру приложения.

Ключевые моменты для успешной интеграции:
- Правильная настройка конфигурации
- Обработка ошибок и исключений
- Управление состоянием и ресурсами
- Мониторинг производительности
- Тестирование всех сценариев использования
