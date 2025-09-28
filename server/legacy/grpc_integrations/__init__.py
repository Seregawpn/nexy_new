"""
Интеграции для gRPC Service Module
"""

from .text_processing_integration import TextProcessingIntegration
from .audio_generation_integration import AudioGenerationIntegration
from .session_management_integration import SessionManagementIntegration
from .database_integration import DatabaseIntegration
from .memory_management_integration import MemoryManagementIntegration

__all__ = [
    'TextProcessingIntegration',
    'AudioGenerationIntegration', 
    'SessionManagementIntegration',
    'DatabaseIntegration',
    'MemoryManagementIntegration'
]



