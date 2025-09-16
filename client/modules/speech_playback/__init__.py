"""
Speech Playback Module - Модуль воспроизведения речи

ОСНОВНЫЕ ПРИНЦИПЫ:
1. Последовательное воспроизведение - один чанк за раз
2. Без лимитов размера - накопление всех данных
3. Thread-safety - безопасная работа в многопоточной среде
4. macOS совместимость - для PKG упаковки
5. Простота и надежность - минимальная сложность

АРХИТЕКТУРА:
- core/ - основные компоненты плеера
- utils/ - утилиты для работы с аудио
- macos/ - macOS-специфичные компоненты
- tests/ - тесты модуля
"""

from .core.player import SequentialSpeechPlayer, PlayerConfig
from .core.buffer import ChunkBuffer, ChunkInfo
from .core.state import PlaybackState, ChunkState
from .utils.audio_utils import resample_audio, convert_channels
from .utils.device_utils import get_best_audio_device
from .macos.core_audio import CoreAudioManager
from .macos.security import SecurityManager
from .macos.performance import PerformanceMonitor

__version__ = "1.0.0"
__author__ = "Nexy AI Voice Assistant Team"

# Экспорт основных классов
__all__ = [
    'SequentialSpeechPlayer',
    'PlayerConfig',
    'ChunkBuffer',
    'ChunkInfo',
    'PlaybackState',
    'ChunkState',
    'resample_audio',
    'convert_channels',
    'get_best_audio_device',
    'CoreAudioManager',
    'SecurityManager',
    'PerformanceMonitor'
]

# Глобальный экземпляр плеера
_global_player = None

def get_global_speech_player():
    """Получить глобальный экземпляр плеера"""
    global _global_player
    if _global_player is None:
        _global_player = SequentialSpeechPlayer()
    return _global_player

def initialize_speech_playback():
    """Инициализация модуля воспроизведения речи"""
    global _global_player
    if _global_player is None:
        _global_player = SequentialSpeechPlayer()
        _global_player.initialize()
    return _global_player

def shutdown_speech_playback():
    """Завершение работы модуля воспроизведения речи"""
    global _global_player
    if _global_player is not None:
        _global_player.shutdown()
        _global_player = None











































