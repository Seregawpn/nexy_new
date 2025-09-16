"""
macOS компоненты модуля hardware_id
"""

from .system_profiler import SystemProfilerBridge
from .hardware_detector import HardwareDetector

__all__ = [
    'SystemProfilerBridge',
    'HardwareDetector'
]
