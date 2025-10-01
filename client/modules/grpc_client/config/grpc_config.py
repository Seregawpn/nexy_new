"""
Конфигурация для gRPC клиента
"""

from typing import Dict, Any
from ..core.types import ServerConfig, RetryStrategy, HealthCheckConfig


def create_default_config() -> Dict[str, Any]:
    """Создает конфигурацию по умолчанию"""
    return {
        'servers': {
            'local': {
                'address': '127.0.0.1',
                'port': 50051,
                'use_ssl': False,
                'timeout': 30,
                'retry_attempts': 3,
                'retry_delay': 1.0
            },
            'production': {
                'address': '20.151.51.172',  # ⚠️ АВТОМАТИЧЕСКИ СИНХРОНИЗИРУЕТСЯ
                'port': 50051,
                'use_ssl': False,
                'timeout': 120,
                'retry_attempts': 5,
                'retry_delay': 2.0
            }
        },
        'auto_fallback': True,
        'health_check_interval': 30,
        'connection_timeout': 10,
        'max_retry_attempts': 3,
        'retry_strategy': 'exponential',
        'circuit_breaker_threshold': 5,
        'circuit_breaker_timeout': 60
    }


def create_local_config() -> Dict[str, Any]:
    """Создает конфигурацию для локальной разработки"""
    return {
        'servers': {
            'local': {
                'address': '127.0.0.1',
                'port': 50051,
                'use_ssl': False,
                'timeout': 30,
                'retry_attempts': 3,
                'retry_delay': 1.0
            }
        },
        'auto_fallback': False,
        'health_check_interval': 10,
        'connection_timeout': 5,
        'max_retry_attempts': 2,
        'retry_strategy': 'linear',
        'circuit_breaker_threshold': 3,
        'circuit_breaker_timeout': 30
    }


def create_production_config() -> Dict[str, Any]:
    """Создает конфигурацию для production"""
    return {
        'servers': {
            'production': {
                'address': '20.151.51.172',  # ⚠️ АВТОМАТИЧЕСКИ СИНХРОНИЗИРУЕТСЯ
                'port': 50051,
                'use_ssl': False,
                'timeout': 120,
                'retry_attempts': 5,
                'retry_delay': 2.0
            }
        },
        'auto_fallback': True,
        'health_check_interval': 60,
        'connection_timeout': 30,
        'max_retry_attempts': 5,
        'retry_strategy': 'exponential',
        'circuit_breaker_threshold': 5,
        'circuit_breaker_timeout': 120
    }


def create_test_config() -> Dict[str, Any]:
    """Создает конфигурацию для тестирования"""
    return {
        'servers': {
            'test': {
                'address': '127.0.0.1',
                'port': 50052,
                'use_ssl': False,
                'timeout': 5,
                'retry_attempts': 1,
                'retry_delay': 0.5
            }
        },
        'auto_fallback': False,
        'health_check_interval': 5,
        'connection_timeout': 2,
        'max_retry_attempts': 1,
        'retry_strategy': 'none',
        'circuit_breaker_threshold': 1,
        'circuit_breaker_timeout': 10
    }
