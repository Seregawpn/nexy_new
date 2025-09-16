# Руководство по интеграции модуля screenshot_capture

## 📋 Обзор

Данное руководство описывает правильную интеграцию модуля `screenshot_capture` с остальными компонентами системы Nexy. Модуль обеспечивает захват скриншотов в формате JPEG с различными уровнями качества.

## 🏗️ Архитектура интеграции

### Основные компоненты
```
screenshot_capture/
├── ScreenshotCapture          # Основной класс захватчика
├── ScreenshotConfig          # Конфигурация захвата
├── ScreenshotResult          # Результат захвата
├── ScreenshotData            # Данные скриншота (JPEG)
└── CoreGraphicsBridge        # macOS bridge для захвата
```

### Внешние зависимости
- `mode_management` - для активации захвата в определенных режимах
- `grpc_client` - для отправки скриншотов на сервер
- `state_manager` - для отслеживания состояния захвата
- `text_processor` - для обработки скриншотов с текстом

## 🔗 Интеграция с модулями

### 1. Интеграция с mode_management

#### ✅ Правильная интеграция:
```python
from mode_management import ModeController, AppMode, ListeningMode
from screenshot_capture import ScreenshotCapture, ScreenshotConfig, ScreenshotFormat

# Создание компонентов
screenshot_capture = ScreenshotCapture()
listening_mode = ListeningMode(speech_recognizer, audio_device_manager)
controller = ModeController()

# Захват скриншота при активации режима прослушивания
async def on_listening_activated():
    # Захватываем скриншот при начале прослушивания
    result = await screenshot_capture.capture_screenshot()
    if result.success:
        # Сохраняем скриншот для контекста
        await save_screenshot_context(result.data)

controller.register_mode_change_callback(on_listening_activated)
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - захват без учета режима
screenshot_capture.capture_screenshot()  # Может конфликтовать с другими процессами
```

#### ⚠️ Потенциальные проблемы:
- **Проблема**: Захват скриншотов в неподходящих режимах
- **Решение**: Привязывайте захват к конкретным режимам (LISTENING, PROCESSING)
- **Проблема**: Блокировка UI при захвате
- **Решение**: Используйте асинхронные вызовы `await capture_screenshot()`

### 2. Интеграция с grpc_client

#### ✅ Правильная интеграция:
```python
from screenshot_capture import ScreenshotCapture, ScreenshotData
from grpc_client import GrpcClient

# Создание компонентов
screenshot_capture = ScreenshotCapture()
grpc_client = GrpcClient()

# Отправка скриншота на сервер
async def send_screenshot_with_context():
    # Захватываем скриншот
    result = await screenshot_capture.capture_screenshot()
    
    if result.success:
        # Конвертируем в формат для gRPC
        screenshot_dict = result.data.to_dict()
        
        # Отправляем на сервер
        response = await grpc_client.process_command(
            "analyze_screenshot", 
            {"screenshot": screenshot_dict}
        )
        return response
    else:
        logger.error(f"Ошибка захвата: {result.error}")
        return None
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - прямая отправка без обработки
await grpc_client.process_command("screenshot", result.data)  # Неправильный формат
```

#### ⚠️ Потенциальные проблемы:
- **Проблема**: Отправка больших скриншотов блокирует сеть
- **Решение**: Используйте сжатие и ограничения размера
- **Проблема**: Неправильный формат данных
- **Решение**: Используйте `to_dict()` для конвертации

### 3. Интеграция с основным приложением

#### ✅ Правильная интеграция:
```python
from screenshot_capture import ScreenshotCapture

# Создание компонентов
screenshot_capture = ScreenshotCapture()

# Синхронизация состояния
async def capture_and_update_state():
    # Захватываем скриншот
    result = await screenshot_capture.capture_screenshot()
    
    if result.success:
        # Обновляем состояние
        await state_manager.set_screenshot_available(True)
        await state_manager.set_last_screenshot_time(time.time())
        await state_manager.set_screenshot_size(result.data.size_bytes)
    else:
        await state_manager.set_screenshot_available(False)
        await state_manager.set_screenshot_error(result.error)
```

#### ❌ Неправильная интеграция:
```python
# НЕ ДЕЛАЙТЕ ТАК - захват без обновления состояния
result = await screenshot_capture.capture_screenshot()  # Состояние не синхронизировано
```

### 4. Интеграция с text_processor

#### ✅ Правильная интеграция:
```python
from screenshot_capture import ScreenshotCapture, ScreenshotData
from text_processor import TextProcessor

# Создание компонентов
screenshot_capture = ScreenshotCapture()
text_processor = TextProcessor()

# Обработка скриншота с текстом
async def process_screenshot_with_text():
    # Захватываем скриншот
    result = await screenshot_capture.capture_screenshot()
    
    if result.success:
        # Конвертируем в формат для text_processor
        screenshot_dict = result.data.to_dict()
        
        # Обрабатываем текст на скриншоте
        text_result = await text_processor.process_image(screenshot_dict)
        
        return {
            "screenshot": result.data,
            "extracted_text": text_result
        }
```

## 🔄 Жизненный цикл интеграции

### 1. Инициализация
```python
async def initialize_screenshot_capture():
    # Создание захватчика с конфигурацией
    config = ScreenshotConfig(
        format=ScreenshotFormat.JPEG,
        quality=ScreenshotQuality.MEDIUM,
        max_width=1280,
        max_height=720,
        timeout=5.0
    )
    
    screenshot_capture = ScreenshotCapture(config)
    
    # Проверяем доступность
    can_capture = await screenshot_capture.test_capture()
    if not can_capture:
        raise ScreenshotPermissionError("Нет прав доступа к экрану")
    
    return screenshot_capture
```

### 2. Конфигурация по режимам
```python
def get_screenshot_config_for_mode(mode: AppMode) -> ScreenshotConfig:
    """Возвращает конфигурацию захвата для конкретного режима"""
    
    if mode == AppMode.LISTENING:
        # Быстрый захват для прослушивания
        return ScreenshotConfig(
            format=ScreenshotFormat.JPEG,
            quality=ScreenshotQuality.LOW,
            max_width=640,
            max_height=480,
            timeout=2.0
        )
    elif mode == AppMode.PROCESSING:
        # Качественный захват для обработки
        return ScreenshotConfig(
            format=ScreenshotFormat.JPEG,
            quality=ScreenshotQuality.HIGH,
            max_width=1280,
            max_height=720,
            timeout=5.0
        )
    else:
        # Стандартная конфигурация
        return ScreenshotConfig()
```

### 3. Обработка событий
```python
async def handle_screenshot_request(event_data):
    """Обрабатывает запрос на захват скриншота"""
    
    try:
        # Получаем конфигурацию
        config = get_screenshot_config_for_mode(event_data.get('mode'))
        
        # Захватываем скриншот
        result = await screenshot_capture.capture_screenshot(config)
        
        if result.success:
            # Обрабатываем успешный результат
            await process_successful_capture(result.data, event_data)
        else:
            # Обрабатываем ошибку
            await handle_capture_error(result.error, event_data)
            
    except Exception as e:
        logger.error(f"Ошибка обработки запроса скриншота: {e}")
        await handle_capture_error(str(e), event_data)
```

## 📊 Формат данных

### ScreenshotData структура
```python
@dataclass
class ScreenshotData:
    base64_data: str          # Base64 кодированные данные JPEG
    format: ScreenshotFormat  # JPEG
    width: int               # Ширина в пикселях
    height: int              # Высота в пикселях
    size_bytes: int          # Размер в байтах
    mime_type: str           # "image/jpeg"
    metadata: Dict[str, Any] # Дополнительные метаданные
```

### Конвертация для gRPC
```python
def prepare_screenshot_for_grpc(screenshot_data: ScreenshotData) -> Dict[str, Any]:
    """Подготавливает данные скриншота для отправки через gRPC"""
    
    return {
        "mime_type": screenshot_data.mime_type,
        "data": screenshot_data.base64_data,
        "width": screenshot_data.width,
        "height": screenshot_data.height,
        "size_bytes": screenshot_data.size_bytes,
        "format": screenshot_data.format.value,
        "metadata": screenshot_data.metadata,
        "timestamp": time.time(),
        "source": "screenshot_capture"
    }
```

### Конвертация для text_processor
```python
def prepare_screenshot_for_text_processing(screenshot_data: ScreenshotData) -> Dict[str, Any]:
    """Подготавливает данные скриншота для обработки текста"""
    
    return {
        "mime_type": screenshot_data.mime_type,
        "data": screenshot_data.base64_data,
        "raw_bytes": None,  # Не используется для JPEG
        "width": screenshot_data.width,
        "height": screenshot_data.height,
        "size_bytes": screenshot_data.size_bytes,
        "format": screenshot_data.format.value,
        "metadata": screenshot_data.metadata
    }
```

## ⚠️ Частые проблемы и решения

### 1. Проблема: "No module named 'CoreGraphics'"
**Симптомы**: Ошибка при захвате областей экрана
**Причины**: 
- Отсутствуют macOS зависимости
- Неправильная настройка окружения

**Решение**:
```python
# Используйте только полный экран для базового функционала
config = ScreenshotConfig(region=ScreenshotRegion.FULL_SCREEN)
result = await screenshot_capture.capture_screenshot(config)
```

### 2. Проблема: "ScreenshotPermissionError"
**Симптомы**: Ошибка прав доступа к экрану
**Причины**: 
- Не предоставлены разрешения в системных настройках
- Приложение не подписано правильно

**Решение**:
```python
# Проверяйте права доступа перед захватом
can_capture = await screenshot_capture.test_capture()
if not can_capture:
    # Покажите пользователю инструкции по настройке разрешений
    show_permission_instructions()
    return
```

### 3. Проблема: Большие размеры файлов
**Симптомы**: Медленная отправка, превышение лимитов
**Причины**: 
- Слишком высокое качество
- Большое разрешение экрана

**Решение**:
```python
# Используйте оптимизированную конфигурацию
config = ScreenshotConfig(
    quality=ScreenshotQuality.MEDIUM,  # Вместо HIGH/MAXIMUM
    max_width=1280,                    # Ограничьте размер
    max_height=720,
    compress=True
)
```

### 4. Проблема: Таймауты захвата
**Симптомы**: "ScreenshotTimeoutError"
**Причины**: 
- Слишком короткий таймаут
- Системная нагрузка

**Решение**:
```python
# Увеличьте таймаут для сложных случаев
config = ScreenshotConfig(timeout=10.0)  # Вместо 5.0
result = await screenshot_capture.capture_screenshot(config)
```

### 5. Проблема: Конфликт с другими приложениями
**Симптомы**: Захват не работает при активных других приложениях
**Причины**: 
- Конфликт прав доступа
- Блокировка экрана

**Решение**:
```python
# Проверяйте состояние экрана перед захватом
if not is_screen_locked() and not is_other_app_active():
    result = await screenshot_capture.capture_screenshot()
```

## 🧪 Тестирование интеграции

### 1. Unit тесты
```python
async def test_screenshot_integration():
    # Тестирование интеграции с mode_management
    controller = ModeController()
    screenshot_capture = ScreenshotCapture()
    
    # Тест захвата при смене режима
    await controller.switch_mode(AppMode.LISTENING)
    result = await screenshot_capture.capture_screenshot()
    assert result.success == True
```

### 2. Интеграционные тесты
```python
async def test_full_screenshot_workflow():
    # Тест полного workflow
    screenshot_capture = ScreenshotCapture()
    grpc_client = GrpcClient()
    
    # Захват и отправка
    result = await screenshot_capture.capture_screenshot()
    if result.success:
        screenshot_dict = result.data.to_dict()
        response = await grpc_client.process_command("screenshot", screenshot_dict)
        assert response is not None
```

### 3. Нагрузочные тесты
```python
async def test_concurrent_screenshots():
    # Тестирование параллельных захватов
    tasks = []
    for i in range(10):
        task = asyncio.create_task(screenshot_capture.capture_screenshot())
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    # Проверяем результаты
```

## 📊 Мониторинг и отладка

### 1. Логирование
```python
import logging

# Настройка логирования для screenshot_capture
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('screenshot_capture')

# Логирование захватов
async def log_screenshot_capture(result):
    if result.success:
        logger.info(f"Скриншот захвачен: {result.data.width}x{result.data.height}, "
                   f"размер: {result.data.size_bytes} байт")
    else:
        logger.error(f"Ошибка захвата: {result.error}")
```

### 2. Метрики
```python
# Получение метрик захвата
def get_screenshot_metrics(screenshot_capture):
    status = screenshot_capture.get_status()
    return {
        "initialized": status["initialized"],
        "bridge_available": status["bridge_available"],
        "config": status["config"]
    }
```

### 3. Статус системы
```python
# Проверка готовности системы
async def check_screenshot_readiness():
    screenshot_capture = ScreenshotCapture()
    
    # Проверяем инициализацию
    if not screenshot_capture._initialized:
        return False, "ScreenshotCapture не инициализирован"
    
    # Проверяем права доступа
    can_capture = await screenshot_capture.test_capture()
    if not can_capture:
        return False, "Нет прав доступа к экрану"
    
    return True, "Система готова к захвату скриншотов"
```

## 🔧 Конфигурация

### 1. Настройка качества
```python
# Для быстрого захвата (режим прослушивания)
fast_config = ScreenshotConfig(
    format=ScreenshotFormat.JPEG,
    quality=ScreenshotQuality.LOW,
    max_width=640,
    max_height=480,
    timeout=2.0
)

# Для качественного захвата (режим обработки)
quality_config = ScreenshotConfig(
    format=ScreenshotFormat.JPEG,
    quality=ScreenshotQuality.HIGH,
    max_width=1280,
    max_height=720,
    timeout=5.0
)
```

### 2. Настройка таймаутов
```python
# Адаптивные таймауты
def get_timeout_for_mode(mode: AppMode) -> float:
    timeouts = {
        AppMode.LISTENING: 2.0,    # Быстрый захват
        AppMode.PROCESSING: 5.0,   # Стандартный захват
        AppMode.SLEEPING: 10.0     # Медленный захват
    }
    return timeouts.get(mode, 5.0)
```

## 📝 Чек-лист интеграции

### ✅ Перед началом:
- [ ] Изучить архитектуру `screenshot_capture`
- [ ] Определить необходимые разрешения
- [ ] Спланировать интеграцию с режимами
- [ ] Настроить логирование и мониторинг

### ✅ При интеграции:
- [ ] Использовать асинхронные вызовы
- [ ] Проверять права доступа перед захватом
- [ ] Конфигурировать качество по режимам
- [ ] Обрабатывать ошибки захвата

### ✅ После интеграции:
- [ ] Протестировать все сценарии захвата
- [ ] Проверить производительность
- [ ] Настроить мониторинг
- [ ] Документировать изменения

## 🚨 Критические моменты

1. **Всегда проверяйте права доступа** - `test_capture()` перед основным захватом
2. **Используйте асинхронные вызовы** - `await capture_screenshot()`
3. **Обрабатывайте ошибки** - проверяйте `result.success`
4. **Оптимизируйте размеры** - используйте `max_width/max_height`
5. **Мониторьте производительность** - логируйте время захвата

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи `screenshot_capture`
2. Убедитесь в наличии прав доступа к экрану
3. Проверьте конфигурацию захвата
4. Протестируйте базовый функционал
5. Обратитесь к команде разработки

---

**Версия документа**: 1.0  
**Дата обновления**: 2025-09-13  
**Автор**: Nexy Team
