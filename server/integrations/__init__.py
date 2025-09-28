"""
Интеграции для взаимодействия между модулями
"""

from .grpc_integrations import (
    TextProcessingIntegration,
    AudioGenerationIntegration,
    SessionManagementIntegration,
    DatabaseIntegration,
    MemoryManagementIntegration
)

__all__ = [
    'TextProcessingIntegration',
    'AudioGenerationIntegration', 
    'SessionManagementIntegration',
    'DatabaseIntegration',
    'MemoryManagementIntegration'
]



