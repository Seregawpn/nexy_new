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
from .config.grpc_config import (
    create_default_config, create_local_config, 
    create_production_config, create_test_config
)

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
    
    # Конфигурация
    "create_default_config",
    "create_local_config",
    "create_production_config",
    "create_test_config",
    
    # Версия
    "__version__"
]


def create_grpc_client(config_type: str = "default", **kwargs) -> GrpcClient:
    """
    Создает экземпляр GrpcClient с конфигурацией
    
    Args:
        config_type: Тип конфигурации (default, local, production, test)
        **kwargs: Дополнительные параметры конфигурации
        
    Returns:
        GrpcClient: Экземпляр gRPC клиента
    """
    if config_type == "local":
        config = create_local_config()
    elif config_type == "production":
        config = create_production_config()
    elif config_type == "test":
        config = create_test_config()
    else:
        config = create_default_config()
    
    # Обновляем конфигурацию дополнительными параметрами
    config.update(kwargs)
    
    return GrpcClient(config)


def create_default_grpc_client(**kwargs) -> GrpcClient:
    """
    Создает GrpcClient с конфигурацией по умолчанию
    
    Returns:
        GrpcClient: Экземпляр gRPC клиента
    """
    return create_grpc_client("default", **kwargs)
