"""
Memory Management Module для Nexy AI Assistant

Модуль управления памятью пользователей с поддержкой:
- Анализа диалогов для извлечения краткосрочной и долгосрочной памяти
- Формирования контекста памяти для LLM
- Фонового обновления памяти после генерации ответов
- Интеграции с Database Module

Архитектура:
- MemoryAnalyzer: анализ диалогов через Gemini API
- MemoryManager: координация всех операций с памятью
- Интеграция с существующим TextProcessor без изменения логики
"""

from .core.memory_manager import MemoryManager
from .providers.memory_analyzer import MemoryAnalyzer

__all__ = [
    'MemoryManager',
    'MemoryAnalyzer'
]
