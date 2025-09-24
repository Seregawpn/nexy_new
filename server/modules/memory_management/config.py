"""
Конфигурация для Memory Management Module
"""

import os
from typing import Dict, Any

class MemoryConfig:
    """Конфигурация модуля управления памятью"""
    
    def __init__(self):
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        self.max_short_term_memory_size = 10240  # 10KB
        self.max_long_term_memory_size = 10240   # 10KB
        self.memory_timeout = 2.0  # секунды на получение памяти
        self.analysis_timeout = 5.0  # секунды на анализ диалога
        
        # Настройки анализа памяти
        self.memory_analysis_model = "gemini-1.5-flash"
        self.memory_analysis_temperature = 0.3
        
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
            return False
        
        if self.memory_timeout <= 0 or self.analysis_timeout <= 0:
            return False
            
        if self.max_short_term_memory_size <= 0 or self.max_long_term_memory_size <= 0:
            return False
            
        return True
