"""
Service интеграции для координации workflow интеграций
"""

from .grpc_service_integration import GrpcServiceIntegration
from .module_coordinator_integration import ModuleCoordinatorIntegration

__all__ = [
    'GrpcServiceIntegration',
    'ModuleCoordinatorIntegration'
]
