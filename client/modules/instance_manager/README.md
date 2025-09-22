# Instance Manager Module

Модуль для управления экземплярами приложения и предотвращения дублирования.

## Функциональность

- ✅ Проверка на дублирование экземпляров
- ✅ Файловая блокировка с TOCTOU защитой
- ✅ PID проверка процессов
- ✅ Автоматическая очистка устаревших блокировок
- ✅ Bundle ID проверка для безопасности

## Использование

```python
from modules.instance_manager import InstanceManager, InstanceStatus, InstanceManagerConfig

# Конфигурация
config = InstanceManagerConfig(
    enabled=True,
    lock_file="~/Library/Application Support/Nexy/nexy.lock",
    timeout_seconds=30,
    pid_check=True
)

# Создание менеджера
manager = InstanceManager(config)

# Проверка дублирования
status = await manager.check_single_instance()
if status == InstanceStatus.DUPLICATE:
    print("❌ Приложение уже запущено!")
    sys.exit(1)

# Захват блокировки
if await manager.acquire_lock():
    print("✅ Блокировка захвачена")
    
    # Освобождение блокировки при завершении
    await manager.release_lock()
```

## Конфигурация

```yaml
instance_manager:
  enabled: true
  lock_file: "~/Library/Application Support/Nexy/nexy.lock"
  timeout_seconds: 30
  cleanup_on_startup: true
  show_duplicate_message: true
  pid_check: true
```

## Безопасность

- **TOCTOU защита**: `O_CREAT | O_EXCL` + `fcntl` advisory lock
- **PID проверка**: проверка существования и имени процесса
- **Bundle ID проверка**: убеждаемся что процесс действительно Nexy
- **Автоматическая очистка**: удаление устаревших блокировок
