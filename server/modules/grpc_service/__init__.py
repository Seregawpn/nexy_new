"""
gRPC Service Module

Универсальный gRPC сервис для интеграции всех модулей
"""

from .core.grpc_service_manager import GrpcServiceManager

__all__ = ['GrpcServiceManager']
