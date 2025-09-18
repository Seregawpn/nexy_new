"""
Типы данных для модуля gRPC клиента
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


class ConnectionState(Enum):
    """Состояния соединения"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class RetryStrategy(Enum):
    """Стратегии повторных попыток"""
    NONE = "none"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


@dataclass
class ServerConfig:
    """Конфигурация сервера"""
    address: str
    port: int
    use_ssl: bool = False
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    max_message_size: int = 50 * 1024 * 1024  # 50MB
    # Keepalive defaults tuned to avoid server GOAWAY (too_many_pings)
    keep_alive_time: int = 120
    keep_alive_timeout: int = 10
    keep_alive_permit_without_calls: bool = False


@dataclass
class ConnectionMetrics:
    """Метрики соединения"""
    total_connections: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_connection_time: Optional[float] = None
    last_error: Optional[str] = None


@dataclass
class RetryConfig:
    """Конфигурация retry механизма"""
    max_attempts: int = 3
    base_delay: float = 1.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    max_delay: float = 60.0
    jitter: bool = True


@dataclass
class HealthCheckConfig:
    """Конфигурация health check"""
    enabled: bool = True
    interval: float = 30.0
    timeout: float = 5.0
    max_failures: int = 3
    recovery_threshold: int = 1


# Callback типы
ConnectionCallback = Callable[[ConnectionState], None]
ErrorCallback = Callable[[Exception, str], None]
MetricsCallback = Callable[[ConnectionMetrics], None]
