"""
Конфигурация gRPC клиента
"""

from .grpc_config import (
    create_default_config,
    create_local_config,
    create_production_config,
    create_test_config
)

__all__ = [
    "create_default_config",
    "create_local_config", 
    "create_production_config",
    "create_test_config"
]
