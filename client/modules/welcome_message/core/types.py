"""
Types and data structures for Welcome Message Module
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from pathlib import Path

# Импортируем утилиту для определения путей к ресурсам
try:
    from modules.welcome_message.utils.resource_path import get_resource_path
except ImportError:
    # Fallback для случаев, когда импорт не работает
    def get_resource_path(relative_path: str, base_path: Optional[Path] = None) -> Path:
        if base_path is None:
            base_path = Path(__file__).parent.parent.parent.parent
        return base_path / relative_path


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
    audio_file: str = "assets/audio/welcome_en.mp3"
    fallback_to_tts: bool = True
    delay_sec: float = 1.0
    volume: float = 0.8
    voice: str = "en-US-JennyNeural"
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    
    def get_audio_path(self, base_path: Optional[Path] = None) -> Path:
        """
        Получить полный путь к аудио файлу.
        
        Автоматически определяет правильный путь для:
        - Development режима
        - PyInstaller onefile (.app onefile)
        - PyInstaller bundle (.app bundle)
        
        Args:
            base_path: Базовый путь (если None, определяется автоматически)
        
        Returns:
            Path: Полный путь к аудио файлу
        """
        return get_resource_path(self.audio_file, base_path)


@dataclass
class WelcomeResult:
    """Результат воспроизведения приветствия"""
    success: bool
    method: str  # "prerecorded" | "tts" | "fallback"
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
