"""
Unit тесты для MemoryManager
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from modules.memory_management.core.memory_manager import MemoryManager


class TestMemoryManager:
    """Тесты для MemoryManager"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.db_manager = Mock()
        self.memory_manager = None
    
    @patch('modules.memory_management.core.memory_manager.MemoryAnalyzer')
    def test_init_success(self, mock_memory_analyzer):
        """Тест успешной инициализации"""
        mock_analyzer = Mock()
        mock_memory_analyzer.return_value = mock_analyzer
        
        manager = MemoryManager(self.db_manager)
        
        assert manager.db_manager == self.db_manager
        assert manager.memory_analyzer == mock_analyzer
        assert manager.config.gemini_api_key is not None
    
    @patch('modules.memory_management.core.memory_manager.MemoryAnalyzer')
    def test_init_no_api_key(self, mock_memory_analyzer):
        """Тест инициализации без API ключа"""
        with patch.dict('os.environ', {}, clear=True):
            manager = MemoryManager(self.db_manager)
            
            assert manager.db_manager == self.db_manager
            assert manager.memory_analyzer is None
    
    @patch('modules.memory_management.core.memory_manager.MemoryAnalyzer')
    def test_set_database_manager(self, mock_memory_analyzer):
        """Тест установки DatabaseManager"""
        manager = MemoryManager()
        
        new_db_manager = Mock()
        manager.set_database_manager(new_db_manager)
        
        assert manager.db_manager == new_db_manager
    
    @pytest.mark.asyncio
    async def test_get_memory_context_success(self):
        """Тест успешного получения контекста памяти"""
        # Настройка моков
        memory_data = {
            'short': 'Current conversation about Python',
            'long': 'User is a software developer'
        }
        
        self.db_manager.get_user_memory.return_value = memory_data
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert "Current conversation about Python" in context
        assert "User is a software developer" in context
        assert "MEMORY CONTEXT" in context
        self.db_manager.get_user_memory.assert_called_once_with("test_hardware_id")
    
    @pytest.mark.asyncio
    async def test_get_memory_context_no_memory(self):
        """Тест получения контекста без памяти"""
        # Настройка моков
        memory_data = {'short': '', 'long': ''}
        self.db_manager.get_user_memory.return_value = memory_data
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_get_memory_context_no_hardware_id(self):
        """Тест получения контекста без hardware_id"""
        manager = MemoryManager(self.db_manager)
        
        context = await manager.get_memory_context("")
        
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_get_memory_context_no_db_manager(self):
        """Тест получения контекста без db_manager"""
        manager = MemoryManager()
        
        context = await manager.get_memory_context("test_hardware_id")
        
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_get_memory_context_timeout(self):
        """Тест получения контекста с таймаутом"""
        # Настройка моков
        self.db_manager.get_user_memory.side_effect = asyncio.TimeoutError()
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_get_memory_context_error(self):
        """Тест получения контекста с ошибкой"""
        # Настройка моков
        self.db_manager.get_user_memory.side_effect = Exception("DB Error")
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        context = await manager.get_memory_context("test_hardware_id")
        
        # Проверки
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_analyze_conversation_success(self):
        """Тест успешного анализа диалога"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = AsyncMock(return_value=("short", "long"))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста
        short_memory, long_memory = await manager.analyze_conversation("prompt", "response")
        
        # Проверки
        assert short_memory == "short"
        assert long_memory == "long"
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
    
    @pytest.mark.asyncio
    async def test_analyze_conversation_no_analyzer(self):
        """Тест анализа диалога без анализатора"""
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = None
        
        # Выполнение теста
        short_memory, long_memory = await manager.analyze_conversation("prompt", "response")
        
        # Проверки
        assert short_memory == ""
        assert long_memory == ""
    
    @pytest.mark.asyncio
    async def test_analyze_conversation_error(self):
        """Тест анализа диалога с ошибкой"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = AsyncMock(side_effect=Exception("Analysis Error"))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста
        short_memory, long_memory = await manager.analyze_conversation("prompt", "response")
        
        # Проверки
        assert short_memory == ""
        assert long_memory == ""
    
    @pytest.mark.asyncio
    async def test_update_memory_background_success(self):
        """Тест успешного фонового обновления памяти"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = AsyncMock(return_value=("short", "long"))
        
        self.db_manager.update_user_memory.return_value = True
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста
        await manager.update_memory_background("hardware_id", "prompt", "response")
        
        # Проверки
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
        self.db_manager.update_user_memory.assert_called_once_with("hardware_id", "short", "long")
    
    @pytest.mark.asyncio
    async def test_update_memory_background_no_memory(self):
        """Тест фонового обновления без памяти"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = AsyncMock(return_value=("", ""))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста
        await manager.update_memory_background("hardware_id", "prompt", "response")
        
        # Проверки
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
        self.db_manager.update_user_memory.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_update_memory_background_error(self):
        """Тест фонового обновления с ошибкой"""
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = AsyncMock(side_effect=Exception("Analysis Error"))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        # Выполнение теста (не должно поднимать исключение)
        await manager.update_memory_background("hardware_id", "prompt", "response")
        
        # Проверки
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
        self.db_manager.update_user_memory.assert_not_called()
    
    def test_is_available_true(self):
        """Тест проверки доступности - доступен"""
        mock_analyzer = Mock()
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        assert manager.is_available() is True
    
    def test_is_available_false_no_analyzer(self):
        """Тест проверки доступности - нет анализатора"""
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = None
        
        assert manager.is_available() is False
    
    def test_is_available_false_no_db(self):
        """Тест проверки доступности - нет БД"""
        mock_analyzer = Mock()
        
        manager = MemoryManager()
        manager.memory_analyzer = mock_analyzer
        
        assert manager.is_available() is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory_success(self):
        """Тест успешной очистки устаревшей памяти"""
        # Настройка моков
        self.db_manager.cleanup_expired_short_term_memory.return_value = 5
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        result = await manager.cleanup_expired_memory(24)
        
        # Проверки
        assert result == 5
        self.db_manager.cleanup_expired_short_term_memory.assert_called_once_with(24)
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory_no_db(self):
        """Тест очистки устаревшей памяти без БД"""
        manager = MemoryManager()
        
        # Выполнение теста
        result = await manager.cleanup_expired_memory(24)
        
        # Проверки
        assert result == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory_error(self):
        """Тест очистки устаревшей памяти с ошибкой"""
        # Настройка моков
        self.db_manager.cleanup_expired_short_term_memory.side_effect = Exception("DB Error")
        
        manager = MemoryManager(self.db_manager)
        
        # Выполнение теста
        result = await manager.cleanup_expired_memory(24)
        
        # Проверки
        assert result == 0
