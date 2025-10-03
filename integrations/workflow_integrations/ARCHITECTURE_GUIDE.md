# Архитектурное руководство: Правильная интеграция модулей

## Принципы модульной архитектуры

### ✅ ПРАВИЛЬНО: Интеграция использует модули

```python
# Интеграция НЕ содержит бизнес-логику
class StreamingWorkflowIntegration:
    def __init__(self, text_filter_manager=None, ...):
        self.text_filter_manager = text_filter_manager  # Делегируем модулю
    
    async def _sanitize_for_tts(self, text: str) -> str:
        # Используем модуль фильтрации
        if self.text_filter_manager:
            result = await self.text_filter_manager.clean_text(text)
            return result.get("cleaned_text", text)
        # Fallback только для критических случаев
        return simple_fallback(text)
```

### ❌ НЕПРАВИЛЬНО: Логика в интеграции

```python
# ПЛОХО: Интеграция содержит сложную бизнес-логику
class StreamingWorkflowIntegration:
    def _sanitize_for_tts(self, text: str) -> str:
        # Сложная логика прямо в интеграции
        t = unicodedata.normalize("NFKC", text)
        t = re.sub(r"[\u0000-\u001F\u007F]", "", t)
        # ... много кода ...
        return t
```

## Модули vs Интеграции

### Модули (server/modules/)
- **Назначение**: Содержат бизнес-логику и алгоритмы
- **Примеры**: `text_filtering`, `audio_generation`, `text_processing`
- **Ответственность**: Обработка данных, фильтрация, генерация

### Интеграции (server/integrations/)
- **Назначение**: Координируют модули и управляют потоком данных
- **Примеры**: `streaming_workflow_integration`, `memory_workflow_integration`
- **Ответственность**: Оркестрация, буферизация, стриминг

## Правильная инициализация

### 1. Создание модулей

```python
# Создаём и инициализируем модули
text_filter_config = TextFilteringConfig()
text_filter_manager = TextFilterManager(text_filter_config)
await text_filter_manager.initialize()

text_processor = TextProcessor()
await text_processor.initialize()

audio_processor = AudioProcessor()
await audio_processor.initialize()
```

### 2. Создание интеграции

```python
# Передаём модули в интеграцию
streaming_integration = StreamingWorkflowIntegration(
    text_processor=text_processor,
    audio_processor=audio_processor,
    memory_workflow=memory_workflow,
    text_filter_manager=text_filter_manager  # Ключевое добавление!
)
```

### 3. Делегирование в интеграции

```python
# Интеграция делегирует работу модулям
async def _sanitize_for_tts(self, text: str) -> str:
    if self.text_filter_manager:
        result = await self.text_filter_manager.clean_text(text)
        return result.get("cleaned_text", text)
    return fallback_clean(text)

async def _split_complete_sentences(self, text: str):
    if self.text_filter_manager:
        result = await self.text_filter_manager.split_sentences(text)
        return result.get("sentences", []), result.get("remainder", "")
    return simple_split(text)
```

## Преимущества правильной архитектуры

### 1. **Переиспользование**
- Модули можно использовать в разных интеграциях
- Логика фильтрации доступна везде

### 2. **Тестируемость**
- Модули тестируются отдельно
- Интеграции тестируются с моками модулей

### 3. **Поддерживаемость**
- Изменения в логике фильтрации в одном месте
- Интеграции остаются простыми

### 4. **Конфигурируемость**
- Модули настраиваются через конфигурацию
- Интеграции не знают о деталях реализации

## Текущие улучшения

### Что было исправлено:

1. **Логика фильтрации** перенесена из `streaming_workflow_integration` в `text_filtering` модуль
2. **Умная разбивка предложений** с учётом технических фраз (`main.py`, `12.10`, `192.168.1.1`)
3. **Подсчёт значимых слов** учитывает технические конструкции
4. **Делегирование** - интеграция использует модули вместо собственной логики

### Результат:

- ✅ Модули содержат бизнес-логику
- ✅ Интеграции координируют модули
- ✅ Код переиспользуется
- ✅ Архитектура соответствует принципам

## Примеры использования

См. `example_usage.py` для полного примера правильной инициализации и использования.
