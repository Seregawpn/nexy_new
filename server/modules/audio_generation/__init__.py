"""
Audio Generation Module - Генерация аудио

Модуль предоставляет функциональность для:
- Генерации аудио через Azure Cognitive Services Speech
- Конвертации текста в речь (TTS)
- Обработки аудио потоков
- Поддержки различных форматов аудио

Совместим с существующим audio_generator.py
"""

from .core.audio_processor import AudioProcessor
from .config import AudioGenerationConfig

__all__ = ['AudioProcessor', 'AudioGenerationConfig']
__version__ = '1.0.0'
