"""
Text Processing Module - Обработка текста с использованием Live API

Модуль предоставляет функциональность для:
- Стриминговой обработки текстовых запросов через Gemini Live API
- Поддержки JPEG изображений
- Интеграции Google Search
- Универсального интерфейса для Live API провайдера

Реализован только со стриминговыми методами.
"""

from .core.text_processor import TextProcessor
from .config import TextProcessingConfig

__all__ = ['TextProcessor', 'TextProcessingConfig']
__version__ = '1.0.0'
