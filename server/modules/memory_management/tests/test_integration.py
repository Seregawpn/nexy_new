"""
Integration тесты для Memory Management Module
"""

import pytest
import asyncio
from unittest.mock import Mock, patch

from modules.memory_management.core.memory_manager import MemoryManager
from modules.memory_management.providers.memory_analyzer import MemoryAnalyzer


class TestMemoryManagementIntegration:
    """Integration тесты для Memory Management Module"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.db_manager = Mock()
        self.manager = None
        self.analyzer = None
    
    @patch('modules.memory_management.core.memory_manager.MemoryAnalyzer')
    def test_full_integration_flow(self, mock_memory_analyzer):
        """Тест полного flow интеграции"""
        # Настройка моков
        mock_analyzer_instance = Mock()
        mock_analyzer_instance.analyze_conversation = Mock()
        mock_memory_analyzer.return_value = mock_analyzer_instance
        
        # Инициализация
        manager = MemoryManager(self.db_manager)
        
        # Проверка инициализации
        assert manager.db_manager == self.db_manager
        assert manager.memory_analyzer == mock_analyzer_instance
        assert manager.is_available() is True
    
    @pytest.mark.asyncio
    async def test_memory_context_integration(self):
        """Тест интеграции получения контекста памяти"""
        # Настройка моков
        memory_data = {
            'short': 'Current conversation about Python programming',
            'long': 'User is a software developer working with Python'
        }
        
        self.db_manager.get_user_memory.return_value = memory_data
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert "MEMORY CONTEXT" in context
        assert "SHORT-TERM MEMORY" in context
        assert "LONG-TERM MEMORY" in context
        assert "Python programming" in context
        assert "software developer" in context
        assert "MEMORY USAGE INSTRUCTIONS" in context
        
        # Проверка вызова БД
        self.db_manager.get_user_memory.assert_called_once_with("test_hardware_id")
    
    @pytest.mark.asyncio
    async def test_memory_analysis_integration(self):
        """Тест интеграции анализа памяти"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = Mock(return_value=("short_memory", "long_memory"))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста
        short_memory, long_memory = await manager.analyze_conversation("prompt", "response")
        
        # Проверки
        assert short_memory == "short_memory"
        assert long_memory == "long_memory"
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
    
    @pytest.mark.asyncio
    async def test_memory_update_integration(self):
        """Тест интеграции обновления памяти"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = Mock(return_value=("short_memory", "long_memory"))
        
        self.db_manager.update_user_memory.return_value = True
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста
        await manager.update_memory_background("hardware_id", "prompt", "response")
        
        # Проверки
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
        self.db_manager.update_user_memory.assert_called_once_with("hardware_id", "short_memory", "long_memory")
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self):
        """Тест интеграции обработки ошибок"""
        # Настройка моков с ошибками
        self.db_manager.get_user_memory.side_effect = Exception("DB Error")
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert context == ""  # Должен вернуть пустую строку при ошибке
    
    @pytest.mark.asyncio
    async def test_timeout_handling_integration(self):
        """Тест интеграции обработки таймаутов"""
        # Настройка моков с таймаутом
        self.db_manager.get_user_memory.side_effect = asyncio.TimeoutError()
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert context == ""  # Должен вернуть пустую строку при таймауте
    
    def test_configuration_integration(self):
        """Тест интеграции конфигурации"""
        manager = MemoryManager(self.db_manager)
        
        # Проверка конфигурации
        config = manager.config
        assert config.memory_timeout == 2.0
        assert config.analysis_timeout == 5.0
        assert config.max_short_term_memory_size == 10240
        assert config.max_long_term_memory_size == 10240
        assert config.memory_analysis_model == "gemini-1.5-flash"
        assert config.memory_analysis_temperature == 0.3
    
    @pytest.mark.asyncio
    async def test_cleanup_integration(self):
        """Тест интеграции очистки памяти"""
        # Настройка моков
        self.db_manager.cleanup_expired_short_term_memory.return_value = 3
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        result = await manager.cleanup_expired_memory(24)
        
        # Проверки
        assert result == 3
        self.db_manager.cleanup_expired_short_term_memory.assert_called_once_with(24)
    
    @pytest.mark.asyncio
    async def test_availability_integration(self):
        """Тест интеграции проверки доступности"""
        # Тест с полной доступностью
        mock_analyzer = Mock()
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        assert manager.is_available() is True
        
        # Тест без анализатора
        manager.memory_analyzer = None
        assert manager.is_available() is False
        
        # Тест без БД
        manager.memory_analyzer = mock_analyzer
        manager.db_manager = None
        assert manager.is_available() is False
    
    @pytest.mark.asyncio
    async def test_real_world_scenario(self):
        """Тест реального сценария использования"""
        # Настройка моков для реалистичного сценария
        memory_data = {
            'short': 'User is asking about Python async programming',
            'long': 'User is a software developer learning Python'
        }
        
        self.db_manager.get_user_memory.return_value = memory_data
        self.db_manager.update_user_memory.return_value = True
        
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = Mock(return_value=(
            "User is working on async Python code",
            "User is a Python developer"
        ))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Сценарий: получение контекста памяти
        context = await manager.get_memory_context("user123")
        assert "Python async programming" in context
        assert "software developer" in context
        
        # Сценарий: анализ нового диалога
        short_memory, long_memory = await manager.analyze_conversation(
            "How do I use asyncio in Python?",
            "You can use asyncio to write asynchronous Python code..."
        )
        assert "async Python code" in short_memory
        assert "Python developer" in long_memory
        
        # Сценарий: обновление памяти
        await manager.update_memory_background(
            "user123",
            "How do I use asyncio in Python?",
            "You can use asyncio to write asynchronous Python code..."
        )
        
        # Проверка вызовов
        self.db_manager.get_user_memory.assert_called_with("user123")
        mock_analyzer.analyze_conversation.assert_called_with(
            "How do I use asyncio in Python?",
            "You can use asyncio to write asynchronous Python code..."
        )
        self.db_manager.update_user_memory.assert_called_with(
            "user123",
            "User is working on async Python code",
            "User is a Python developer"
        )
