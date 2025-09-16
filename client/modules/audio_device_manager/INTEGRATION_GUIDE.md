# 🎧 Audio Device Manager - Руководство по интеграции

## 📋 Статус готовности

✅ **СИСТЕМА ГОТОВА К ВНЕДРЕНИЮ**
- ✅ Логика работает корректно
- ✅ Автоматическое переключение функционирует
- ✅ Приоритизация устройств настроена
- ✅ Мониторинг в реальном времени работает
- ✅ API протестировано

## 🔌 Точки интеграции с проектом

### 1. **Главный файл** (`client/main.py`)

```python
from audio_device_manager import AudioDeviceManager

class MainApplication:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def start(self):
        # Запуск аудио менеджера
        await self.audio_manager.start()
        
        # Регистрация callbacks
        self.audio_manager.set_device_changed_callback(self.on_audio_changed)
        self.audio_manager.set_device_switched_callback(self.on_audio_switched)
        
    async def on_audio_changed(self, change):
        """Обработка изменений аудио устройств"""
        for device in change.added:
            print(f"🎧 Подключено: {device.name}")
        for device in change.removed:
            print(f"🔌 Отключено: {device.name}")
```

### 2. **State Management** (основной StateManager в `main.py`)

```python
from audio_device_manager import AudioDeviceManager

class SimpleStateManager:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def start(self):
        await self.audio_manager.start()
        
    def get_current_audio_device(self):
        return self.audio_manager.current_device
```

### 3. **Module Coordinator** (`client/integration/core/module_coordinator.py`)

```python
from audio_device_manager import AudioDeviceManager

class ModuleCoordinator:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def initialize_modules(self):
        await self.audio_manager.start()
        
    def get_system_status(self):
        return {
            'audio_device': self.audio_manager.current_device,
            'available_devices': len(self.audio_manager.get_available_devices()),
            'audio_metrics': self.audio_manager.get_metrics()
        }
```

## 🚀 Быстрый старт

### Базовое использование

```python
import asyncio
from audio_device_manager import AudioDeviceManager

async def main():
    # Создание и запуск
    manager = AudioDeviceManager()
    await manager.start()
    
    # Получение текущего устройства
    device = await manager.get_current_device()
    print(f"Активное: {device.name}")
    
    # Остановка
    await manager.stop()

asyncio.run(main())
```

## ⚙️ API методы

### Управление

```python
await manager.start()                    # Запуск
await manager.stop()                     # Остановка
await manager.restart()                  # Перезапуск
```

### Устройства

```python
devices = await manager.get_available_devices()  # Все устройства
current = await manager.get_current_device()     # Текущее
best = await manager.get_best_device()           # Лучшее по приоритету
```

### Переключение

```python
await manager.switch_to_device(device)           # На конкретное устройство
await manager.switch_to_device_type(DeviceType.OUTPUT)  # По типу
```

### Метрики

```python
metrics = manager.get_metrics()
print(f"Устройств: {metrics.total_devices}")
print(f"Переключений: {metrics.total_switches}")
```

## 📊 Callbacks

```python
def on_device_changed(change):
    """При изменении устройств"""
    print(f"Добавлено: {len(change.added)}")
    print(f"Удалено: {len(change.removed)}")

def on_device_switched(from_device, to_device):
    """При переключении"""
    print(f"Переключено на: {to_device.name}")

# Регистрация
manager.set_device_changed_callback(on_device_changed)
manager.set_device_switched_callback(on_device_switched)
```

## 🔧 Конфигурация

```python
from audio_device_manager.core.types import AudioDeviceManagerConfig

config = AudioDeviceManagerConfig(
    auto_switch_enabled=True,        # Автопереключение
    monitoring_interval=1.0,         # Интервал мониторинга
    switch_delay=0.5,               # Задержка переключения
    device_priorities={             # Приоритеты
        'bluetooth_headphones': 1,
        'usb_headphones': 2,
        'builtin_speakers': 4
    }
)

manager = AudioDeviceManager(config)
```

## 🎯 Приоритеты устройств

```python
# Автоматическая приоритизация:
# 1 = HIGHEST  - Bluetooth наушники (AirPods)
# 2 = HIGH     - USB наушники, гарнитуры
# 3 = MEDIUM   - Беспроводные устройства
# 4 = NORMAL   - Внешние колонки
# 6 = LOWEST   - Встроенные динамики
```

## 🔗 Интеграция с другими модулями

### Audio Player

```python
class AudioPlayer:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def play(self, audio_data):
        device = await self.audio_manager.get_current_device()
        print(f"Воспроизведение на: {device.name}")
```

### Voice Recognition

```python
class SpeechRecognizer:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def listen(self):
        device = await self.audio_manager.get_current_device()
        print(f"Прослушивание через: {device.name}")
```

### Interrupt Management

```python
class InterruptManager:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def interrupt_audio(self):
        device = await self.audio_manager.get_current_device()
        print(f"Прерывание на: {device.name}")
```

## ⚠️ Требования

### 1. macOS зависимости

```bash
# Установка SwitchAudioSource
brew install switchaudio-osx

# Проверка
switchaudio -a
```

### 2. Python пакеты

```txt
# requirements.txt
PyObjC>=8.0
asyncio
```

### 3. Права доступа

```xml
<!-- entitlements.plist -->
<key>com.apple.security.device.audio-input</key>
<true/>
<key>com.apple.security.device.audio-output</key>
<true/>
```

## 🐛 Обработка ошибок

```python
def on_error(error, context):
    print(f"Ошибка в {context}: {error}")

manager.set_error_callback(on_error)

# Или try/catch
try:
    await manager.start()
except Exception as e:
    print(f"Ошибка запуска: {e}")
```

## ⚠️ Типичные ошибки и антипаттерны

### ❌ НЕ ДЕЛАЙТЕ ТАК

#### 1. **Неправильная инициализация**

```python
# ❌ ПЛОХО - создание в неправильном месте
class MyApp:
    def __init__(self):
        self.audio_manager = None  # Не инициализирован
        
    async def start(self):
        # Создание в async методе - плохо
        self.audio_manager = AudioDeviceManager()
        await self.audio_manager.start()
```

```python
# ✅ ХОРОШО - правильная инициализация
class MyApp:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()  # Создаем сразу
        
    async def start(self):
        await self.audio_manager.start()  # Только запускаем
```

#### 2. **Игнорирование async/await**

```python
# ❌ ПЛОХО - игнорирование async
def start_audio():
    manager = AudioDeviceManager()
    manager.start()  # Ошибка! start() - async метод
    return manager
```

```python
# ✅ ХОРОШО - правильное использование async
async def start_audio():
    manager = AudioDeviceManager()
    await manager.start()  # Правильно с await
    return manager
```

#### 3. **Неправильная обработка callbacks**

```python
# ❌ ПЛОХО - неправильные названия методов
manager.set_device_change_callback(callback)  # Неправильно!
manager.set_device_switch_callback(callback)  # Неправильно!
```

```python
# ✅ ХОРОШО - правильные названия методов
manager.set_device_changed_callback(callback)  # Правильно!
manager.set_device_switched_callback(callback)  # Правильно!
```

#### 4. **Отсутствие обработки ошибок**

```python
# ❌ ПЛОХО - нет обработки ошибок
async def play_audio():
    manager = AudioDeviceManager()
    await manager.start()
    device = await manager.get_current_device()
    # Что если device = None?
    print(device.name)  # AttributeError!
```

```python
# ✅ ХОРОШО - с обработкой ошибок
async def play_audio():
    try:
        manager = AudioDeviceManager()
        await manager.start()
        device = await manager.get_current_device()
        
        if device:
            print(f"Активное устройство: {device.name}")
        else:
            print("Устройство не найдено")
            
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        await manager.stop()
```

#### 5. **Неправильное управление жизненным циклом**

```python
# ❌ ПЛОХО - забыли остановить менеджер
async def process_audio():
    manager = AudioDeviceManager()
    await manager.start()
    # Забыли await manager.stop() - утечка ресурсов!
```

```python
# ✅ ХОРОШО - правильное управление ресурсами
async def process_audio():
    manager = AudioDeviceManager()
    try:
        await manager.start()
        # Ваша логика здесь
    finally:
        await manager.stop()  # Всегда останавливаем
```

#### 6. **Неправильная работа с устройствами**

```python
# ❌ ПЛОХО - неправильная проверка типов
device = await manager.get_current_device()
if device.type == "output":  # Ошибка! device.type - enum
    print("Устройство вывода")
```

```python
# ✅ ХОРОШО - правильная работа с enum
device = await manager.get_current_device()
if device.type == DeviceType.OUTPUT:  # Правильно!
    print("Устройство вывода")
```

#### 7. **Синхронные вызовы в async контексте**

```python
# ❌ ПЛОХО - синхронный вызов async метода
def get_devices():
    manager = AudioDeviceManager()
    devices = manager.get_available_devices()  # Ошибка! Нужен await
    return devices
```

```python
# ✅ ХОРОШО - правильный async вызов
async def get_devices():
    manager = AudioDeviceManager()
    devices = await manager.get_available_devices()  # Правильно!
    return devices
```

#### 8. **Неправильная конфигурация**

```python
# ❌ ПЛОХО - неправильные типы в конфигурации
config = {
    'auto_switch_enabled': "true",  # Должно быть bool
    'monitoring_interval': "1.0",   # Должно быть float
    'device_priorities': "default"  # Должно быть dict
}
manager = AudioDeviceManager(config)
```

```python
# ✅ ХОРОШО - правильная конфигурация
from audio_device_manager.core.types import AudioDeviceManagerConfig

config = AudioDeviceManagerConfig(
    auto_switch_enabled=True,        # bool
    monitoring_interval=1.0,         # float
    device_priorities={              # dict
        'bluetooth_headphones': 1,
        'usb_headphones': 2
    }
)
manager = AudioDeviceManager(config)
```

### 🚨 Критические ошибки

#### 1. **Множественные экземпляры менеджера**

```python
# ❌ КРИТИЧЕСКАЯ ОШИБКА - несколько менеджеров
class App:
    def __init__(self):
        self.audio_manager1 = AudioDeviceManager()  # Плохо!
        self.audio_manager2 = AudioDeviceManager()  # Плохо!
```

```python
# ✅ ПРАВИЛЬНО - один менеджер (Singleton pattern)
class App:
    _audio_manager = None
    
    @classmethod
    def get_audio_manager(cls):
        if cls._audio_manager is None:
            cls._audio_manager = AudioDeviceManager()
        return cls._audio_manager
```

#### 2. **Блокирующие операции в main thread**

```python
# ❌ КРИТИЧЕСКАЯ ОШИБКА - блокировка UI
def on_button_click():
    manager = AudioDeviceManager()
    asyncio.run(manager.start())  # Блокирует UI!
```

```python
# ✅ ПРАВИЛЬНО - неблокирующий вызов
async def on_button_click():
    manager = AudioDeviceManager()
    await manager.start()  # Не блокирует
```

#### 3. **Отсутствие проверки зависимостей**

```python
# ❌ КРИТИЧЕСКАЯ ОШИБКА - нет проверки SwitchAudio
async def start_audio():
    manager = AudioDeviceManager()
    await manager.start()  # Упадет если SwitchAudio не установлен
```

```python
# ✅ ПРАВИЛЬНО - проверка зависимостей
import subprocess

def check_switchaudio():
    try:
        subprocess.run(['switchaudio', '-a'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

async def start_audio():
    if not check_switchaudio():
        raise RuntimeError("SwitchAudio не установлен. Выполните: brew install switchaudio-osx")
    
    manager = AudioDeviceManager()
    await manager.start()
```

### 🔧 Лучшие практики

#### 1. **Правильная инициализация**

```python
class AudioService:
    def __init__(self):
        self.manager = AudioDeviceManager()
        self.is_running = False
        
    async def start(self):
        if not self.is_running:
            await self.manager.start()
            self.is_running = True
            
    async def stop(self):
        if self.is_running:
            await self.manager.stop()
            self.is_running = False
```

#### 2. **Обработка всех типов ошибок**

```python
async def safe_audio_operation():
    manager = AudioDeviceManager()
    
    try:
        await manager.start()
        
        # Основная логика
        device = await manager.get_current_device()
        if device:
            print(f"Активное устройство: {device.name}")
        else:
            print("Устройство не найдено")
            
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
    except RuntimeError as e:
        print(f"Ошибка выполнения: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
    finally:
        try:
            await manager.stop()
        except Exception as e:
            print(f"Ошибка при остановке: {e}")
```

#### 3. **Правильная работа с callbacks**

```python
class AudioController:
    def __init__(self):
        self.manager = AudioDeviceManager()
        self.setup_callbacks()
        
    def setup_callbacks(self):
        self.manager.set_device_changed_callback(self.on_device_changed)
        self.manager.set_device_switched_callback(self.on_device_switched)
        self.manager.set_error_callback(self.on_error)
        
    def on_device_changed(self, change):
        # Обработка изменений устройств
        pass
        
    def on_device_switched(self, from_device, to_device):
        # Обработка переключений
        pass
        
    def on_error(self, error):
        # Обработка ошибок
        pass
```

### 📋 Чеклист проверки

Перед интеграцией убедитесь:

- [ ] ✅ Используете `await` с async методами
- [ ] ✅ Правильные названия callback методов
- [ ] ✅ Обрабатываете все возможные ошибки
- [ ] ✅ Останавливаете менеджер в `finally` блоке
- [ ] ✅ Проверяете зависимости (SwitchAudio)
- [ ] ✅ Используете правильные типы в конфигурации
- [ ] ✅ Не создаете множественные экземпляры
- [ ] ✅ Проверяете `None` значения перед использованием
- [ ] ✅ Используете enum для сравнения типов устройств

## 📈 Мониторинг

```python
# Метрики в реальном времени
def on_metrics_updated(metrics):
    print(f"Устройств: {metrics.total_devices}")
    print(f"Переключений: {metrics.total_switches}")
    print(f"Успешных: {metrics.successful_switches}")

manager.set_metrics_callback(on_metrics_updated)
```

## 💡 Примеры использования

### Полная интеграция

```python
class MyApp:
    def __init__(self):
        self.audio_manager = AudioDeviceManager()
        
    async def start(self):
        # Запуск аудио менеджера
        await self.audio_manager.start()
        
        # Регистрация всех callbacks
        self.audio_manager.set_device_changed_callback(self.on_devices_changed)
        self.audio_manager.set_device_switched_callback(self.on_device_switched)
        self.audio_manager.set_error_callback(self.on_error)
        self.audio_manager.set_metrics_callback(self.on_metrics)
        
    async def on_devices_changed(self, change):
        # Обработка изменений устройств
        if change.added:
            for device in change.added:
                if device.channels == 2:  # Наушники
                    print(f"🎧 Наушники подключены: {device.name}")
                    
    async def on_device_switched(self, from_device, to_device):
        # Уведомление пользователя о переключении
        print(f"🔄 Аудио переключено на: {to_device.name}")
        
    def on_error(self, error, context):
        # Логирование ошибок
        print(f"❌ Ошибка аудио ({context}): {error}")
        
    def on_metrics(self, metrics):
        # Мониторинг состояния
        if metrics.total_switches > 0:
            success_rate = metrics.successful_switches / metrics.total_switches
            print(f"📊 Успешность переключений: {success_rate:.2%}")
```

## ✅ Готовность к продакшену

**МОДУЛЬ ГОТОВ К ВНЕДРЕНИЮ!**

- ✅ Логика протестирована в реальном времени
- ✅ Автоматическое переключение работает идеально
- ✅ Приоритизация устройств настроена
- ✅ API стабильно и готово
- ✅ Обработка ошибок реализована
- ✅ Документация создана

## 🚀 Следующие шаги

1. **Интегрировать в main.py** - добавить инициализацию
2. **Подключить к основному StateManager** - для мониторинга состояния
3. **Связать с audio_player** - для корректного воспроизведения
4. **Настроить в module_coordinator** - для общего управления
5. **Добавить в упаковку** - включить в macOS bundle

---

**Система готова к использованию в продакшене!** 🎉