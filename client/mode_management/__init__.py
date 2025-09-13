"""
Mode Management - Модуль управления режимами
"""

from .core.mode_controller import ModeController
from .core.types import (
    AppMode, ModeTransition, ModeTransitionType, ModeStatus, ModeEvent,
    ModeConfig, ModeMetrics
)
from .modes.sleeping_mode import SleepingMode
from .modes.processing_mode import ProcessingMode
from .modes.listening_mode import ListeningMode

__all__ = [
    'ModeController',
    'AppMode',
    'ModeTransition',
    'ModeTransitionType',
    'ModeStatus',
    'ModeEvent',
    'ModeConfig',
    'ModeMetrics',
    'SleepingMode',
    'ProcessingMode',
    'ListeningMode'
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
