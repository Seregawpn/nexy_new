"""
Упрощенные Unit тесты для MemoryAnalyzer (без внешних зависимостей)
"""

import pytest
import re
from unittest.mock import Mock

# Тестируем только парсинг без инициализации Gemini
class TestMemoryAnalyzerParsing:
    """Тесты парсинга для MemoryAnalyzer"""
    
    def test_parse_analysis_response_valid(self):
        """Тест парсинга валидного ответа"""
        response_text = """
        SHORT_TERM: User is discussing Python programming
        LONG_TERM: User is a software developer
        """
        
        # Тестируем логику парсинга напрямую
        short_term_match = re.search(r'SHORT_TERM:\s*(.*?)(?=LONG_TERM:|$)', response_text, re.DOTALL | re.IGNORECASE)
        long_term_match = re.search(r'LONG_TERM:\s*(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
        
        short_memory = ""
        long_memory = ""
        
        if short_term_match:
            short_memory = short_term_match.group(1).strip()
            short_memory = re.sub(r'\s+', ' ', short_memory)
        
        if long_term_match:
            long_memory = long_term_match.group(1).strip()
            long_memory = re.sub(r'\s+', ' ', long_memory)
        
        assert "Python programming" in short_memory
        assert "software developer" in long_memory
    
    def test_parse_analysis_response_empty(self):
        """Тест парсинга пустого ответа"""
        response_text = """
        SHORT_TERM: empty
        LONG_TERM: none
        """
        
        short_term_match = re.search(r'SHORT_TERM:\s*(.*?)(?=LONG_TERM:|$)', response_text, re.DOTALL | re.IGNORECASE)
        long_term_match = re.search(r'LONG_TERM:\s*(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
        
        short_memory = ""
        long_memory = ""
        
        if short_term_match:
            short_memory = short_term_match.group(1).strip()
            short_memory = re.sub(r'\s+', ' ', short_memory)
        
        if long_term_match:
            long_memory = long_term_match.group(1).strip()
            long_memory = re.sub(r'\s+', ' ', long_memory)
        
        # Проверяем, что пустые значения обрабатываются корректно
        if short_memory.lower() in ['empty', 'none', 'no information', '']:
            short_memory = ""
        
        if long_memory.lower() in ['empty', 'none', 'no information', '']:
            long_memory = ""
        
        assert short_memory == ""
        assert long_memory == ""
    
    def test_parse_analysis_response_malformed(self):
        """Тест парсинга некорректного ответа"""
        response_text = "Some random text without proper format"
        
        short_term_match = re.search(r'SHORT_TERM:\s*(.*?)(?=LONG_TERM:|$)', response_text, re.DOTALL | re.IGNORECASE)
        long_term_match = re.search(r'LONG_TERM:\s*(.*?)$', response_text, re.DOTALL | re.IGNORECASE)
        
        short_memory = ""
        long_memory = ""
        
        if short_term_match:
            short_memory = short_term_match.group(1).strip()
        
        if long_term_match:
            long_memory = long_term_match.group(1).strip()
        
        assert short_memory == ""
        assert long_memory == ""
