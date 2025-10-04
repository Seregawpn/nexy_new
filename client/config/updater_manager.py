"""
Централизованный менеджер обновлений для Nexy AI Assistant
Единственное место для управления всеми настройками обновлений
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class UpdateChannel:
    """Информация о канале обновлений"""
    name: str
    url: str
    description: str
    enabled: bool = True


@dataclass
class UpdaterConfig:
    """Конфигурация системы обновлений"""
    enabled: bool
    update_channel: str
    appcast_url: str
    manifest_url: str
    auto_check: bool
    check_interval: int
    check_on_startup: bool
    auto_install: bool
    install_after_download: bool
    silent_mode: bool
    security: Dict[str, Any]
    network: Dict[str, Any]
    ui: Dict[str, Any]
    channels: Dict[str, UpdateChannel]


class UpdaterManager:
    """Централизованный менеджер обновлений"""
    
    def __init__(self, config_path: str = "config/unified_config.yaml"):
        self.config_path = config_path
        self._config = None
        self._updater_config = None
        self._load_config()
    
    def _load_config(self):
        """Загружает конфигурацию из файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Парсим конфигурацию обновлений
            self._parse_updater_config()
            
        except Exception as e:
            raise RuntimeError(f"Не удалось загрузить конфигурацию из {self.config_path}: {e}")
    
    def _parse_updater_config(self):
        """Парсит конфигурацию обновлений"""
        updater_data = self._config.get('updater', {})
        
        # Парсим каналы
        channels = {}
        channels_data = updater_data.get('channels', {})
        for channel_name, channel_data in channels_data.items():
            channels[channel_name] = UpdateChannel(
                name=channel_name,
                url=channel_data.get('url', ''),
                description=channel_data.get('description', ''),
                enabled=channel_data.get('enabled', True)
            )
        
        self._updater_config = UpdaterConfig(
            enabled=updater_data.get('enabled', True),
            update_channel=updater_data.get('update_channel', 'stable'),
            appcast_url=updater_data.get('appcast_url', ''),
            manifest_url=updater_data.get('manifest_url', ''),
            auto_check=updater_data.get('auto_check', True),
            check_interval=updater_data.get('check_interval', 3600),
            check_on_startup=updater_data.get('check_on_startup', True),
            auto_install=updater_data.get('auto_install', False),
            install_after_download=updater_data.get('install_after_download', False),
            silent_mode=updater_data.get('silent_mode', True),
            security=updater_data.get('security', {}),
            network=updater_data.get('network', {}),
            ui=updater_data.get('ui', {}),
            channels=channels
        )
    
    def _save_config(self):
        """Сохраняет конфигурацию в файл"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            raise RuntimeError(f"Не удалось сохранить конфигурацию в {self.config_path}: {e}")
    
    def get_updater_config(self) -> UpdaterConfig:
        """Получает конфигурацию обновлений"""
        return self._updater_config
    
    def get_current_channel(self) -> UpdateChannel:
        """Получает текущий канал обновлений"""
        channel_name = self._updater_config.update_channel
        return self._updater_config.channels.get(channel_name)
    
    def get_all_channels(self) -> Dict[str, UpdateChannel]:
        """Получает все доступные каналы"""
        return self._updater_config.channels
    
    def switch_channel(self, channel_name: str) -> bool:
        """Переключает канал обновлений"""
        try:
            if channel_name not in self._updater_config.channels:
                return False
            
            # Обновляем конфигурацию
            self._config['updater']['update_channel'] = channel_name
            self._updater_config.update_channel = channel_name
            
            # Обновляем URL для текущего канала
            channel = self._updater_config.channels[channel_name]
            self._config['updater']['appcast_url'] = channel.url
            self._updater_config.appcast_url = channel.url
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка переключения канала {channel_name}: {e}")
            return False
    
    def update_channel_url(self, channel_name: str, new_url: str) -> bool:
        """Обновляет URL канала обновлений"""
        try:
            if channel_name not in self._updater_config.channels:
                return False
            
            # Обновляем в конфигурации
            self._config['updater']['channels'][channel_name]['url'] = new_url
            self._updater_config.channels[channel_name].url = new_url
            
            # Если это текущий канал, обновляем и основной URL
            if self._updater_config.update_channel == channel_name:
                self._config['updater']['appcast_url'] = new_url
                self._updater_config.appcast_url = new_url
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка обновления URL канала {channel_name}: {e}")
            return False
    
    def add_channel(self, channel_name: str, url: str, description: str = "") -> bool:
        """Добавляет новый канал обновлений"""
        try:
            # Добавляем в конфигурацию
            if 'channels' not in self._config['updater']:
                self._config['updater']['channels'] = {}
            
            self._config['updater']['channels'][channel_name] = {
                'url': url,
                'description': description,
                'enabled': True
            }
            
            # Добавляем в объект конфигурации
            self._updater_config.channels[channel_name] = UpdateChannel(
                name=channel_name,
                url=url,
                description=description,
                enabled=True
            )
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка добавления канала {channel_name}: {e}")
            return False
    
    def remove_channel(self, channel_name: str) -> bool:
        """Удаляет канал обновлений"""
        try:
            if channel_name not in self._updater_config.channels:
                return False
            
            # Нельзя удалить текущий канал
            if self._updater_config.update_channel == channel_name:
                return False
            
            # Удаляем из конфигурации
            del self._config['updater']['channels'][channel_name]
            del self._updater_config.channels[channel_name]
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка удаления канала {channel_name}: {e}")
            return False
    
    def update_setting(self, setting_name: str, value: Any) -> bool:
        """Обновляет настройку обновлений"""
        try:
            # Обновляем в конфигурации
            self._config['updater'][setting_name] = value
            
            # Обновляем в объекте конфигурации
            if hasattr(self._updater_config, setting_name):
                setattr(self._updater_config, setting_name, value)
            
            self._save_config()
            return True
            
        except Exception as e:
            print(f"Ошибка обновления настройки {setting_name}: {e}")
            return False
    
    def get_manifest_url(self) -> str:
        """Получает URL манифеста для текущего канала"""
        channel = self.get_current_channel()
        if channel and channel.url:
            return channel.url
        return self._updater_config.manifest_url
    
    def is_enabled(self) -> bool:
        """Проверяет, включены ли обновления"""
        return self._updater_config.enabled
    
    def enable(self) -> bool:
        """Включает обновления"""
        return self.update_setting('enabled', True)
    
    def disable(self) -> bool:
        """Отключает обновления"""
        return self.update_setting('enabled', False)


# Глобальный экземпляр для использования в приложении
updater_manager = UpdaterManager()


def get_updater_manager() -> UpdaterManager:
    """Получает глобальный экземпляр UpdaterManager"""
    return updater_manager


# Удобные функции для быстрого доступа
def get_updater_config() -> UpdaterConfig:
    """Получает конфигурацию обновлений"""
    return updater_manager.get_updater_config()


def get_current_channel() -> UpdateChannel:
    """Получает текущий канал обновлений"""
    return updater_manager.get_current_channel()


def switch_channel(channel_name: str) -> bool:
    """Переключает канал обновлений"""
    return updater_manager.switch_channel(channel_name)


def update_channel_url(channel_name: str, new_url: str) -> bool:
    """Обновляет URL канала обновлений"""
    return updater_manager.update_channel_url(channel_name, new_url)


if __name__ == "__main__":
    # Пример использования
    manager = UpdaterManager()
    
    print("=== КОНФИГУРАЦИЯ ОБНОВЛЕНИЙ ===")
    config = manager.get_updater_config()
    print(f"Включено: {config.enabled}")
    print(f"Канал: {config.update_channel}")
    print(f"URL: {config.appcast_url}")
    print(f"Интервал проверки: {config.check_interval} сек")
    
    print(f"\n=== ТЕКУЩИЙ КАНАЛ ===")
    current = manager.get_current_channel()
    if current:
        print(f"Канал: {current.name}")
        print(f"URL: {current.url}")
        print(f"Описание: {current.description}")
    
    print(f"\n=== ВСЕ КАНАЛЫ ===")
    for name, channel in manager.get_all_channels().items():
        print(f"{name}: {channel.url} - {channel.description}")
