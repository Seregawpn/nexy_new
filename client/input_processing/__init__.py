"""
Input Processing - Модуль обработки ввода
Объединяет обработку клавиатуры и речи
"""

from .keyboard.keyboard_monitor import KeyboardMonitor
from .keyboard.types import KeyEvent, KeyEventType, KeyboardConfig
from .speech.speech_recognizer import SpeechRecognizer
from .speech.types import SpeechEvent, SpeechEventType, SpeechState, SpeechConfig
from .config.input_config import InputConfig, DEFAULT_INPUT_CONFIG

__all__ = [
    'KeyboardMonitor',
    'KeyEvent',
    'KeyEventType', 
    'KeyboardConfig',
    'SpeechRecognizer',
    'SpeechEvent',
    'SpeechEventType',
    'SpeechState',
    'SpeechConfig',
    'InputConfig',
    'DEFAULT_INPUT_CONFIG'
]

__version__ = "1.0.0"
__author__ = "Nexy Team"
