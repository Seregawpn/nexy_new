"""
gRPC Service Module

Универсальный gRPC сервис для интеграции всех модулей
"""

from .core.grpc_service_manager import GrpcServiceManager
from .core.grpc_server import run_server, NewStreamingServicer

# Protobuf файлы
import streaming_pb2
import streaming_pb2_grpc

__all__ = ['GrpcServiceManager', 'run_server', 'NewStreamingServicer', 'streaming_pb2', 'streaming_pb2_grpc']
