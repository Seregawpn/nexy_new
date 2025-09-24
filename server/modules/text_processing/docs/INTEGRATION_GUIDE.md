# 📚 Text Processing Module - Руководство по Интеграции

## 🎯 Обзор

Text Processing Module - это универсальный модуль для обработки текстовых запросов с поддержкой fallback логики. Модуль использует Gemini Live API как основной провайдер и LangChain как fallback.

## 🏗️ Архитектура

### Компоненты модуля:
- **TextProcessor** - основной координатор
- **FallbackManager** - управление переключением между провайдерами
- **GeminiLiveProvider** - основной провайдер (приоритет 1)
- **LangChainProvider** - fallback провайдер (приоритет 2)
- **Config** - конфигурация модуля

### Принципы работы:
1. **Универсальный интерфейс** - все провайдеры реализуют UniversalProviderInterface
2. **Fallback логика** - автоматическое переключение при ошибках
3. **Circuit breaker** - защита от каскадных сбоев
4. **Health checks** - мониторинг состояния провайдеров

## 🔧 Установка и Настройка

### 1. Установка зависимостей

```bash
# Основные зависимости
pip install google-generativeai
pip install langchain-google-genai

# Для разработки
pip install pytest pytest-asyncio
```

### 2. Настройка переменных окружения

```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### 3. Базовая конфигурация

```python
config = {
    'gemini_api_key': 'your-api-key',
    'gemini_model': 'gemini-2.0-flash-exp',
    'gemini_temperature': 0.7,
    'gemini_max_tokens': 2048,
    'langchain_model': 'gemini-pro',
    'fallback_timeout': 30,
    'circuit_breaker_threshold': 3,
    'circuit_breaker_timeout': 300
}
```

## 🚀 Использование

### Базовое использование

```python
from modules.text_processing.core.text_processor import TextProcessor

# Создание процессора
processor = TextProcessor(config)

# Инициализация
await processor.initialize()

# Обработка текста
async for result in processor.process_text("Hello, how are you?"):
    print(result, end='')

# Очистка ресурсов
await processor.cleanup()
```

### Расширенное использование

```python
# Получение статуса
status = processor.get_status()
print(f"Initialized: {status['is_initialized']}")
print(f"Healthy providers: {len(processor.get_healthy_providers())}")

# Получение метрик
metrics = processor.get_metrics()
print(f"Total requests: {metrics['fallback_manager']['total_requests']}")

# Сброс метрик
processor.reset_metrics()
```

## 📊 Мониторинг и Отладка

### Статус провайдеров

```python
# Получение статуса всех провайдеров
status = processor.get_status()
for provider in status['providers']:
    print(f"Provider: {provider['name']}")
    print(f"Status: {provider['status']}")
    print(f"Error count: {provider['error_count']}")
    print(f"Success rate: {provider['success_rate']:.2%}")
```

### Метрики производительности

```python
# Получение метрик
metrics = processor.get_metrics()
fallback_metrics = metrics['fallback_manager']

print(f"Total requests: {fallback_metrics['total_requests']}")
print(f"Successful requests: {fallback_metrics['successful_requests']}")
print(f"Failed requests: {fallback_metrics['failed_requests']}")
print(f"Fallback switches: {fallback_metrics['fallback_switches']}")
print(f"Success rate: {fallback_metrics['success_rate']:.2%}")
```

### Health checks

```python
# Проверка здоровья провайдеров
healthy_providers = processor.get_healthy_providers()
failed_providers = processor.get_failed_providers()

print(f"Healthy: {len(healthy_providers)}")
print(f"Failed: {len(failed_providers)}")
```

## 🔄 Fallback Логика

### Принципы работы:
1. **Приоритет провайдеров**: Gemini Live (1) → LangChain (2)
2. **Circuit breaker**: отключение провайдера после 3 ошибок
3. **Автоматическое восстановление**: проверка через 5 минут
4. **Health checks**: проверка состояния перед использованием

### Настройка fallback:

```python
config = {
    'circuit_breaker_threshold': 3,  # Количество ошибок до отключения
    'circuit_breaker_timeout': 300,  # Время до повторной проверки (сек)
    'fallback_timeout': 30,          # Таймаут для fallback (сек)
}
```

## ⚠️ Обработка Ошибок

### Типы ошибок:
1. **Инициализация**: отсутствие API ключей, недоступность сервисов
2. **Обработка**: ошибки API, таймауты, пустые ответы
3. **Fallback**: все провайдеры недоступны

### Обработка в коде:

```python
try:
    async for result in processor.process_text(prompt):
        yield result
except Exception as e:
    logger.error(f"Text processing error: {e}")
    yield f"Error: {str(e)}"
```

## 🧪 Тестирование

### Запуск тестов:

```bash
# Все тесты модуля
python -m pytest modules/text_processing/tests/

# Конкретный тест
python -m pytest modules/text_processing/tests/test_text_processor.py

# С покрытием
python -m pytest modules/text_processing/tests/ --cov=modules.text_processing
```

### Тестирование провайдеров:

```python
# Тест конкретного провайдера
from modules.text_processing.providers.gemini_live_provider import GeminiLiveProvider

provider = GeminiLiveProvider(config)
await provider.initialize()

results = []
async for result in provider.process("Test prompt"):
    results.append(result)

assert len(results) > 0
```

## 🔧 Конфигурация

### Полная конфигурация:

```python
config = {
    # Gemini Live настройки
    'gemini_api_key': 'your-api-key',
    'gemini_model': 'gemini-2.0-flash-exp',
    'gemini_temperature': 0.7,
    'gemini_max_tokens': 2048,
    
    # LangChain настройки
    'langchain_model': 'gemini-pro',
    'langchain_temperature': 0.7,
    
    # Fallback настройки
    'fallback_timeout': 30,
    'circuit_breaker_threshold': 3,
    'circuit_breaker_timeout': 300,
    
    # Логирование
    'log_level': 'INFO',
    'log_requests': True,
    'log_responses': False,
    
    # Производительность
    'max_concurrent_requests': 10,
    'request_timeout': 60
}
```

### Валидация конфигурации:

```python
from modules.text_processing.config import TextProcessingConfig

config = TextProcessingConfig(your_config)
if config.validate():
    print("Configuration is valid")
else:
    print("Configuration validation failed")
```

## 📈 Производительность

### Оптимизация:
1. **Кэширование**: повторные запросы кэшируются
2. **Параллелизм**: поддержка concurrent запросов
3. **Streaming**: потоковая передача результатов
4. **Circuit breaker**: защита от перегрузки

### Мониторинг:
- Метрики запросов и ошибок
- Статус провайдеров
- Время ответа
- Успешность fallback

## 🚨 Устранение Неполадок

### Частые проблемы:

1. **"Provider not available"**
   - Проверьте установку зависимостей
   - Проверьте API ключи

2. **"All providers failed"**
   - Проверьте интернет соединение
   - Проверьте статус API сервисов
   - Проверьте лимиты API

3. **"Configuration validation failed"**
   - Проверьте наличие API ключей
   - Проверьте корректность параметров

### Логирование:

```python
import logging

# Включение подробного логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('modules.text_processing')
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

## 📞 Поддержка

### Полезные команды:

```python
# Получение сводки
summary = processor.get_summary()
print(summary)

# Принудительный сброс провайдера
processor.fallback_manager.force_reset_provider("gemini_live")

# Проверка здоровья
for provider in processor.providers:
    health = await provider.health_check()
    print(f"{provider.name}: {'Healthy' if health else 'Unhealthy'}")
```

### Контакты:
- Документация: `modules/text_processing/docs/`
- Тесты: `modules/text_processing/tests/`
- Логи: проверьте логи приложения

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: Python 3.11+, AsyncIO
