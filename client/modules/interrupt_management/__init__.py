"""
Interrupt Management - Модуль управления прерываниями
"""

from .core.interrupt_coordinator import InterruptCoordinator, InterruptDependencies
from .core.types import (
    InterruptEvent, InterruptType, InterruptPriority, InterruptStatus,
    InterruptConfig, InterruptMetrics
)
from .handlers.speech_interrupt import SpeechInterruptHandler
from .handlers.recording_interrupt import RecordingInterruptHandler
from .config.interrupt_config import InterruptModuleConfig, DEFAULT_INTERRUPT_CONFIG

__all__ = [
    'InterruptCoordinator',
    'InterruptDependencies',
    'InterruptEvent',
    'InterruptType',
    'InterruptPriority',
    'InterruptStatus',
    'InterruptConfig',
    'InterruptMetrics',
    'SpeechInterruptHandler',
    'RecordingInterruptHandler',
    'InterruptModuleConfig',
    'DEFAULT_INTERRUPT_CONFIG'
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
