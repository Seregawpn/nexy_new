"""
Types and data structures for Welcome Message Module
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path



class WelcomeState(Enum):
    """Состояния плеера приветствия"""
    IDLE = "idle"
    LOADING = "loading"
    PLAYING = "playing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class WelcomeConfig:
    """Конфигурация модуля приветствия"""
    enabled: bool = True
    text: str = "Hi! Nexy is here. How can I help you?"
    delay_sec: float = 1.0
    volume: float = 0.8
    voice: str = "en-US-JennyNeural"
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    use_server: bool = True
    server_timeout_sec: float = 30.0
    ignore_microphone_permission: bool = False
    


@dataclass
class WelcomeResult:
    """Результат воспроизведения приветствия"""
    success: bool
    method: str  # "server" | "none" | "error"
    duration_sec: float
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Конвертировать в словарь для EventBus"""
        return {
            "success": self.success,
            "method": self.method,
            "duration_sec": self.duration_sec,
            "error": self.error,
            "metadata": self.metadata or {}
        }
