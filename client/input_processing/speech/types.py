"""
Типы данных для обработки речи
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class SpeechState(Enum):
    """Состояния распознавания речи"""
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"

class SpeechEventType(Enum):
    """Типы событий речи"""
    RECORDING_START = "recording_start"
    RECORDING_STOP = "recording_stop"
    TEXT_RECOGNIZED = "text_recognized"
    ERROR_OCCURRED = "error_occurred"
    STATE_CHANGED = "state_changed"

@dataclass
class SpeechEvent:
    """Событие речи"""
    event_type: SpeechEventType
    state: SpeechState
    timestamp: float
    text: Optional[str] = None
    confidence: Optional[float] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

@dataclass
class SpeechConfig:
    """Конфигурация распознавания речи"""
    sample_rate: int = 16000
    chunk_size: int = 1024
    channels: int = 1
    dtype: str = 'int16'
    energy_threshold: int = 100
    dynamic_energy_threshold: bool = True
    pause_threshold: float = 0.5
    phrase_threshold: float = 0.3
    non_speaking_duration: float = 0.3
    max_duration: float = 30.0
    auto_start: bool = True
