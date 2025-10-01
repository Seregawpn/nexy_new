"""
Автоматический синхронизатор конфигурации серверов
Обеспечивает единую точку управления IP-адресами и настройками серверов
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ServerConfigSynchronizer:
    """Синхронизирует настройки серверов между всеми конфигурационными файлами"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            self.config_dir = Path(__file__).parent
        else:
            self.config_dir = Path(config_dir)
        
        self.unified_config_path = self.config_dir / "unified_config.yaml"
        self.network_config_path = self.config_dir / "network_config.yaml"
        
    def sync_all_configs(self, target_environment: str = "production") -> bool:
        """
        Синхронизирует все конфигурационные файлы на основе unified_config.yaml
        
        Args:
            target_environment: Какой сервер использовать как основной (local/production/fallback)
        
        Returns:
            bool: True если синхронизация прошла успешно
        """
        try:
            logger.info(f"Starting server config synchronization for environment: {target_environment}")
            
            # 1. Загружаем основную конфигурацию
            unified_config = self._load_unified_config()
            if not unified_config:
                logger.error("Failed to load unified_config.yaml")
                return False
            
            # 2. Синхронизируем network_config.yaml
            self._sync_network_config(unified_config)
            
            # 3. Синхронизируем grpc секцию в unified_config.yaml
            self._sync_grpc_section(unified_config, target_environment)
            
            # 4. Обновляем хардкод в модулях
            self._sync_module_configs(unified_config, target_environment)
            
            logger.info("Server config synchronization completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to sync server configs: {e}")
            return False
    
    def _load_unified_config(self) -> Optional[Dict[str, Any]]:
        """Загружает unified_config.yaml"""
        try:
            with open(self.unified_config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load unified_config.yaml: {e}")
            return None
    
    def _save_unified_config(self, config: Dict[str, Any]) -> bool:
        """Сохраняет unified_config.yaml"""
        try:
            with open(self.unified_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            return True
        except Exception as e:
            logger.error(f"Failed to save unified_config.yaml: {e}")
            return False
    
    def _sync_network_config(self, unified_config: Dict[str, Any]):
        """Синхронизирует network_config.yaml с unified_config.yaml"""
        try:
            servers = unified_config.get('servers', {})
            grpc_servers = servers.get('grpc_servers', {})
            appcast = servers.get('appcast', {})
            
            # Создаем network_config структуру
            network_config = {
                'appcast': appcast,
                'grpc_servers': grpc_servers,
                'network': {
                    'auto_fallback': True,
                    'connection_check_interval': 5,
                    'ping_hosts': ['8.8.8.8', '1.1.1.1', 'google.com'],
                    'ping_timeout': 5
                }
            }
            
            # Сохраняем network_config.yaml
            with open(self.network_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(network_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info("network_config.yaml synchronized")
            
        except Exception as e:
            logger.error(f"Failed to sync network_config.yaml: {e}")
    
    def _sync_grpc_section(self, unified_config: Dict[str, Any], target_environment: str):
        """Синхронизирует grpc секцию с выбранным сервером"""
        try:
            servers = unified_config.get('servers', {})
            grpc_servers = servers.get('grpc_servers', {})
            
            if target_environment not in grpc_servers:
                logger.warning(f"Environment '{target_environment}' not found, using 'local'")
                target_environment = 'local'
            
            target_server = grpc_servers[target_environment]
            
            # Обновляем grpc секцию
            if 'grpc' not in unified_config:
                unified_config['grpc'] = {}
            
            unified_config['grpc'].update({
                'server_host': target_server['host'],
                'server_port': target_server['port'],
                'use_tls': target_server['ssl']
            })
            
            # Сохраняем обновленную конфигурацию
            self._save_unified_config(unified_config)
            logger.info(f"grpc section synchronized with {target_environment} server")
            
        except Exception as e:
            logger.error(f"Failed to sync grpc section: {e}")
    
    def _sync_module_configs(self, unified_config: Dict[str, Any], target_environment: str):
        """Обновляет хардкод в модулях"""
        try:
            servers = unified_config.get('servers', {})
            grpc_servers = servers.get('grpc_servers', {})
            
            if target_environment not in grpc_servers:
                target_environment = 'local'
            
            target_server = grpc_servers[target_environment]
            
            # Обновляем grpc_client модуль
            self._update_grpc_client_module(target_server)
            
            logger.info("Module configs synchronized")
            
        except Exception as e:
            logger.error(f"Failed to sync module configs: {e}")
    
    def _update_grpc_client_module(self, server_config: Dict[str, Any]):
        """Обновляет конфигурацию в grpc_client модуле"""
        try:
            # Путь к файлу конфигурации grpc_client
            grpc_config_path = Path(__file__).parent.parent / "modules" / "grpc_client" / "config" / "grpc_config.py"
            
            if not grpc_config_path.exists():
                logger.warning("grpc_config.py not found, skipping module update")
                return
            
            # Читаем файл
            with open(grpc_config_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Обновляем production сервер
            old_production = "'address': '20.151.51.172',"
            new_production = f"'address': '{server_config['host']}',"
            
            if old_production in content:
                content = content.replace(old_production, new_production)
                
                # Сохраняем обновленный файл
                with open(grpc_config_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"Updated grpc_client module with server: {server_config['host']}")
            else:
                logger.info("No hardcoded production server found in grpc_client module")
                
        except Exception as e:
            logger.error(f"Failed to update grpc_client module: {e}")
    
    def change_server_ip(self, new_ip: str, environment: str = "production") -> bool:
        """
        Изменяет IP-адрес сервера в единой точке и синхронизирует все конфигурации
        
        Args:
            new_ip: Новый IP-адрес
            environment: Окружение для изменения (local/production/fallback)
        
        Returns:
            bool: True если изменение прошло успешно
        """
        try:
            logger.info(f"Changing {environment} server IP to: {new_ip}")
            
            # 1. Загружаем конфигурацию
            unified_config = self._load_unified_config()
            if not unified_config:
                return False
            
            # 2. Обновляем IP в servers секции
            servers = unified_config.get('servers', {})
            grpc_servers = servers.get('grpc_servers', {})
            
            if environment not in grpc_servers:
                logger.error(f"Environment '{environment}' not found")
                return False
            
            grpc_servers[environment]['host'] = new_ip
            
            # 3. Сохраняем обновленную конфигурацию
            self._save_unified_config(unified_config)
            
            # 4. Синхронизируем все файлы
            return self.sync_all_configs(environment)
            
        except Exception as e:
            logger.error(f"Failed to change server IP: {e}")
            return False
    
    def get_current_server_config(self, environment: str = "production") -> Optional[Dict[str, Any]]:
        """Получает текущую конфигурацию сервера"""
        try:
            unified_config = self._load_unified_config()
            if not unified_config:
                return None
            
            servers = unified_config.get('servers', {})
            grpc_servers = servers.get('grpc_servers', {})
            
            return grpc_servers.get(environment)
            
        except Exception as e:
            logger.error(f"Failed to get server config: {e}")
            return None


def main():
    """CLI для управления конфигурацией серверов"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Server Configuration Synchronizer")
    parser.add_argument("--change-ip", help="Change server IP address")
    parser.add_argument("--environment", default="production", choices=["local", "production", "fallback"],
                       help="Target environment")
    parser.add_argument("--sync", action="store_true", help="Sync all configurations")
    parser.add_argument("--show", action="store_true", help="Show current server config")
    
    args = parser.parse_args()
    
    synchronizer = ServerConfigSynchronizer()
    
    if args.change_ip:
        success = synchronizer.change_server_ip(args.change_ip, args.environment)
        if success:
            print(f"✅ Successfully changed {args.environment} server IP to {args.change_ip}")
        else:
            print(f"❌ Failed to change server IP")
            exit(1)
    
    elif args.sync:
        success = synchronizer.sync_all_configs(args.environment)
        if success:
            print(f"✅ Successfully synchronized all configurations for {args.environment}")
        else:
            print(f"❌ Failed to synchronize configurations")
            exit(1)
    
    elif args.show:
        config = synchronizer.get_current_server_config(args.environment)
        if config:
            print(f"Current {args.environment} server config:")
            for key, value in config.items():
                print(f"  {key}: {value}")
        else:
            print(f"❌ Failed to get server config")
            exit(1)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
