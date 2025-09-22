# Autostart Manager Module

Модуль для управления автозапуском приложения.

## Функциональность

- ✅ LaunchAgent управление (основной метод)
- ✅ Login Items управление (альтернативный метод)
- ✅ Bundle ID подход (без жестких путей)
- ✅ Исправленный KeepAlive (совместимость с обновлениями)
- ✅ Автоматическая генерация plist файлов

## Использование

```python
from modules.autostart_manager import AutostartManager, AutostartStatus, AutostartConfig

# Конфигурация
config = AutostartConfig(
    enabled=True,
    method="launch_agent",
    bundle_id="com.nexy.assistant",
    delay_seconds=5
)

# Создание менеджера
manager = AutostartManager(config)

# Включение автозапуска
status = await manager.enable_autostart()
if status == AutostartStatus.ENABLED:
    print("✅ Автозапуск включен")

# Проверка статуса
status = await manager.get_autostart_status()
print(f"Статус автозапуска: {status.value}")

# Отключение автозапуска
await manager.disable_autostart()
```

## Конфигурация

```yaml
autostart:
  enabled: true
  delay: 5
  method: "launch_agent"
  launch_agent_path: "~/Library/LaunchAgents/com.nexy.assistant.plist"
  bundle_id: "com.nexy.assistant"
```

## LaunchAgent

- **Bundle ID подход**: `open -b com.nexy.assistant` (работает везде)
- **Исправленный KeepAlive**: `SuccessfulExit: false` (совместимость с обновлениями)
- **Автогенерация plist**: динамическое создание файлов конфигурации
- **Безопасная установка**: проверка существования и перезагрузка

## Безопасность

- **Нет жестких путей**: работает независимо от местоположения .app
- **Совместимость с обновлениями**: не конфликтует с UpdaterIntegration
- **Автоматическая очистка**: безопасное удаление при отключении
