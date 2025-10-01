#!/usr/bin/env python3
"""
Удобный скрипт для изменения IP-адреса сервера
Использование: python config/change_server.py <новый_ip> [окружение]
"""

import sys
import os
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.server_config_sync import ServerConfigSynchronizer


def main():
    if len(sys.argv) < 2:
        print("❌ Использование: python config/change_server.py <новый_ip> [окружение]")
        print("   Окружения: local, production, fallback (по умолчанию: production)")
        print("")
        print("Примеры:")
        print("  python config/change_server.py 192.168.1.100")
        print("  python config/change_server.py 10.0.0.50 local")
        print("  python config/change_server.py server.example.com production")
        sys.exit(1)
    
    new_ip = sys.argv[1]
    environment = sys.argv[2] if len(sys.argv) > 2 else "production"
    
    if environment not in ["local", "production", "fallback"]:
        print(f"❌ Неверное окружение: {environment}")
        print("   Доступные окружения: local, production, fallback")
        sys.exit(1)
    
    print(f"🔄 Изменяю IP-адрес {environment} сервера на: {new_ip}")
    
    synchronizer = ServerConfigSynchronizer()
    
    # Показываем текущую конфигурацию
    current_config = synchronizer.get_current_server_config(environment)
    if current_config:
        print(f"📋 Текущая конфигурация {environment}:")
        print(f"   Host: {current_config['host']}")
        print(f"   Port: {current_config['port']}")
        print(f"   SSL: {current_config['ssl']}")
        print("")
    
    # Изменяем IP
    success = synchronizer.change_server_ip(new_ip, environment)
    
    if success:
        print(f"✅ Успешно изменен IP-адрес {environment} сервера на: {new_ip}")
        print("")
        print("📋 Обновленная конфигурация:")
        updated_config = synchronizer.get_current_server_config(environment)
        if updated_config:
            print(f"   Host: {updated_config['host']}")
            print(f"   Port: {updated_config['port']}")
            print(f"   SSL: {updated_config['ssl']}")
            print(f"   Timeout: {updated_config['timeout']}s")
            print(f"   Retry attempts: {updated_config['retry_attempts']}")
        
        print("")
        print("🔄 Синхронизированы файлы:")
        print("   ✅ unified_config.yaml")
        print("   ✅ network_config.yaml")
        print("   ✅ modules/grpc_client/config/grpc_config.py")
        print("")
        print("💡 Теперь можно запускать приложение с новым сервером!")
        
    else:
        print(f"❌ Ошибка при изменении IP-адреса сервера")
        sys.exit(1)


if __name__ == "__main__":
    main()
