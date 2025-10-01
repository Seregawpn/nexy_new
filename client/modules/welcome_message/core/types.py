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
    audio_file: str = "assets/audio/welcome_en.mp3"
    fallback_to_tts: bool = True
    delay_sec: float = 1.0
    volume: float = 0.8
    voice: str = "en-US-JennyNeural"
    sample_rate: int = 48000
    channels: int = 1
    bit_depth: int = 16
    
    def get_audio_path(self, base_path: Optional[Path] = None) -> Path:
        """Получить полный путь к аудио файлу"""
        if base_path is None:
            base_path = self._find_base_path()
        return base_path / self.audio_file
    
    def _find_base_path(self) -> Path:
        """Найти базовый путь к ресурсам с учетом PyInstaller"""
        import logging
        import sys
        
        logger = logging.getLogger(__name__)
        
        # 1. PyInstaller onefile/onedir: данные распакованы рядом с исполняемым файлом
        if hasattr(sys, "_MEIPASS"):
            candidate = Path(sys._MEIPASS)
            audio_path = candidate / self.audio_file
            logger.info(f"🔍 [WELCOME_CONFIG] Проверяю PyInstaller _MEIPASS: {audio_path}")
            if audio_path.exists():
                logger.info(f"✅ [WELCOME_CONFIG] Найден аудио файл в _MEIPASS: {audio_path}")
                return candidate
            
            # Частый случай: ресурсы лежат в подкаталоге Resources
            resources_candidate = candidate / "Resources"
            audio_path = resources_candidate / self.audio_file
            logger.info(f"🔍 [WELCOME_CONFIG] Проверяю _MEIPASS/Resources: {audio_path}")
            if audio_path.exists():
                logger.info(f"✅ [WELCOME_CONFIG] Найден аудио файл в _MEIPASS/Resources: {audio_path}")
                return resources_candidate
        
        # 2. PyInstaller bundle (.app): ищем каталог MacOS -> Contents -> Resources
        resolved_path = Path(__file__).resolve()
        macos_dir = None
        for parent in resolved_path.parents:
            if parent.name == "MacOS":
                macos_dir = parent
                break
        
        if macos_dir is not None:
            contents_dir = macos_dir.parent  # MacOS -> Contents
            resources_path = contents_dir / "Resources"  # Contents -> Resources
            audio_path = resources_path / self.audio_file
            logger.info(f"🔍 [WELCOME_CONFIG] Проверяю bundle Resources: {audio_path}")
            if audio_path.exists():
                logger.info(f"✅ [WELCOME_CONFIG] Найден аудио файл в bundle: {audio_path}")
                return resources_path
        
        # 3. Dev-режим (репозиторий)
        dev_path = Path(__file__).parent.parent.parent.parent
        audio_path = dev_path / self.audio_file
        logger.info(f"🔍 [WELCOME_CONFIG] Проверяю dev-режим: {audio_path}")
        if audio_path.exists():
            logger.info(f"✅ [WELCOME_CONFIG] Найден аудио файл в dev-режиме: {audio_path}")
            return dev_path
        
        # 4. Fallback - возвращаем dev путь даже если файла нет
        logger.warning(f"⚠️ [WELCOME_CONFIG] Аудио файл не найден, используем fallback: {audio_path}")
        return dev_path


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
