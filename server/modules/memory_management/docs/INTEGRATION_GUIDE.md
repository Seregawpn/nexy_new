# 🧠 Memory Management Module - Инструкция по Интеграции

## 📋 Обзор

**Memory Management Module** управляет памятью пользователей Nexy AI Assistant, обеспечивая:
- Анализ диалогов для извлечения важной информации
- Формирование контекста памяти для LLM
- Фоновое обновление памяти после генерации ответов
- Полную совместимость с существующим TextProcessor

## 🏗️ Архитектура

```
Memory Management Module
├─ MemoryManager (координатор)
│  ├─ get_memory_context() - получение контекста для LLM
│  ├─ analyze_conversation() - анализ диалогов
│  └─ update_memory_background() - фоновое обновление
└─ MemoryAnalyzer (провайдер)
    └─ analyze_conversation() - анализ через Gemini API
```

## 🔧 Интеграция с TextProcessor

### Шаг 1: Импорт модуля

```python
# В text_processor.py заменить:
from memory_analyzer import MemoryAnalyzer

# На:
from modules.memory_management import MemoryManager
```

### Шаг 2: Инициализация

```python
class TextProcessor:
    def __init__(self):
        # Заменить:
        self.memory_analyzer = None
        
        # На:
        self.memory_manager = MemoryManager()
```

### Шаг 3: Установка DatabaseManager

```python
def set_database_manager(self, db_manager):
    # Заменить:
    self.db_manager = db_manager
    
    # На:
    self.db_manager = db_manager
    self.memory_manager.set_database_manager(db_manager)
```

### Шаг 4: Получение контекста памяти

```python
async def generate_response_stream(self, prompt, hardware_id=None, ...):
    # Заменить логику получения памяти (строки 254-282):
    memory_context = ""
    if hardware_id and self.db_manager:
        try:
            async with asyncio.timeout(2.0):
                memory_data = await asyncio.to_thread(
                    self.db_manager.get_user_memory, 
                    hardware_id
                )
                # ... формирование memory_context ...
        except Exception as e:
            # ... обработка ошибок ...
    
    # На:
    memory_context = await self.memory_manager.get_memory_context(hardware_id)
```

### Шаг 5: Фоновое обновление памяти

```python
# Заменить логику обновления памяти (строки 645-648):
if hardware_id and self.db_manager and self.memory_analyzer:
    asyncio.create_task(
        self._update_memory_background(hardware_id, user_content, full_response)
    )

# На:
if hardware_id and self.memory_manager.is_available():
    asyncio.create_task(
        self.memory_manager.update_memory_background(hardware_id, user_content, full_response)
    )
```

### Шаг 6: Удаление старого метода

```python
# Удалить метод _update_memory_background() из TextProcessor
# Он теперь находится в MemoryManager
```

## 🔄 Полный Пример Интеграции

### До (text_processor.py):

```python
class TextProcessor:
    def __init__(self):
        self.memory_analyzer = None
        self.db_manager = None
    
    def set_database_manager(self, db_manager):
        self.db_manager = db_manager
        
        # Инициализация MemoryAnalyzer
        gemini_api_key = Config.GEMINI_API_KEY
        if gemini_api_key:
            try:
                from memory_analyzer import MemoryAnalyzer
                self.memory_analyzer = MemoryAnalyzer(gemini_api_key)
            except ImportError:
                self.memory_analyzer = None
    
    async def generate_response_stream(self, prompt, hardware_id=None, ...):
        # Получение памяти (строки 254-282)
        memory_context = ""
        if hardware_id and self.db_manager:
            try:
                async with asyncio.timeout(2.0):
                    memory_data = await asyncio.to_thread(
                        self.db_manager.get_user_memory, 
                        hardware_id
                    )
                    # ... формирование memory_context ...
            except Exception as e:
                # ... обработка ошибок ...
        
        # ... генерация ответа ...
        
        # Фоновое обновление памяти (строки 645-648)
        if hardware_id and self.db_manager and self.memory_analyzer:
            asyncio.create_task(
                self._update_memory_background(hardware_id, user_content, full_response)
            )
    
    async def _update_memory_background(self, hardware_id, prompt, response):
        # ... логика обновления памяти ...
```

### После (text_processor.py):

```python
class TextProcessor:
    def __init__(self):
        from modules.memory_management import MemoryManager
        self.memory_manager = MemoryManager()
        self.db_manager = None
    
    def set_database_manager(self, db_manager):
        self.db_manager = db_manager
        self.memory_manager.set_database_manager(db_manager)
    
    async def generate_response_stream(self, prompt, hardware_id=None, ...):
        # Получение памяти
        memory_context = await self.memory_manager.get_memory_context(hardware_id)
        
        # ... генерация ответа ...
        
        # Фоновое обновление памяти
        if hardware_id and self.memory_manager.is_available():
            asyncio.create_task(
                self.memory_manager.update_memory_background(hardware_id, user_content, full_response)
            )
```

## ⚙️ Конфигурация

### Environment Variables:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
```

### Настройки в config.py:

```python
# Размеры памяти
MAX_SHORT_TERM_MEMORY_SIZE = 10240  # 10KB
MAX_LONG_TERM_MEMORY_SIZE = 10240   # 10KB

# Таймауты
MEMORY_TIMEOUT = 2.0  # секунды на получение памяти
ANALYSIS_TIMEOUT = 5.0  # секунды на анализ диалога

# Настройки модели
MEMORY_ANALYSIS_MODEL = "gemini-1.5-flash"
MEMORY_ANALYSIS_TEMPERATURE = 0.3
```

## 🧪 Тестирование

### Unit тесты:

```bash
cd server/modules/memory_management
python -m pytest tests/ -v
```

### Integration тесты:

```bash
# Тест с реальной БД
python tests/test_integration.py
```

## 🔍 Мониторинг и Логирование

### Логи:

```python
# Получение памяти
logger.info(f"🧠 Memory obtained for {hardware_id}: short-term ({len(short)} chars), long-term ({len(long)} chars)")

# Анализ диалога
logger.info(f"🧠 Memory analysis completed: short-term ({len(short)} chars), long-term ({len(long)} chars)")

# Обновление памяти
logger.info(f"✅ Memory for {hardware_id} updated: short-term ({len(short)} chars), long-term ({len(long)} chars)")
```

## 🚨 Обработка Ошибок

### Graceful Degradation:

- Если MemoryAnalyzer недоступен → работа без анализа памяти
- Если БД недоступна → работа без сохранения памяти
- Если API недоступен → пропуск анализа, продолжение работы

### Логирование ошибок:

```python
logger.error(f"❌ Error getting memory context for {hardware_id}: {e}")
logger.error(f"❌ Error analyzing conversation: {e}")
logger.error(f"❌ Error in background memory update for {hardware_id}: {e}")
```

## 📊 Производительность

### Метрики:

- Время получения памяти: < 2 секунд
- Время анализа диалога: < 5 секунд
- Размер краткосрочной памяти: ≤ 10KB
- Размер долгосрочной памяти: ≤ 10KB

### Оптимизации:

- Асинхронная обработка
- Таймауты для предотвращения блокировок
- Фоновое обновление памяти
- Кэширование результатов

## 🔒 Безопасность

### Ограничения:

- Максимальный размер памяти: 10KB для каждого типа
- Таймауты для предотвращения DoS
- Валидация входных данных
- Безопасное хранение API ключей

## 🚀 Готовность к Продакшену

### ✅ Завершено:

- [x] Полная совместимость с TextProcessor
- [x] Асинхронная обработка
- [x] Обработка ошибок
- [x] Логирование и мониторинг
- [x] Конфигурация
- [x] Тесты

### 📋 Checklist для интеграции:

- [ ] Импорт MemoryManager в TextProcessor
- [ ] Замена инициализации memory_analyzer
- [ ] Замена логики получения памяти
- [ ] Замена логики обновления памяти
- [ ] Удаление старого метода _update_memory_background
- [ ] Тестирование интеграции
- [ ] Проверка логов
- [ ] Валидация производительности

---

**Memory Management Module готов к интеграции и обеспечивает полную совместимость с существующей архитектурой Nexy AI Assistant!** 🎯
