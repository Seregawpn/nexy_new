"""
Упрощенные Unit тесты для MemoryManager (без внешних зависимостей)
"""

import pytest
import asyncio
from unittest.mock import Mock

# Тестируем только базовую логику без инициализации Gemini
class TestMemoryManagerSimple:
    """Упрощенные тесты для MemoryManager"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.db_manager = Mock()
    
    @pytest.mark.asyncio
    async def test_get_memory_context_no_hardware_id(self):
        """Тест получения контекста без hardware_id"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        manager = MemoryManager(self.db_manager)
        
        context = await manager.get_memory_context("")
        
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_get_memory_context_no_db_manager(self):
        """Тест получения контекста без db_manager"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        manager = MemoryManager()
        
        context = await manager.get_memory_context("test_hardware_id")
        
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_get_memory_context_error(self):
        """Тест получения контекста с ошибкой"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        # Настройка моков с ошибкой
        self.db_manager.get_user_memory.side_effect = Exception("DB Error")
        
        manager = MemoryManager(self.db_manager)
        
        context = await manager.get_memory_context("test_hardware_id")
        
        assert context == ""
    
    @pytest.mark.asyncio
    async def test_analyze_conversation_no_analyzer(self):
        """Тест анализа диалога без анализатора"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = None
        
        short_memory, long_memory = await manager.analyze_conversation("prompt", "response")
        
        assert short_memory == ""
        assert long_memory == ""
    
    @pytest.mark.asyncio
    async def test_update_memory_background_no_memory(self):
        """Тест фонового обновления без памяти"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        # Настройка моков
        mock_analyzer = Mock()
        mock_analyzer.analyze_conversation = Mock(return_value=("", ""))
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = mock_analyzer
        
        await manager.update_memory_background("hardware_id", "prompt", "response")
        
        mock_analyzer.analyze_conversation.assert_called_once_with("prompt", "response")
        self.db_manager.update_user_memory.assert_not_called()
    
    def test_is_available_false_no_analyzer(self):
        """Тест проверки доступности - нет анализатора"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        manager = MemoryManager(self.db_manager)
        manager.memory_analyzer = None
        
        assert manager.is_available() is False
    
    def test_is_available_false_no_db(self):
        """Тест проверки доступности - нет БД"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        mock_analyzer = Mock()
        
        manager = MemoryManager()
        manager.memory_analyzer = mock_analyzer
        
        assert manager.is_available() is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_memory_no_db(self):
        """Тест очистки устаревшей памяти без БД"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        manager = MemoryManager()
        
        result = await manager.cleanup_expired_memory(24)
        
        assert result == 0
    
    def test_set_database_manager(self):
        """Тест установки DatabaseManager"""
        from modules.memory_management.core.memory_manager import MemoryManager
        
        manager = MemoryManager()
        
        new_db_manager = Mock()
        manager.set_database_manager(new_db_manager)
        
        assert manager.db_manager == new_db_manager
