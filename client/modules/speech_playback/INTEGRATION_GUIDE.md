# 🎵 Speech Playback - Руководство по интеграции

## 📋 Обзор модуля

Модуль `speech_playback` обеспечивает последовательное воспроизведение аудио чанков с поддержкой:
- Последовательной очереди воспроизведения
- Потоковой обработки аудио данных
- macOS Core Audio интеграции
- Управления состояниями и метриками
- Thread-safe операций

## 🔗 Интеграция с другими модулями

### 1. Интеграция с Text Processor

#### ✅ Правильная интеграция:
```python
from speech_playback import SequentialSpeechPlayer, PlayerConfig
from text_processor import TextProcessor
from audio_generator import AudioGenerator

# Создание компонентов
player = SequentialSpeechPlayer(PlayerConfig(
    sample_rate=48000,  # Azure TTS использует 48000Hz
    channels=1,         # Azure TTS генерирует моно
    dtype='int16'
))

text_processor = TextProcessor()
audio_generator = AudioGenerator()

# Генерация и воспроизведение
async def process_text_with_audio(text: str):
    # Генерируем аудио через Azure TTS
    audio_data = await audio_generator.generate_audio(text)
    
    if audio_data is not None:
        # Добавляем в очередь воспроизведения
        chunk_id = player.add_audio_data(
            audio_data=audio_data,
            priority=0,
            metadata={"text": text, "source": "azure_tts"}
        )
        
        # Запускаем воспроизведение
        if not player.is_playing():
            player.start_playback()
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК:
# 1. Не добавляйте аудио данные напрямую в буфер
player.chunk_buffer.add_chunk(audio_data)  # ❌

# 2. Не изменяйте состояние плеера напрямую
player.state_manager.current_state = PlaybackState.PLAYING  # ❌

# 3. Не используйте неправильные форматы аудио
player.add_audio_data(audio_data, sample_rate=22050)  # ❌ Должно быть 48000Hz
```

### 2. Интеграция с Mode Management

#### ✅ Правильная интеграция:
```python
from mode_management import ModeController, AppMode
from speech_playback import SequentialSpeechPlayer

class SpeakingMode:
    def __init__(self):
        self.player = SequentialSpeechPlayer()
        self.player.initialize()
    
    async def enter_mode(self):
        # Настраиваем callbacks для отслеживания
        self.player.set_callbacks(
            on_playback_completed=self._on_speech_completed,
            on_error=self._on_speech_error
        )
    
    async def exit_mode(self):
        # Останавливаем воспроизведение при выходе из режима
        if self.player.is_playing():
            self.player.stop_playback()
    
    def _on_speech_completed(self):
        # Переключаемся в режим прослушивания после завершения речи
        self.mode_controller.switch_mode(AppMode.LISTENING)
```

### 3. Интеграция с Interrupt Management

#### ✅ Правильная интеграция:
```python
from interrupt_management import InterruptCoordinator, InterruptType
from speech_playback import SequentialSpeechPlayer

class SpeechInterruptHandler:
    def __init__(self):
        self.player = SequentialSpeechPlayer()
    
    async def handle_interrupt(self, interrupt_event):
        if interrupt_event.interrupt_type == InterruptType.SPEECH_INTERRUPT:
            # Приоритетное прерывание речи
            if self.player.is_playing():
                self.player.pause_playback()
                # Обрабатываем новое сообщение
                await self.process_urgent_message(interrupt_event.data)
```

## 📊 Формат данных

### Входные данные (add_audio_data):
```python
# Формат аудио данных
audio_data: np.ndarray  # 1D массив int16, 48000Hz, моно
metadata: dict = {
    "text": str,           # Исходный текст
    "chunk_number": int,   # Номер чанка
    "source": str,         # Источник генерации
    "priority": int        # Приоритет (0 = обычный)
}
```

### Выходные данные (callbacks):
```python
# ChunkInfo объект
chunk_info = {
    "id": str,                    # Уникальный ID чанка
    "state": ChunkState,          # Текущее состояние
    "metadata": dict,             # Метаданные
    "duration": float,            # Длительность в секундах
    "size": int                   # Размер в сэмплах
}
```

## ⚠️ Возможные ошибки и их решения

### 1. Ошибки инициализации
```python
# ❌ Ошибка: "Core Audio не инициализирован"
# ✅ Решение: Проверьте инициализацию
if not player.initialize():
    raise RuntimeError("Не удалось инициализировать плеер")

# ❌ Ошибка: "Нет доступных аудио устройств"
# ✅ Решение: Проверьте подключение устройств
devices = player.get_available_devices()
if not devices:
    raise RuntimeError("Нет доступных аудио устройств")
```

### 2. Ошибки формата аудио
```python
# ❌ Ошибка: "Неверный формат аудио"
# ✅ Решение: Используйте правильный формат
audio_data = audio_data.astype(np.int16)  # int16
audio_data = audio_data.reshape(-1, 1)    # 1D массив
# Частота дискретизации должна быть 48000Hz
```

### 3. Ошибки состояния
```python
# ❌ Ошибка: "Невозможно запустить воспроизведение в текущем состоянии"
# ✅ Решение: Проверьте состояние перед операциями
if player.state_manager.current_state == PlaybackState.IDLE:
    player.start_playback()
else:
    logger.warning("Плеер не в состоянии IDLE")
```

### 4. Ошибки памяти
```python
# ❌ Ошибка: "Превышен лимит памяти"
# ✅ Решение: Настройте лимиты памяти
config = PlayerConfig(
    max_memory_mb=100,  # Уменьшите лимит
    buffer_size=512     # Уменьшите размер буфера
)
```

## 🔧 Требования к интеграции

### 1. Системные требования
- **macOS 10.15+** (для Core Audio)
- **Python 3.8+**
- **Зависимости:** `sounddevice`, `numpy`, `pydub`

### 2. Аудио требования
- **Формат:** 16-bit PCM, 48000Hz, моно
- **Тип данных:** `numpy.int16`
- **Размер чанка:** рекомендуется 1-5 секунд

### 3. Память
- **Минимум:** 50MB свободной памяти
- **Рекомендуется:** 200MB для буферизации
- **Максимум:** настраивается через `max_memory_mb`

## 🚀 Примеры использования

### 1. Базовое воспроизведение
```python
import asyncio
from speech_playback import SequentialSpeechPlayer, PlayerConfig

async def basic_playback():
    # Создание плеера
    player = SequentialSpeechPlayer(PlayerConfig())
    player.initialize()
    
    # Добавление аудио данных
    chunk_id = player.add_audio_data(audio_data, metadata={"text": "Hello"})
    
    # Запуск воспроизведения
    player.start_playback()
    
    # Ожидание завершения
    while player.is_playing():
        await asyncio.sleep(0.1)
    
    player.shutdown()
```

### 2. Потоковое воспроизведение
```python
async def streaming_playback(audio_generator, text_stream):
    player = SequentialSpeechPlayer()
    player.initialize()
    
    # Обработка потока текста
    async for text in text_stream:
        audio_data = await audio_generator.generate_audio(text)
        if audio_data is not None:
            player.add_audio_data(audio_data, metadata={"text": text})
    
    # Запуск воспроизведения
    player.start_playback()
    
    # Ожидание завершения
    while player.is_playing():
        await asyncio.sleep(0.1)
```

### 3. Управление состоянием
```python
def setup_player_callbacks(player):
    def on_chunk_started(chunk_info):
        print(f"Начало воспроизведения: {chunk_info.id}")
    
    def on_chunk_completed(chunk_info):
        print(f"Завершение воспроизведения: {chunk_info.id}")
    
    def on_playback_completed():
        print("Все чанки воспроизведены")
    
    def on_error(error):
        print(f"Ошибка воспроизведения: {error}")
    
    player.set_callbacks(
        on_chunk_started=on_chunk_started,
        on_chunk_completed=on_chunk_completed,
        on_playback_completed=on_playback_completed,
        on_error=on_error
    )
```

## 📈 Мониторинг и отладка

### 1. Получение статуса
```python
status = player.get_status()
print(f"Состояние: {status['state']}")
print(f"Чанков в очереди: {status['chunk_count']}")
print(f"Размер буфера: {status['buffer_size']} байт")
```

### 2. Логирование
```python
import logging

# Настройка логирования для speech_playback
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('speech_playback')
logger.setLevel(logging.DEBUG)
```

### 3. Обработка ошибок
```python
try:
    player.start_playback()
except Exception as e:
    logger.error(f"Ошибка запуска воспроизведения: {e}")
    # Обработка ошибки
```

## 🔄 Жизненный цикл модуля

1. **Инициализация:** `player.initialize()`
2. **Настройка:** `player.set_callbacks()`
3. **Добавление данных:** `player.add_audio_data()`
4. **Запуск:** `player.start_playback()`
5. **Управление:** `player.pause_playback()`, `player.resume_playback()`
6. **Остановка:** `player.stop_playback()`
7. **Завершение:** `player.shutdown()`

## ⚡ Производительность

### Рекомендации:
- Используйте чанки размером 1-5 секунд
- Не превышайте лимит памяти
- Регулярно очищайте завершенные чанки
- Мониторьте использование CPU

### Оптимизация:
```python
# Оптимальная конфигурация
config = PlayerConfig(
    sample_rate=48000,
    channels=1,
    buffer_size=1024,      # Оптимальный размер буфера
    max_memory_mb=200,     # Разумный лимит памяти
    auto_device_selection=True
)
```

## 🛡️ Безопасность

- Все операции thread-safe
- Автоматическая очистка памяти
- Защита от переполнения буферов
- Валидация входных данных

---

**Примечание:** Этот модуль предназначен для использования в macOS приложениях и требует соответствующих разрешений для работы с аудио.
