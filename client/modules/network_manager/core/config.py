"""
Конфигурация NetworkManager Module
Интегрируется с unified_config.yaml
"""

from dataclasses import dataclass
from typing import List, Optional
from .types import NetworkConfig

@dataclass
class NetworkManagerConfig:
    """Конфигурация NetworkManager с интеграцией unified_config"""
    
    # Основные настройки
    check_interval: float = 30.0
    ping_timeout: float = 5.0
    max_retries: int = 3
    retry_delay: float = 5.0
    
    # Хосты для пинга (из unified_config.yaml)
    ping_hosts: List[str] = None
    
    # URL для тестирования
    test_urls: List[str] = None
    
    def __post_init__(self):
        if self.ping_hosts is None:
            self.ping_hosts = [
                "8.8.8.8",      # Google DNS
                "1.1.1.1",      # Cloudflare DNS
                "google.com"     # Google
            ]
        
        if self.test_urls is None:
            self.test_urls = [
                "https://www.google.com",
                "https://www.apple.com",
                "https://www.cloudflare.com"
            ]
    
    @classmethod
    def from_unified_config(cls, config_data: dict) -> 'NetworkManagerConfig':
        """Создать конфигурацию из unified_config.yaml"""
        network_data = config_data.get('network', {})
        
        return cls(
            check_interval=network_data.get('connection_check_interval', 30.0),
            ping_timeout=network_data.get('ping_timeout', 5.0),
            ping_hosts=network_data.get('ping_hosts', [
                "8.8.8.8",
                "1.1.1.1", 
                "google.com"
            ])
        )
    
    def to_network_config(self) -> NetworkConfig:
        """Преобразовать в NetworkConfig для совместимости"""
        return NetworkConfig(
            check_interval=self.check_interval,
            ping_timeout=self.ping_timeout,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            ping_hosts=self.ping_hosts,
            test_urls=self.test_urls
        )
