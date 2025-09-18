"""
Типы данных для обработки клавиатуры
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class KeyEventType(Enum):
    """Типы событий клавиатуры"""
    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    SHORT_PRESS = "short_press"  # < 0.6s
    LONG_PRESS = "long_press"    # >= 0.6s

class KeyType(Enum):
    """Типы клавиш"""
    SPACE = "space"
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    ENTER = "enter"
    ESC = "esc"

@dataclass
class KeyEvent:
    """Событие клавиатуры"""
    key: str
    event_type: KeyEventType
    timestamp: float
    duration: Optional[float] = None
    data: Optional[Dict[str, Any]] = None

@dataclass
class KeyboardConfig:
    """Конфигурация клавиатуры"""
    key_to_monitor: str = "space"
    short_press_threshold: float = 0.6
    long_press_threshold: float = 1.0
    event_cooldown: float = 0.1
    hold_check_interval: float = 0.05
    debounce_time: float = 0.1
