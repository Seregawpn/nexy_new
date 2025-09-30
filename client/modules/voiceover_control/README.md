# VoiceOver Control Module

## 📋 Обзор

Модуль `voiceover_control` обеспечивает управление VoiceOver на macOS для временного отключения речи во время работы приложения Nexy. Это критически важно для пользователей с нарушениями зрения, которые полагаются на VoiceOver для навигации.

## 🎯 Назначение

- **Ducking**: Временное отключение VoiceOver при переходе в режимы `LISTENING` и `PROCESSING`
- **Release**: Восстановление VoiceOver при переходе в режим `SLEEPING`
- **Интеграция**: Бесшовная работа с системой режимов приложения

## 🔧 Архитектура

### Основные компоненты

```
voiceover_control/
├── core/
│   ├── controller.py          # Основной контроллер
│   └── __init__.py
├── tests/                     # Тесты и диагностика
│   ├── quick_voiceover_test.py
│   ├── test_voiceover_toggle.py
│   ├── test_voiceover_ducking.py
│   └── TEST_RESULTS.md
└── README.md                  # Эта инструкция
```

### Классы

- **`VoiceOverController`**: Основной класс управления VoiceOver
- **`VoiceOverControlSettings`**: Конфигурация модуля

## ⚙️ Текущая логика работы

### 1. Инициализация
```python
controller = VoiceOverController(settings)
await controller.initialize()
```

### 2. Ducking (Отключение VoiceOver)
```python
# При переходе в LISTENING или PROCESSING
await controller.duck(reason="keyboard.press")
```

**Что происходит:**
- Выполняется `Command+F5` для полного отключения VoiceOver
- Устанавливается флаг `_speech_muted_by_us = True`
- Логируется операция

### 3. Release (Восстановление VoiceOver)
```python
# При переходе в SLEEPING
await controller.release()
```

**Что происходит:**
- Выполняется `Command+F5` для включения VoiceOver обратно
- Сбрасывается флаг `_speech_muted_by_us = False`
- Логируется операция

### 4. Управление режимами
```python
# Автоматическое управление по режимам
await controller.apply_mode("listening")  # Duck
await controller.apply_mode("processing") # Duck
await controller.apply_mode("sleeping")   # Release
```

## 🛠️ Методы управления

### Основные методы

| Метод | Описание | Параметры |
|-------|----------|-----------|
| `initialize()` | Инициализация контроллера | - |
| `duck(reason)` | Отключить VoiceOver | `reason: str` |
| `release(force)` | Включить VoiceOver | `force: bool` |
| `apply_mode(mode)` | Применить режим | `mode: str` |
| `shutdown()` | Завершение работы | - |

### Внутренние методы

| Метод | Описание |
|-------|----------|
| `_toggle_voiceover_with_command_f5()` | Выполнить Command+F5 |
| `_run_osascript(script)` | Выполнить AppleScript |
| `_log_voiceover_state(context)` | Логирование состояния |

## 📊 Результаты тестирования

### ✅ РАБОТАЮЩИЕ методы:
- **Command+F5**: Полное включение/выключение VoiceOver
- **`say`**: Заставить VoiceOver говорить

### ❌ НЕ РАБОТАЮЩИЕ методы:
- **`set speechMuted`**: Свойство не существует
- **`stop speaking`**: Синтаксическая ошибка
- **`pause speaking`**: Синтаксическая ошибка
- **`set speechVolume`**: Свойство не существует

**Вывод**: Command+F5 - единственный рабочий метод управления VoiceOver.

## ⚙️ Конфигурация

### В `unified_config.yaml`:

```yaml
accessibility:
  voiceover_control:
    enabled: true
    mode: toggle_voiceover  # Используем Command+F5
    duck_on_modes:
      - listening
      - processing
    release_on_modes:
      - sleeping
    debounce_seconds: 0.25
    stop_repeats: 2
    stop_repeat_delay: 0.05
    use_apple_script_fallback: true
    engage_on_keyboard_press: true
    # Настройки логирования
    debug_logging: true
    log_osascript_commands: true
    log_voiceover_state: true
    # Метод ducking
    ducking_method: command_f5
```

### Параметры конфигурации

| Параметр | Тип | По умолчанию | Описание |
|----------|-----|--------------|----------|
| `enabled` | bool | true | Включить модуль |
| `mode` | str | "toggle_voiceover" | Режим работы |
| `duck_on_modes` | list | ["listening", "processing"] | Режимы для ducking |
| `release_on_modes` | list | ["sleeping"] | Режимы для release |
| `debounce_seconds` | float | 0.25 | Задержка между операциями |
| `debug_logging` | bool | true | Детальное логирование |

## 🔌 Интеграция

### 1. Создание интеграции

```python
# integration/integrations/voiceover_ducking_integration.py
from integration.core.base_integration import BaseIntegration
from modules.voiceover_control.core.controller import VoiceOverController, VoiceOverControlSettings

class VoiceOverDuckingIntegration(BaseIntegration):
    def __init__(self, event_bus, state_manager, error_handler, config=None):
        super().__init__(event_bus, state_manager, error_handler)
        self.config = config
        self.controller = VoiceOverController(VoiceOverControlSettings(**config))

    async def initialize(self) -> bool:
        try:
            await self.event_bus.subscribe("app.mode_changed", self.handle_mode_change)
            return await self.controller.initialize()
        except Exception as exc:
            logger.error("Failed to initialize VoiceOverDuckingIntegration: %s", exc)
            return False

    async def handle_mode_change(self, event: Dict[str, Any]) -> None:
        try:
            mode = event.get("data", {}).get("mode")
            if mode:
                await self.controller.apply_mode(mode.value)
        except Exception as exc:
            await self.error_handler.handle_error(exc, "handle_mode_change")
```

### 2. Добавление в координатор

```python
# integration/core/simple_module_coordinator.py
from integration.integrations.voiceover_ducking_integration import VoiceOverDuckingIntegration

class SimpleModuleCoordinator:
    def __init__(self):
        # ... existing code ...
        self.voiceover_ducking = VoiceOverDuckingIntegration(
            self.event_bus, self.state_manager, self.error_handler, 
            self.config.get("accessibility", {}).get("voiceover_control", {})
        )

    async def initialize_integrations(self):
        # ... existing code ...
        await self.voiceover_ducking.initialize()
```

### 3. Порядок инициализации

```python
# Рекомендуемый порядок в SimpleModuleCoordinator
async def initialize_integrations(self):
    # 1. Базовые интеграции
    await self.permissions.initialize()
    await self.hardware_id.initialize()
    
    # 2. VoiceOver (после permissions, до input)
    await self.voiceover_ducking.initialize()
    
    # 3. Остальные интеграции
    await self.input_processing.initialize()
    # ... остальные
```

## 🧪 Тестирование

### Быстрый тест
```bash
cd client/modules/voiceover_control/tests
python3 quick_voiceover_test.py
```

### Полный тест ducking
```bash
python3 test_voiceover_ducking.py
```

### Тест переключения
```bash
python3 test_voiceover_toggle.py
```

## 📝 Логирование

### Уровни логирования

- **INFO**: Основные операции (duck, release)
- **DEBUG**: Детальная информация о состоянии
- **WARNING**: Проблемы с выполнением команд
- **ERROR**: Критические ошибки

### Примеры логов

```
INFO - VoiceOverController: Using Command+F5 to disable VoiceOver (reason=keyboard.press)
INFO - VoiceOverController: Command+F5 executed successfully
INFO - VoiceOverController: VoiceOver restored via Command+F5
```

## ⚠️ Важные замечания

### 1. Требования к системе
- **macOS**: Модуль работает только на macOS
- **VoiceOver**: Должен быть включен для тестирования
- **Разрешения**: Требуется разрешение на Accessibility

### 2. Ограничения
- **Command+F5**: Единственный рабочий метод
- **Полное отключение**: VoiceOver полностью выключается/включается
- **Нет частичного контроля**: Нельзя управлять только речью

### 3. Рекомендации
- **Тестирование**: Всегда тестируйте на реальном VoiceOver
- **Логирование**: Включите debug_logging для диагностики
- **Обработка ошибок**: Модуль gracefully обрабатывает ошибки

## 🚀 Готовность к продакшену

### ✅ Готово:
- [x] Тестирование завершено
- [x] Рабочие методы определены
- [x] Контроллер обновлен
- [x] Конфигурация настроена
- [x] Документация создана
- [x] Интеграция готова

### 📋 Чеклист для интеграции:
- [ ] Создать `VoiceOverDuckingIntegration`
- [ ] Добавить в `SimpleModuleCoordinator`
- [ ] Настроить порядок инициализации
- [ ] Протестировать в основном приложении
- [ ] Проверить логирование

## 🔗 Связанные файлы

- **Контроллер**: `client/modules/voiceover_control/core/controller.py`
- **Конфигурация**: `client/config/unified_config.yaml`
- **Тесты**: `client/modules/voiceover_control/tests/`
- **Результаты**: `client/modules/voiceover_control/tests/TEST_RESULTS.md`

---

**Модуль готов к интеграции в основное приложение!** 🎯
