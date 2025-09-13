"""
Mode Management - Модуль управления режимами
"""

from .core.mode_controller import ModeController
from .core.types import (
    AppMode, ModeTransition, ModeTransitionType, ModeStatus, ModeEvent,
    ModeConfig, ModeMetrics
)
from .modes.speaking_mode import SpeakingMode
from .modes.recording_mode import RecordingMode

__all__ = [
    'ModeController',
    'AppMode',
    'ModeTransition',
    'ModeTransitionType',
    'ModeStatus',
    'ModeEvent',
    'ModeConfig',
    'ModeMetrics',
    'SpeakingMode',
    'RecordingMode'
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
