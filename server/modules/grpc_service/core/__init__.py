"""
Core components для gRPC Service Module
"""

from .grpc_service_manager import GrpcServiceManager
from .grpc_server import run_server, NewStreamingServicer

__all__ = ['GrpcServiceManager', 'run_server', 'NewStreamingServicer']
