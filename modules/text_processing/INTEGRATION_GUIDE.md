# 🚀 Инструкция по Интеграции Text Processing Module

## 📋 Обзор

Модуль `text_processing` реализует стриминговую обработку текста с использованием Google Live API. Поддерживает текст, JPEG изображения и Google Search.

## 🏗️ Архитектура

```
text_processing/
├── __init__.py                    # Основные экспорты
├── config.py                      # Конфигурация модуля
├── core/
│   └── text_processor.py          # Основной процессор (только стриминг)
└── providers/
    └── gemini_live_provider.py    # Live API провайдер
```

## 🔧 Быстрая Интеграция

### 1. Импорт Модуля
```python
from modules.text_processing import TextProcessor, TextProcessingConfig
```

### 2. Создание и Инициализация
```python
# Создание процессора
processor = TextProcessor()

# Инициализация (обязательно)
await processor.initialize()
```

### 3. Использование Стриминговых Методов

#### Стриминг Текста
```python
async for chunk in processor.process_text_streaming("Hello, how are you?"):
    print(chunk)  # Каждый чанк - часть ответа
```

#### Стриминг с JPEG Изображением
```python
# image_data должен быть в формате JPEG
async for chunk in processor.process_text_streaming_with_jpeg_image("What do you see?", image_data):
    print(chunk)
```

### 4. Очистка Ресурсов
```python
await processor.cleanup()
```

## ⚙️ Конфигурация

### Environment Variables
```env
# Live API настройки
GEMINI_API_KEY=your_api_key_here
GEMINI_LIVE_MODEL=gemini-live-2.5-flash-preview
GEMINI_LIVE_TEMPERATURE=0.7
GEMINI_LIVE_MAX_TOKENS=2048
GEMINI_LIVE_TOOLS=google_search

# Настройки изображений
IMAGE_FORMAT=jpeg
IMAGE_MIME_TYPE=image/jpeg
IMAGE_MAX_SIZE=10485760
STREAMING_CHUNK_SIZE=8192
```

### Кастомная Конфигурация
```python
config = {
    'gemini_live_model': 'gemini-live-2.5-flash-preview',
    'gemini_live_temperature': 0.7,
    'gemini_live_tools': ['google_search'],
    'image_max_size': 10 * 1024 * 1024
}

processor = TextProcessor(config)
```

## 📊 Мониторинг и Статус

### Проверка Статуса
```python
status = processor.get_status()
print(f"Инициализирован: {status['is_initialized']}")
print(f"Live API: {status['live_provider']['is_initialized']}")
```

### Получение Метрик
```python
metrics = processor.get_metrics()
print(f"Метрики: {metrics}")
```

### Проверка Провайдеров
```python
healthy = processor.get_healthy_providers()
failed = processor.get_failed_providers()
print(f"Здоровые: {len(healthy)}, Неисправные: {len(failed)}")
```

## 🔄 Полный Пример Использования

```python
import asyncio
from modules.text_processing import TextProcessor

async def main():
    # Создание и инициализация
    processor = TextProcessor()
    
    if not await processor.initialize():
        print("❌ Ошибка инициализации")
        return
    
    try:
        # Стриминг текста
        print("📝 Обработка текста:")
        async for chunk in processor.process_text_streaming("Explain artificial intelligence"):
            print(f"  {chunk.strip()}")
        
        # Стриминг с изображением (если есть)
        # image_data = load_jpeg_image("screenshot.jpg")
        # async for chunk in processor.process_text_streaming_with_jpeg_image("What do you see?", image_data):
        #     print(f"  {chunk.strip()}")
        
    finally:
        # Очистка ресурсов
        await processor.cleanup()

# Запуск
asyncio.run(main())
```

## 🚨 Обработка Ошибок

### Базовые Ошибки
```python
try:
    async for chunk in processor.process_text_streaming("Hello"):
        print(chunk)
except Exception as e:
    print(f"Ошибка обработки: {e}")
```

### Проверка Инициализации
```python
if not processor.is_initialized:
    print("❌ Процессор не инициализирован")
    return
```

### Валидация JPEG
```python
# Проверка формата JPEG
if not image_data.startswith(b'\xff\xd8\xff'):
    raise ValueError("Image must be in JPEG format")
```

## 🔧 Интеграция в gRPC

### Пример gRPC Интеграции
```python
async def process_text_request(request):
    processor = TextProcessor()
    await processor.initialize()
    
    try:
        if request.image_data:
            # С изображением
            async for chunk in processor.process_text_streaming_with_jpeg_image(
                request.text, 
                request.image_data
            ):
                yield create_response(chunk)
        else:
            # Только текст
            async for chunk in processor.process_text_streaming(request.text):
                yield create_response(chunk)
    finally:
        await processor.cleanup()
```

## 📝 Требования

### Зависимости
- `google-generativeai` - для Live API
- `asyncio` - для асинхронной работы
- `typing` - для типизации

### Системные Требования
- Python 3.9+
- Интернет соединение для Live API
- Валидный API ключ Google

## ⚡ Производительность

### Рекомендации
- **Инициализация:** ~2 секунды (однократно)
- **Стриминг:** 1-10 секунд на запрос
- **Память:** Стабильное использование
- **Сеть:** Требует стабильного соединения

### Оптимизация
- Переиспользуйте один экземпляр процессора
- Не создавайте новый процессор для каждого запроса
- Правильно очищайте ресурсы

## 🐛 Отладка

### Логирование
```python
import logging
logging.basicConfig(level=logging.INFO)
```

### Проверка Конфигурации
```python
config = TextProcessingConfig()
if not config.validate():
    print("❌ Неверная конфигурация")
```

### Тестирование Подключения
```python
status = processor.get_status()
if not status['live_provider']['is_initialized']:
    print("❌ Live API не инициализирован")
```

## 🎯 Лучшие Практики

1. **Всегда инициализируйте** процессор перед использованием
2. **Используйте try/finally** для гарантированной очистки
3. **Проверяйте статус** перед обработкой
4. **Валидируйте JPEG** перед отправкой
5. **Переиспользуйте экземпляры** для лучшей производительности
6. **Обрабатывайте ошибки** корректно

## 📞 Поддержка

При возникновении проблем:
1. Проверьте API ключ
2. Убедитесь в стабильности сети
3. Проверьте логи
4. Валидируйте конфигурацию

---

**Версия:** 1.0.0  
**Последнее обновление:** 26 сентября 2025  
**Статус:** ✅ Готов к Production
