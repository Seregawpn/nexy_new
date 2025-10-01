"""
Конфигурация для Memory Management Module
Использует централизованную конфигурацию
"""

from typing import Dict, Any

from config.unified_config import get_config

class MemoryConfig:
    """Конфигурация модуля управления памятью"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Инициализация конфигурации из централизованной системы
        
        Args:
            config: Словарь с конфигурацией (опционально, переопределяет централизованную)
        """
        # Получаем централизованную конфигурацию
        unified_config = get_config()
        self.config = config or {}
        
        # Используем централизованные настройки с возможностью переопределения
        self.gemini_api_key = self.config.get('gemini_api_key', unified_config.memory.gemini_api_key)
        self.max_short_term_memory_size = self.config.get('max_short_term_memory_size', unified_config.memory.max_short_term_memory_size)
        self.max_long_term_memory_size = self.config.get('max_long_term_memory_size', unified_config.memory.max_long_term_memory_size)
        self.memory_timeout = self.config.get('memory_timeout', unified_config.memory.memory_timeout)
        self.analysis_timeout = self.config.get('analysis_timeout', unified_config.memory.analysis_timeout)
        
        # Настройки анализа памяти
        self.memory_analysis_model = self.config.get('memory_analysis_model', unified_config.memory.memory_analysis_model)
        self.memory_analysis_temperature = self.config.get('memory_analysis_temperature', unified_config.memory.memory_analysis_temperature)
        
        # Промпты для анализа памяти
        self.memory_analysis_prompt = """
        Analyze this conversation between user and AI assistant to extract memory information.
        
        USER INPUT: {prompt}
        AI RESPONSE: {response}
        
        Extract and categorize information into:
        
        1. SHORT-TERM MEMORY (current conversation context):
           - Current topic being discussed
           - Recent context that helps understand the conversation flow
           - Temporary information relevant to this session
           - Keep it concise and relevant
        
        2. LONG-TERM MEMORY (important user information):
           - User's name, preferences, important details
           - Significant facts about the user
           - Important relationships or context
           - Information worth remembering for future conversations
           - Only include truly important information
        
        Rules:
        - If no important information is found, return empty strings
        - Keep memories concise and factual
        - Don't include generic information
        - Focus on what would be useful for future conversations
        - Separate short-term and long-term clearly
        
        Return in this format:
        SHORT_TERM: [extracted short-term memory or empty]
        LONG_TERM: [extracted long-term memory or empty]
        """
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Возвращает конфигурацию в виде словаря"""
        return {
            'GEMINI_API_KEY': self.gemini_api_key,
            'MAX_SHORT_TERM_MEMORY_SIZE': self.max_short_term_memory_size,
            'MAX_LONG_TERM_MEMORY_SIZE': self.max_long_term_memory_size,
            'MEMORY_TIMEOUT': self.memory_timeout,
            'ANALYSIS_TIMEOUT': self.analysis_timeout,
            'MEMORY_ANALYSIS_MODEL': self.memory_analysis_model,
            'MEMORY_ANALYSIS_TEMPERATURE': self.memory_analysis_temperature,
            'MEMORY_ANALYSIS_PROMPT': self.memory_analysis_prompt
        }
    
    def validate_config(self) -> bool:
        """Проверяет корректность конфигурации"""
        if not self.gemini_api_key:
            print("⚠️ GEMINI_API_KEY не установлен")
            return False
        
        if self.memory_timeout <= 0 or self.analysis_timeout <= 0:
            print("❌ memory_timeout и analysis_timeout должны быть больше 0")
            return False
            
        if self.max_short_term_memory_size <= 0 or self.max_long_term_memory_size <= 0:
            print("❌ max_short_term_memory_size и max_long_term_memory_size должны быть больше 0")
            return False
            
        return True
