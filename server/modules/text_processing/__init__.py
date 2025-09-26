"""
Text Processing Module - Обработка текста с использованием AI

Модуль предоставляет функциональность для:
- Обработки текстовых запросов через Gemini Live API
- Fallback на LangChain + Google Gemini
- Универсальный интерфейс для всех провайдеров
- Система fallback для надежности

Совместим с существующим text_processor.py
"""

from .core.text_processor import TextProcessor
from .config import TextProcessingConfig

__all__ = ['TextProcessor', 'TextProcessingConfig']
__version__ = '1.0.0'
