# Text Filtering Module - Инструкция по Интеграции

## 🎯 Обзор

Text Filtering Module - это универсальный модуль для предобработки, фильтрации и очистки текстовых данных. Обеспечивает высококачественную обработку текста с возможностью настройки различных фильтров и валидации.

## 🏗️ Архитектура

### Универсальный Стандарт Взаимодействия

```
Text Input → TextFilterManager → TextCleaningProvider + ContentFilteringProvider + SentenceProcessingProvider → Filtered Output
```

### Компоненты

1. **TextFilterManager** - основной координатор фильтрации текста
2. **TextCleaningProvider** - очистка и предобработка текста
3. **ContentFilteringProvider** - фильтрация контента и валидация
4. **SentenceProcessingProvider** - обработка предложений
5. **Universal Module Interface** - стандартный интерфейс модуля

## 📋 Функциональность

### Основные операции

- **filter_text** - полная фильтрация текста
- **clean_text** - очистка текста от лишних символов
- **split_sentences** - разбиение на предложения
- **validate_text** - валидация текста
- **preprocess_text** - предобработка текста

### Очистка текста

- Удаление лишних пробелов и переносов строк
- Удаление специальных символов
- Нормализация Unicode
- Удаление управляющих символов

### Фильтрация контента

- Проверка длины текста
- Блокировка пустого текста
- Блокировка текста только из пробелов
- Валидация кодировки и Unicode

### Обработка предложений

- Разбиение текста на предложения
- Проверка завершенности предложений
- Автоматическое добавление точек
- Сохранение форматирования

## 🔧 Использование

### Инициализация

```python
from modules.text_filtering import TextFilterManager
from modules.text_filtering.config import TextFilteringConfig

# Создание конфигурации
config = TextFilteringConfig()

# Создание менеджера
text_filter_manager = TextFilterManager(config)

# Инициализация
await text_filter_manager.initialize()
```

### Фильтрация текста

```python
# Полная фильтрация текста
text = "  Hello, world!   This is a test.  "
result = await text_filter_manager.filter_text(text)

if result["success"]:
    print(f"Original: '{result['original_text']}'")
    print(f"Filtered: '{result['filtered_text']}'")
    print(f"Operations: {result['operations']}")
    print(f"Processing time: {result['processing_time_ms']:.1f}ms")
else:
    print(f"Error: {result['error']}")
```

### Очистка текста

```python
# Очистка текста
dirty_text = "  Hello   world!   @#$%   "
result = await text_filter_manager.clean_text(dirty_text)

if result["success"]:
    print(f"Cleaned text: '{result['cleaned_text']}'")
    print(f"Operations: {result['operations']}")
```

### Разбиение на предложения

```python
# Разбиение на предложения
text = "Hello world! How are you? I'm fine."
result = await text_filter_manager.split_sentences(text)

if result["success"]:
    print(f"Sentences: {result['sentences']}")
    print(f"Count: {result['sentence_count']}")
```

### Валидация текста

```python
# Валидация текста
text = "Valid text content"
result = await text_filter_manager.validate_text(text)

if result["success"]:
    if result["valid"]:
        print("Text is valid")
    else:
        print(f"Validation errors: {result['errors']}")
```

## ⚙️ Конфигурация

### Переменные окружения

```bash
# Настройки очистки текста
TEXT_CLEANING_ENABLED=true
REMOVE_SPECIAL_CHARS=true
NORMALIZE_UNICODE=true

# Настройки фильтрации контента
CONTENT_FILTERING_ENABLED=true
MAX_TEXT_LENGTH=10000
MIN_TEXT_LENGTH=1

# Настройки предобработки
REMOVE_URLS=false
REMOVE_EMAILS=false
REMOVE_PHONE_NUMBERS=false
REMOVE_SENSITIVE_DATA=false

# Настройки производительности
TEXT_FILTER_CACHE_ENABLED=true
TEXT_FILTER_CACHE_SIZE=1000
TEXT_FILTER_CACHE_TTL=3600

# Настройки логирования
LOG_FILTERED_CONTENT=false
LOG_PERFORMANCE=true
```

### Конфигурация модулей

```python
# В config.py можно настроить различные аспекты фильтрации
text_cleaning = {
    "enabled": True,
    "remove_extra_whitespace": True,
    "remove_special_chars": True,
    "normalize_unicode": True
}

content_filtering = {
    "enabled": True,
    "max_length": 10000,
    "min_length": 1,
    "block_empty": True
}

sentence_splitting = {
    "enabled": True,
    "sentence_pattern": r'(?<=[.!?])\s*(?=[A-ZА-Я0-9])|(?<=[.!?])\s*$',
    "auto_add_period": True
}
```

## 🧪 Тестирование

### Unit тесты

```python
# Тестирование TextFilterManager
pytest modules/text_filtering/tests/test_text_filter_manager.py

# Тестирование провайдеров
pytest modules/text_filtering/tests/test_text_cleaning_provider.py
pytest modules/text_filtering/tests/test_content_filtering_provider.py
pytest modules/text_filtering/tests/test_sentence_processing_provider.py
```

### Integration тесты

```python
# Тестирование полного цикла фильтрации
pytest modules/text_filtering/tests/test_integration.py
```

### Universal тесты

```python
# Тестирование соответствия универсальным стандартам
pytest modules/text_filtering/universal_tests/test_universal_compliance.py
```

## 📊 Мониторинг

### Статистика фильтрации

```python
# Получение статистики
stats = text_filter_manager.get_statistics()
print(f"Total processed: {stats['total_processed']}")
print(f"Filter rate: {stats['filter_rate']:.2%}")
print(f"Error rate: {stats['error_rate']:.2%}")
print(f"Average processing time: {stats['avg_processing_time_ms']:.1f}ms")
print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
```

### Статус провайдеров

```python
# Статус провайдеров
text_cleaning_status = await text_cleaning_provider.get_status()
content_filtering_status = await content_filtering_provider.get_status()
sentence_processing_status = await sentence_processing_provider.get_status()
```

## 🔒 Безопасность

### Фильтрация контента

- Проверка длины текста для предотвращения DoS
- Валидация кодировки для предотвращения атак
- Блокировка пустого и некорректного контента
- Ограничение размера обрабатываемого текста

### Удаление чувствительных данных

- Удаление URL (опционально)
- Удаление email адресов (опционально)
- Удаление номеров телефонов (опционально)
- Удаление чувствительных данных (опционально)

### Производительность

- Кэширование результатов для повышения производительности
- Ограничение размера кэша
- Батчевая обработка для больших объемов данных

## 🚀 Развертывание

### Запуск модуля

```python
# В main.py или gRPC сервере
from modules.text_filtering import TextFilterManager

async def main():
    text_filter_manager = TextFilterManager()
    await text_filter_manager.initialize()
    
    # Использование в других модулях
    # (код интеграции)
```

### Интеграция с Text Processing Module

```python
# В TextProcessor
class TextProcessor:
    def __init__(self):
        self.text_filter_manager = TextFilterManager()
        await self.text_filter_manager.initialize()
    
    async def process_text(self, text: str):
        # Фильтруем текст перед обработкой
        filtered_result = await self.text_filter_manager.filter_text(text)
        
        if filtered_result["success"]:
            text = filtered_result["filtered_text"]
            # Продолжаем обработку
        else:
            # Обрабатываем ошибку фильтрации
            pass
```

### Интеграция с Audio Generation Module

```python
# В AudioGenerator
class AudioGenerator:
    def __init__(self):
        self.text_filter_manager = TextFilterManager()
        await self.text_filter_manager.initialize()
    
    async def generate_audio(self, text: str):
        # Очищаем текст перед генерацией аудио
        cleaned_result = await self.text_filter_manager.clean_text(text)
        
        if cleaned_result["success"]:
            text = cleaned_result["cleaned_text"]
            # Генерируем аудио
        else:
            # Обрабатываем ошибку очистки
            pass
```

## 🔄 Обновления

### Добавление новых фильтров

1. Создать новый провайдер в `providers/`
2. Добавить конфигурацию в `config.py`
3. Интегрировать в `TextFilterManager`
4. Написать тесты для нового функционала

### Модификация существующих фильтров

1. Обновить логику фильтрации
2. Обновить конфигурацию при необходимости
3. Обновить тесты
4. Проверить совместимость с существующим кодом

## 📞 Поддержка

### Отладка

```python
# Включение детального логирования
import logging
logging.getLogger("modules.text_filtering").setLevel(logging.DEBUG)

# Проверка статуса
stats = text_filter_manager.get_statistics()
print(json.dumps(stats, indent=2))
```

### Мониторинг производительности

```python
# Метрики фильтрации
stats = text_filter_manager.get_statistics()
print(f"Filter rate: {stats['filter_rate']:.2%}")
print(f"Average processing time: {stats['avg_processing_time_ms']:.1f}ms")
print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
```

---

**Версия документации**: 1.0  
**Дата обновления**: 2025-01-15  
**Совместимость**: Text Filtering Module v1.0
