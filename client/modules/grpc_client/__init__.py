"""
Модуль gRPC клиента с модульной архитектурой

Этот модуль предоставляет:
- Модульное управление gRPC соединениями
- Retry механизмы с различными стратегиями
- Health check систему
- Гибкую конфигурацию серверов
- Thread-safe операции
- Мониторинг и метрики
"""

from .core.grpc_client import GrpcClient
from .core.types import (
    ConnectionState, RetryStrategy, ServerConfig, 
    ConnectionMetrics, RetryConfig, HealthCheckConfig
)
# Конфигурация теперь централизована в unified_config.yaml
# Функции конфигурации удалены в пользу централизованной системы

# Версия модуля
__version__ = "1.0.0"

# Экспортируемые классы и функции
__all__ = [
    # Основные классы
    "GrpcClient",
    
    # Типы данных
    "ConnectionState",
    "RetryStrategy", 
    "ServerConfig",
    "ConnectionMetrics",
    "RetryConfig",
    "HealthCheckConfig",
    
    # Конфигурация централизована в unified_config.yaml
    
    # Версия
    "__version__"
]


def create_grpc_client(**kwargs) -> GrpcClient:
    """
    Создает экземпляр GrpcClient с централизованной конфигурацией
    
    Args:
        **kwargs: Дополнительные параметры конфигурации (переопределяют unified_config.yaml)
        
    Returns:
        GrpcClient: Экземпляр gRPC клиента
    """
    return GrpcClient(kwargs if kwargs else None)


def create_default_grpc_client(**kwargs) -> GrpcClient:
    """
    Создает GrpcClient с централизованной конфигурацией
    
    Returns:
        GrpcClient: Экземпляр gRPC клиента
    """
    return create_grpc_client(**kwargs)
