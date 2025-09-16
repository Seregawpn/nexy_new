# Tray Controller Module - Руководство по интеграции

## 📋 Обзор

Tray Controller Module обеспечивает отображение иконки в меню-баре macOS и управление статусом приложения. Модуль полностью готов к интеграции с главной логикой проекта.

## 🎯 Основные возможности

- **3 режима работы**: SLEEPING, LISTENING, PROCESSING
- **Идеально круглые SVG иконки** (серый, синий, оранжевый)
- **Минималистичное меню** на английском языке
- **Интеграция с EventBus** для событий
- **Управление статусом** через ApplicationStateManager
- **macOS-совместимость** с rumps

## 🏗️ Архитектура модуля

```
tray_controller/
├── core/
│   ├── tray_controller.py    # Основной контроллер
│   ├── types.py             # Типы данных и генератор иконок
│   └── config.py            # Менеджер конфигурации
├── macos/
│   ├── tray_icon.py         # macOS иконки
│   └── menu_handler.py      # macOS меню
└── integration.py           # Интеграция с основным проектом
```

## 🔧 Интеграция с главной логикой

### 1. Импорт модуля

```python
from modules.tray_controller import TrayController, TrayStatus
from modules.tray_controller.integration import TrayControllerIntegration
```

### 2. Инициализация в main.py

```python
import asyncio
import threading
from modules.tray_controller import TrayController, TrayStatus

class MainApplication:
    def __init__(self):
        self.tray_controller = TrayController()
        self.tray_app = None
        
    async def initialize(self):
        """Инициализация приложения"""
        # Инициализируем tray controller
        await self.tray_controller.initialize()
        
    async def start(self):
        """Запуск приложения"""
        # Запускаем tray controller
        await self.tray_controller.start()
        
        # Получаем rumps app для главного потока
        self.tray_app = self.tray_controller.get_app()
        
        # Запускаем tray в отдельном потоке
        tray_thread = threading.Thread(target=self.tray_controller.run_app)
        tray_thread.daemon = True
        tray_thread.start()
        
    async def update_tray_status(self, new_status: TrayStatus):
        """Обновить статус в трее"""
        await self.tray_controller.update_status(new_status)
```

### 3. Интеграция с EventBus

```python
from integration.event_bus import EventBus

class TrayControllerIntegration:
    def __init__(self, tray_controller: TrayController, event_bus: EventBus):
        self.tray_controller = tray_controller
        self.event_bus = event_bus
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Настроить обработчики событий"""
        # Слушаем изменения режима приложения
        self.event_bus.subscribe("app.mode.changed", self._on_mode_changed)
        
        # Слушаем события микрофона
        self.event_bus.subscribe("microphone.started", self._on_microphone_started)
        self.event_bus.subscribe("microphone.stopped", self._on_microphone_stopped)
        
        # Слушаем события обработки
        self.event_bus.subscribe("processing.started", self._on_processing_started)
        self.event_bus.subscribe("processing.completed", self._on_processing_completed)
    
    async def _on_mode_changed(self, event_data):
        """Обработка изменения режима"""
        mode = event_data.get("mode")
        if mode == "sleeping":
            await self.tray_controller.update_status(TrayStatus.SLEEPING)
        elif mode == "listening":
            await self.tray_controller.update_status(TrayStatus.LISTENING)
        elif mode == "processing":
            await self.tray_controller.update_status(TrayStatus.PROCESSING)
    
    async def _on_microphone_started(self, event_data):
        """Микрофон активирован"""
        await self.tray_controller.update_status(TrayStatus.LISTENING)
    
    async def _on_microphone_stopped(self, event_data):
        """Микрофон деактивирован"""
        await self.tray_controller.update_status(TrayStatus.PROCESSING)
    
    async def _on_processing_started(self, event_data):
        """Начало обработки"""
        await self.tray_controller.update_status(TrayStatus.PROCESSING)
    
    async def _on_processing_completed(self, event_data):
        """Окончание обработки"""
        await self.tray_controller.update_status(TrayStatus.SLEEPING)
```

### 4. Интеграция с ApplicationStateManager

```python
from integration.application_state_manager import ApplicationStateManager

class TrayControllerIntegration:
    def __init__(self, tray_controller: TrayController, state_manager: ApplicationStateManager):
        self.tray_controller = tray_controller
        self.state_manager = state_manager
        self._setup_state_sync()
    
    def _setup_state_sync(self):
        """Синхронизация с состоянием приложения"""
        # Слушаем изменения состояния
        self.state_manager.add_state_listener("app_mode", self._on_app_mode_changed)
        self.state_manager.add_state_listener("is_processing", self._on_processing_changed)
    
    async def _on_app_mode_changed(self, old_value, new_value):
        """Обработка изменения режима приложения"""
        status_mapping = {
            "sleeping": TrayStatus.SLEEPING,
            "listening": TrayStatus.LISTENING,
            "processing": TrayStatus.PROCESSING
        }
        
        if new_value in status_mapping:
            await self.tray_controller.update_status(status_mapping[new_value])
    
    async def _on_processing_changed(self, old_value, new_value):
        """Обработка изменения состояния обработки"""
        if new_value:
            await self.tray_controller.update_status(TrayStatus.PROCESSING)
        else:
            # Возвращаемся к предыдущему режиму
            current_mode = self.state_manager.get_state("app_mode")
            if current_mode == "listening":
                await self.tray_controller.update_status(TrayStatus.LISTENING)
            else:
                await self.tray_controller.update_status(TrayStatus.SLEEPING)
```

## 🔄 Жизненный цикл интеграции

### 1. Инициализация
```python
# В main.py
tray_controller = TrayController()
await tray_controller.initialize()
```

### 2. Запуск
```python
# Запуск tray controller
await tray_controller.start()

# Получение rumps app
tray_app = tray_controller.get_app()

# Запуск в главном потоке (обязательно!)
tray_app.run()  # Или в отдельном потоке
```

### 3. Обновление статуса
```python
# Обновление статуса
await tray_controller.update_status(TrayStatus.LISTENING)
```

### 4. Остановка
```python
# Остановка tray controller
await tray_controller.stop()
```

## ⚙️ Конфигурация

### tray_config.yaml
```yaml
# Размер иконки
icon_size: 20

# Режим отладки
debug_mode: true

# Звуковые уведомления
enable_sound: true

# Цвета иконок
colors:
  sleeping: "#808080"    # Серый
  listening: "#007AFF"   # Синий
  processing: "#FF9500"  # Оранжевый
```

## 🎨 Визуальные состояния

| Режим | Цвет | Описание |
|-------|------|----------|
| SLEEPING | Серый (#808080) | Приложение в режиме ожидания |
| LISTENING | Синий (#007AFF) | Активное прослушивание микрофона |
| PROCESSING | Оранжевый (#FF9500) | Обработка команды или воспроизведение |

## 📱 Меню трея

```
Nexy AI Assistant
─────────────────
Status: [Current Status]
─────────────────
Quit
```

## 🔧 Требования

### Зависимости
```bash
pip install rumps
```

### macOS разрешения
- **Доступ к меню-бару**: Автоматически
- **Создание файлов**: Для временных иконок

## 🚨 Важные моменты

### 1. Главный поток
- **rumps.App.run()** должен вызываться в главном потоке
- Используйте `threading.Thread` для запуска в отдельном потоке

### 2. Асинхронность
- Все методы TrayController асинхронные
- Используйте `await` при вызове методов

### 3. Обработка ошибок
- Модуль имеет встроенную обработку ошибок
- Логирование через стандартный logging

### 4. Производительность
- SVG иконки генерируются динамически
- Минимальное потребление ресурсов

## 🧪 Тестирование

### Простой тест
```python
# Запуск теста отображения
python3 show_icon.py
```

### Unit тесты
```python
# Запуск тестов
python3 -m pytest tests/
```

## 📝 Пример полной интеграции

```python
import asyncio
import threading
from modules.tray_controller import TrayController, TrayStatus
from integration.event_bus import EventBus
from integration.application_state_manager import ApplicationStateManager

class MainApplication:
    def __init__(self):
        self.tray_controller = TrayController()
        self.event_bus = EventBus()
        self.state_manager = ApplicationStateManager()
        self.tray_integration = None
        
    async def initialize(self):
        """Инициализация всех компонентов"""
        # Инициализируем tray controller
        await self.tray_controller.initialize()
        
        # Создаем интеграцию
        self.tray_integration = TrayControllerIntegration(
            self.tray_controller,
            self.event_bus,
            self.state_manager
        )
        
    async def start(self):
        """Запуск приложения"""
        # Запускаем tray controller
        await self.tray_controller.start()
        
        # Запускаем tray в отдельном потоке
        tray_thread = threading.Thread(target=self.tray_controller.run_app)
        tray_thread.daemon = True
        tray_thread.start()
        
        # Устанавливаем начальный статус
        await self.tray_controller.update_status(TrayStatus.SLEEPING)
        
    async def stop(self):
        """Остановка приложения"""
        await self.tray_controller.stop()

# Запуск приложения
if __name__ == "__main__":
    app = MainApplication()
    asyncio.run(app.initialize())
    asyncio.run(app.start())
```

## ✅ Готовность к интеграции

Модуль полностью готов к интеграции с главной логикой проекта:

- ✅ **Все компоненты реализованы**
- ✅ **Тесты пройдены**
- ✅ **Конфигурация настроена**
- ✅ **Документация создана**
- ✅ **Примеры интеграции готовы**

**Модуль готов к использованию в production!** 🚀