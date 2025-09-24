"""
Unit тесты для MemoryAnalyzer
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from modules.memory_management.providers.memory_analyzer import MemoryAnalyzer


class TestMemoryAnalyzer:
    """Тесты для MemoryAnalyzer"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.api_key = "test_api_key"
        self.analyzer = None
    
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    def test_init_success(self, mock_genai):
        """Тест успешной инициализации"""
        mock_genai.configure = Mock()
        
        analyzer = MemoryAnalyzer(self.api_key)
        
        assert analyzer.api_key == self.api_key
        assert analyzer.model_name == "gemini-1.5-flash"
        assert analyzer.temperature == 0.3
        mock_genai.configure.assert_called_once_with(api_key=self.api_key)
    
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    def test_init_without_gemini(self, mock_genai):
        """Тест инициализации без Gemini"""
        with patch('modules.memory_management.providers.memory_analyzer.GEMINI_AVAILABLE', False):
            with pytest.raises(ImportError, match="google.generativeai not available"):
                MemoryAnalyzer(self.api_key)
    
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    def test_is_available(self, mock_genai):
        """Тест проверки доступности"""
        analyzer = MemoryAnalyzer(self.api_key)
        assert analyzer.is_available() is True
    
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    def test_is_available_no_api_key(self, mock_genai):
        """Тест проверки доступности без API ключа"""
        analyzer = MemoryAnalyzer(self.api_key)
        analyzer.api_key = None
        assert analyzer.is_available() is False
    
    @pytest.mark.asyncio
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    @patch('modules.memory_management.providers.memory_analyzer.asyncio.to_thread')
    async def test_analyze_conversation_success(self, mock_to_thread, mock_genai):
        """Тест успешного анализа диалога"""
        # Настройка моков
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        mock_response = Mock()
        mock_response.text = """
        SHORT_TERM: User is asking about Python programming and needs help with async/await
        LONG_TERM: User is a beginner programmer learning Python
        """
        
        mock_to_thread.return_value = mock_response
        
        analyzer = MemoryAnalyzer(self.api_key)
        
        # Выполнение теста
        short_memory, long_memory = await analyzer.analyze_conversation(
            "How do I use async/await in Python?",
            "Async/await in Python allows you to write asynchronous code..."
        )
        
        # Проверки
        assert "Python programming" in short_memory
        assert "beginner programmer" in long_memory
        mock_to_thread.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    @patch('modules.memory_management.providers.memory_analyzer.asyncio.to_thread')
    async def test_analyze_conversation_empty_response(self, mock_to_thread, mock_genai):
        """Тест анализа диалога с пустым ответом"""
        # Настройка моков
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        mock_response = Mock()
        mock_response.text = None
        
        mock_to_thread.return_value = mock_response
        
        analyzer = MemoryAnalyzer(self.api_key)
        
        # Выполнение теста
        short_memory, long_memory = await analyzer.analyze_conversation(
            "Hello",
            "Hi there!"
        )
        
        # Проверки
        assert short_memory == ""
        assert long_memory == ""
    
    @pytest.mark.asyncio
    @patch('modules.memory_management.providers.memory_analyzer.genai')
    @patch('modules.memory_management.providers.memory_analyzer.asyncio.to_thread')
    async def test_analyze_conversation_error(self, mock_to_thread, mock_genai):
        """Тест анализа диалога с ошибкой"""
        # Настройка моков
        mock_model = Mock()
        mock_genai.GenerativeModel.return_value = mock_model
        
        mock_to_thread.side_effect = Exception("API Error")
        
        analyzer = MemoryAnalyzer(self.api_key)
        
        # Выполнение теста
        short_memory, long_memory = await analyzer.analyze_conversation(
            "Hello",
            "Hi there!"
        )
        
        # Проверки
        assert short_memory == ""
        assert long_memory == ""
    
    def test_parse_analysis_response_valid(self):
        """Тест парсинга валидного ответа"""
        # Создаем mock анализатор без инициализации Gemini
        analyzer = Mock()
        analyzer._parse_analysis_response = MemoryAnalyzer._parse_analysis_response.__get__(analyzer, Mock)
        
        response_text = """
        SHORT_TERM: User is discussing Python programming
        LONG_TERM: User is a software developer
        """
        
        short_memory, long_memory = analyzer._parse_analysis_response(response_text)
        
        assert "Python programming" in short_memory
        assert "software developer" in long_memory
    
    def test_parse_analysis_response_empty(self):
        """Тест парсинга пустого ответа"""
        analyzer = MemoryAnalyzer(self.api_key)
        
        response_text = """
        SHORT_TERM: empty
        LONG_TERM: none
        """
        
        short_memory, long_memory = analyzer._parse_analysis_response(response_text)
        
        assert short_memory == ""
        assert long_memory == ""
    
    def test_parse_analysis_response_malformed(self):
        """Тест парсинга некорректного ответа"""
        analyzer = MemoryAnalyzer(self.api_key)
        
        response_text = "Some random text without proper format"
        
        short_memory, long_memory = analyzer._parse_analysis_response(response_text)
        
        assert short_memory == ""
        assert long_memory == ""
