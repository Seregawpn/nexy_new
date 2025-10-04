"""
Диагностический скрипт для проверки определения путей к ресурсам
"""

import sys
from pathlib import Path

# Добавляем пути к модулям
CLIENT_ROOT = Path(__file__).parent
sys.path.insert(0, str(CLIENT_ROOT))
sys.path.insert(0, str(CLIENT_ROOT / "modules"))

from modules.welcome_message.utils.resource_path import (
    get_resource_base_path,
    get_resource_path,
    resource_exists
)
from modules.welcome_message.core.types import WelcomeConfig

def main():
    print("=" * 80)
    print("🔍 Диагностика путей к ресурсам")
    print("=" * 80)
    
    # Проверяем базовый путь
    base_path = get_resource_base_path()
    print(f"\n📁 Базовый путь: {base_path}")
    print(f"   Существует: {base_path.exists()}")
    
    # Проверяем sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        print(f"   🔹 PyInstaller режим (onefile): {sys._MEIPASS}")
    else:
        print(f"   🔹 Development режим")
    
    # Проверяем путь к main.py
    main_py = base_path / "main.py"
    print(f"\n📄 main.py: {main_py}")
    print(f"   Существует: {main_py.exists()}")
    
    # Проверяем наличие assets каталога (общие ресурсы)
    assets_dir = base_path / "assets"
    print(f"\n📂 assets/: {assets_dir}")
    print(f"   Существует: {assets_dir.exists()}")

    # Проверяем WelcomeConfig
    print(f"\n🎵 WelcomeConfig:")
    config = WelcomeConfig()
    print(f"   enabled={config.enabled}")
    print(f"   use_server={config.use_server}")
    print(f"   server_timeout_sec={config.server_timeout_sec}")
    
    # Проверяем resource_exists
    print(f"\n✅ resource_exists():")
    test_paths = [
        "config/unified_config.yaml"
    ]
    for test_path in test_paths:
        exists = resource_exists(test_path)
        status = "✓" if exists else "✗"
        print(f"   {status} {test_path}")
    
    print("\n" + "=" * 80)
    
    # Финальный статус
    if config.use_server:
        print("✅ УСПЕХ: Конфигурация использует серверную генерацию приветствия")
    else:
        print("❌ ОШИБКА: Конфигурация отключила серверную генерацию приветствия")
    
    print("=" * 80)

if __name__ == "__main__":
    main()




