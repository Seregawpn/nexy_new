# 📚 Audio Generation Module - Руководство по Интеграции

## 🎯 Обзор

Audio Generation Module - это модуль для преобразования текста в речь с использованием Azure Cognitive Services Speech. Модуль поддерживает streaming аудио, различные форматы и настройки голоса.

## 🏗️ Архитектура

### Компоненты модуля:
- **AudioProcessor** - основной координатор
- **AzureTTSProvider** - провайдер Azure TTS
- **Config** - конфигурация модуля

### Принципы работы:
1. **Единый провайдер** - Azure Cognitive Services Speech
2. **Streaming поддержка** - потоковая передача аудио
3. **SSML поддержка** - расширенный контроль голоса
4. **Health checks** - мониторинг состояния провайдера

## 🔧 Установка и Настройка

### 1. Установка зависимостей

```bash
# Azure Speech SDK
pip install azure-cognitiveservices-speech

# Для разработки
pip install pytest pytest-asyncio
```

### 2. Настройка переменных окружения

```bash
export AZURE_SPEECH_KEY="your-azure-speech-key"
export AZURE_SPEECH_REGION="your-azure-region"
```

### 3. Базовая конфигурация

```python
config = {
    'azure_speech_key': 'your-azure-speech-key',
    'azure_speech_region': 'eastus',
    'azure_voice_name': 'en-US-AriaNeural',
    'azure_voice_style': 'friendly',
    'azure_speech_rate': 1.0,
    'azure_speech_pitch': 1.0,
    'azure_speech_volume': 1.0,
    'audio_format': 'riff-16khz-16bit-mono-pcm',
    'sample_rate': 16000,
    'channels': 1,
    'bits_per_sample': 16,
    'streaming_enabled': True,
    'streaming_chunk_size': 4096
}
```

## 🚀 Использование

### Базовое использование

```python
from modules.audio_generation.core.audio_processor import AudioProcessor

# Создание процессора
processor = AudioProcessor(config)

# Инициализация
await processor.initialize()

# Генерация речи
audio_chunks = []
async for chunk in processor.generate_speech("Hello, how are you?"):
    audio_chunks.append(chunk)

# Очистка ресурсов
await processor.cleanup()
```

### Потоковая генерация

```python
# Потоковая генерация речи
async for chunk in processor.generate_speech_streaming("Long text for streaming"):
    # Отправляем chunk клиенту в реальном времени
    send_audio_to_client(chunk)
```

### Обновление настроек голоса

```python
# Обновление настроек голоса
new_voice_settings = {
    'voice_name': 'en-US-JennyNeural',
    'voice_style': 'cheerful',
    'speech_rate': 1.2,
    'speech_pitch': 0.8,
    'speech_volume': 0.9
}

success = processor.update_voice_settings(new_voice_settings)
```

## 📊 Мониторинг и Отладка

### Статус процессора

```python
# Получение статуса процессора
status = processor.get_status()
print(f"Initialized: {status['is_initialized']}")
print(f"Provider available: {status['provider']['is_available']}")
print(f"Voice: {status['provider']['voice_name']}")
```

### Метрики производительности

```python
# Получение метрик
metrics = processor.get_metrics()
provider_metrics = metrics['provider']

print(f"Total requests: {provider_metrics['total_requests']}")
print(f"Successful requests: {provider_metrics['successful_requests']}")
print(f"Failed requests: {provider_metrics['failed_requests']}")
print(f"Success rate: {provider_metrics['success_rate']:.2%}")
```

### Информация об аудио

```python
# Получение информации об аудио формате
audio_info = processor.get_audio_info()
print(f"Format: {audio_info['format']}")
print(f"Sample rate: {audio_info['sample_rate']}")
print(f"Channels: {audio_info['channels']}")
print(f"Bits per sample: {audio_info['bits_per_sample']}")
```

## 🎵 Настройки Голоса

### Доступные голоса

```python
# Получение доступных опций голоса
voice_options = processor.get_voice_options()

print("Available voices:")
for voice in voice_options['voice_names']:
    print(f"  - {voice}")

print("Available styles:")
for style in voice_options['voice_styles']:
    print(f"  - {style}")

print("Available formats:")
for format in voice_options['audio_formats']:
    print(f"  - {format}")
```

### Популярные комбинации голосов

```python
# Дружелюбный женский голос
voice_settings = {
    'voice_name': 'en-US-AriaNeural',
    'voice_style': 'friendly',
    'speech_rate': 1.0
}

# Веселый мужской голос
voice_settings = {
    'voice_name': 'en-US-DavisNeural',
    'voice_style': 'cheerful',
    'speech_rate': 1.1
}

# Серьезный профессиональный голос
voice_settings = {
    'voice_name': 'en-US-JennyNeural',
    'voice_style': 'serious',
    'speech_rate': 0.9
}
```

## ⚙️ Конфигурация

### Полная конфигурация

```python
config = {
    # Azure настройки
    'azure_speech_key': 'your-azure-speech-key',
    'azure_speech_region': 'eastus',
    
    # Настройки голоса
    'azure_voice_name': 'en-US-AriaNeural',
    'azure_voice_style': 'friendly',
    'azure_speech_rate': 1.0,
    'azure_speech_pitch': 1.0,
    'azure_speech_volume': 1.0,
    
    # Аудио настройки
    'audio_format': 'riff-16khz-16bit-mono-pcm',
    'sample_rate': 16000,
    'channels': 1,
    'bits_per_sample': 16,
    
    # Streaming настройки
    'streaming_enabled': True,
    'streaming_chunk_size': 4096,
    
    # Производительность
    'max_concurrent_requests': 10,
    'request_timeout': 60,
    'connection_timeout': 30,
    
    # Логирование
    'log_level': 'INFO',
    'log_requests': True,
    'log_responses': False
}
```

### Валидация конфигурации

```python
from modules.audio_generation.config import AudioGenerationConfig

config = AudioGenerationConfig(your_config)
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration validation failed")
```

## 🎛️ Streaming Аудио

### Включение streaming

```python
config = {
    'streaming_enabled': True,
    'streaming_chunk_size': 2048  # 2KB chunks
}

processor = AudioProcessor(config)
await processor.initialize()

# Потоковая генерация
async for chunk in processor.generate_speech_streaming("Long text"):
    # Отправляем chunk немедленно
    yield chunk
```

### Отключение streaming

```python
config = {
    'streaming_enabled': False
}

# Используется обычная генерация с большими chunks
```

## ⚠️ Обработка Ошибок

### Типы ошибок:
1. **Инициализация**: отсутствие Azure ключей, недоступность сервиса
2. **Генерация**: ошибки Azure API, таймауты, пустые ответы
3. **Streaming**: проблемы с передачей данных

### Обработка в коде:

```python
try:
    async for chunk in processor.generate_speech(text):
        yield chunk
except Exception as e:
    logger.error(f"Audio generation error: {e}")
    # Fallback или уведомление об ошибке
    yield b''  # Пустой chunk или error message
```

### Обработка таймаутов:

```python
import asyncio

try:
    async with asyncio.timeout(30):  # 30 секунд таймаут
        async for chunk in processor.generate_speech(text):
            yield chunk
except asyncio.TimeoutError:
    logger.error("Audio generation timeout")
    yield b''  # Пустой chunk
```

## 🧪 Тестирование

### Запуск тестов:

```bash
# Все тесты модуля
python -m pytest modules/audio_generation/tests/

# Конкретный тест
python -m pytest modules/audio_generation/tests/test_audio_processor.py

# С покрытием
python -m pytest modules/audio_generation/tests/ --cov=modules.audio_generation
```

### Тестирование провайдера:

```python
# Тест Azure TTS провайдера
from modules.audio_generation.providers.azure_tts_provider import AzureTTSProvider

config = {
    'speech_key': 'test-key',
    'speech_region': 'eastus'
}

provider = AzureTTSProvider(config)
await provider.initialize()

audio_chunks = []
async for chunk in provider.process("Test text"):
    audio_chunks.append(chunk)

assert len(audio_chunks) > 0
```

### Тестирование с моками:

```python
# Тест без реального Azure API
from unittest.mock import patch, MagicMock

with patch('modules.audio_generation.providers.azure_tts_provider.speechsdk') as mock_speechsdk:
    mock_speechsdk.ResultReason.SynthesizingAudioCompleted = "SynthesizingAudioCompleted"
    
    # Настраиваем моки...
    
    # Тестируем функциональность
    result = await provider.process("Test")
```

## 📈 Производительность

### Оптимизация:
1. **Streaming**: уменьшает задержку для длинных текстов
2. **Кэширование**: повторные запросы с одинаковым текстом
3. **Connection pooling**: переиспользование соединений
4. **Chunk size tuning**: оптимизация размера chunks

### Мониторинг:
- Время генерации аудио
- Размер генерируемых chunks
- Использование памяти
- Статус Azure API

### Рекомендации:
- Используйте streaming для текстов > 100 символов
- Настройте chunk_size в зависимости от сети
- Мониторьте Azure API лимиты
- Используйте подходящий аудио формат

## 🚨 Устранение Неполадок

### Частые проблемы:

1. **"Provider not available"**
   - Проверьте установку Azure Speech SDK
   - Проверьте API ключи и регион

2. **"Synthesis failed"**
   - Проверьте интернет соединение
   - Проверьте статус Azure Speech Service
   - Проверьте лимиты API

3. **"Configuration validation failed"**
   - Проверьте наличие Azure ключей
   - Проверьте корректность параметров голоса

4. **"No audio data generated"**
   - Проверьте текст на специальные символы
   - Попробуйте другой голос
   - Проверьте SSML синтаксис

### Логирование:

```python
import logging

# Включение подробного логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('modules.audio_generation')
```

### Диагностика:

```python
# Проверка статуса
status = processor.get_status()
print(f"Provider status: {status['provider']['status']}")
print(f"Error count: {status['provider']['error_count']}")
print(f"Last error: {status['provider']['last_error']}")

# Проверка health
health = await processor.provider.health_check()
print(f"Provider healthy: {health}")
```

## 🔄 Обновления

### Обновление модуля:
1. Остановите процессор: `await processor.cleanup()`
2. Обновите код
3. Перезапустите: `await processor.initialize()`

### Обновление конфигурации:
1. Измените конфигурацию
2. Перезапустите процессор
3. Проверьте статус: `processor.get_status()`

### Обновление настроек голоса:
```python
# Обновление без перезапуска
new_settings = {
    'voice_name': 'en-US-JennyNeural',
    'voice_style': 'cheerful'
}

success = processor.update_voice_settings(new_settings)
```

## 📞 Поддержка

### Полезные команды:

```python
# Получение сводки
summary = processor.get_summary()
print(summary)

# Сброс метрик
processor.reset_metrics()

# Получение доступных голосов
voice_options = processor.get_voice_options()
```

### Контакты:
- Документация: `modules/audio_generation/docs/`
- Тесты: `modules/audio_generation/tests/`
- Логи: проверьте логи приложения

### Azure Speech Service:
- [Azure Speech Service Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/)
- [Voice Gallery](https://speech.microsoft.com/portal/voicegallery)
- [SSML Reference](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/speech-synthesis-markup)

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: Python 3.11+, AsyncIO, Azure Speech SDK 1.34+
