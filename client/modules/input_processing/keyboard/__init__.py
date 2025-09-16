"""
Keyboard module - обработка клавиатуры
"""

from .keyboard_monitor import KeyboardMonitor
from .types import KeyEvent, KeyEventType, KeyType, KeyboardConfig

__all__ = [
    'KeyboardMonitor',
    'KeyEvent',
    'KeyEventType',
    'KeyType',
    'KeyboardConfig'
]
