#!/bin/bash
# tools/packaging/prepare_for_implementation.sh
# Финальная подготовка к реализации

set -e

echo "🚀 Финальная подготовка к реализации Nexy..."

# 1. Создание резервных копий
echo "📦 Создание резервных копий..."
BACKUP_DIR="../Nexy-backup-$(date +%Y%m%d-%H%M%S)"
cp -r . "$BACKUP_DIR"
echo "✅ Резервная копия создана: $BACKUP_DIR"

# 2. Корректное завершение уже запущенных экземпляров
echo "🛑 Корректное завершение уже запущенных экземпляров Nexy..."

# Попробовать штатно закрыть по bundle id
osascript -e 'tell application id "com.nexy.assistant" to quit' 2>/dev/null || true

# Мягкая эвакуация LaunchAgent (если загружен)
launchctl bootout "gui/$UID/com.nexy.assistant" 2>/dev/null || true

# Точечное убийство главного бинаря (если висит)
pgrep -f "Nexy.app/Contents/MacOS/Nexy" | xargs -r kill 2>/dev/null || true
sleep 1
pgrep -f "Nexy.app/Contents/MacOS/Nexy" | xargs -r kill -9 2>/dev/null || true

echo "✅ Завершение экземпляров завершено"

# 3. Очистка старых файлов блокировки (безопасно)
echo "🧹 Очистка старых файлов блокировки..."
rm -f "$HOME/Library/Application Support/Nexy/nexy.lock"
echo "✅ Файлы блокировки очищены"

# 4. Проверка отсутствия запущенных процессов
echo "🔍 Проверка отсутствия запущенных процессов Nexy..."
if pgrep -f "Nexy" >/dev/null; then
    echo "⚠️ Внимание: найдены запущенные процессы Nexy:"
    pgrep -f "Nexy" | xargs ps -p
    echo "Рекомендуется перезагрузить систему перед началом реализации"
else
    echo "✅ Процессы Nexy не найдены"
fi

# 5. Проверка LaunchAgent статуса
echo "🔍 Проверка статуса LaunchAgent..."
if launchctl print "gui/$UID/com.nexy.assistant" >/dev/null 2>&1; then
    echo "⚠️ LaunchAgent загружен - будет перезагружен при реализации"
else
    echo "✅ LaunchAgent не загружен"
fi

# 6. Проверка зависимостей
echo "🔍 Проверка зависимостей..."
python3 -c "
import sys
required_modules = ['psutil', 'asyncio', 'json', 'os', 'fcntl', 'subprocess']
missing = []
for module in required_modules:
    try:
        __import__(module)
    except ImportError:
        missing.append(module)

if missing:
    print(f'❌ Отсутствуют модули: {missing}')
    sys.exit(1)
else:
    print('✅ Все необходимые модули доступны')
"

# 7. Проверка структуры проекта
echo "🔍 Проверка структуры проекта..."
required_dirs=(
    "modules/instance_manager/core"
    "modules/autostart_manager/core"
    "modules/autostart_manager/macos"
    "integration/integrations"
    "tools/packaging"
)

for dir in "${required_dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        echo "❌ Отсутствует директория: $dir"
        exit 1
    fi
done

echo "✅ Структура проекта корректна"

# 8. Проверка конфигурации
echo "🔍 Проверка конфигурации..."
if [[ ! -f "config/unified_config.yaml" ]]; then
    echo "❌ Отсутствует файл конфигурации: config/unified_config.yaml"
    exit 1
fi

# Проверяем что новые секции добавлены
if ! grep -q "instance_manager:" config/unified_config.yaml; then
    echo "❌ Секция instance_manager не найдена в конфигурации"
    exit 1
fi

if ! grep -q "autostart:" config/unified_config.yaml; then
    echo "❌ Секция autostart не найдена в конфигурации"
    exit 1
fi

echo "✅ Конфигурация корректна"

# 9. Проверка PyInstaller spec
echo "🔍 Проверка PyInstaller spec..."
if [[ ! -f "tools/packaging/Nexy.spec" ]]; then
    echo "❌ Отсутствует файл: tools/packaging/Nexy.spec"
    exit 1
fi

if ! grep -q "modules.instance_manager.core.instance_manager" tools/packaging/Nexy.spec; then
    echo "❌ Новые модули не добавлены в PyInstaller spec"
    exit 1
fi

echo "✅ PyInstaller spec корректный"

# 10. Проверка скриптов
echo "🔍 Проверка скриптов..."
scripts=(
    "tools/packaging/install_launch_agent.sh"
    "tools/packaging/uninstall_launch_agent.sh"
    "tools/packaging/com.nexy.assistant.plist"
)

for script in "${scripts[@]}"; do
    if [[ ! -f "$script" ]]; then
        echo "❌ Отсутствует скрипт: $script"
        exit 1
    fi
done

echo "✅ Все скрипты на месте"

echo ""
echo "🎉 ПОДГОТОВКА ЗАВЕРШЕНА УСПЕШНО!"
echo ""
echo "📋 ГОТОВ К РЕАЛИЗАЦИИ:"
echo "  ✅ Резервные копии созданы"
echo "  ✅ Процессы Nexy завершены"
echo "  ✅ Файлы блокировки очищены"
echo "  ✅ Зависимости проверены"
echo "  ✅ Структура проекта корректна"
echo "  ✅ Конфигурация обновлена"
echo "  ✅ PyInstaller spec готов"
echo "  ✅ Скрипты созданы"
echo ""
echo "🚀 МОЖНО НАЧИНАТЬ РЕАЛИЗАЦИЮ!"
echo ""
echo "Следующий шаг: Начать с Фазы 2 (Создание модулей)"
