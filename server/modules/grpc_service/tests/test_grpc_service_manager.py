"""
Тесты для GrpcServiceManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from modules.grpc_service.core.grpc_service_manager import GrpcServiceManager
from modules.grpc_service.config import GrpcServiceConfig

class TestGrpcServiceManager:
    """Тесты для GrpcServiceManager"""
    
    @pytest.fixture
    def config(self):
        """Фикстура конфигурации"""
        return GrpcServiceConfig()
    
    @pytest.fixture
    def grpc_manager(self, config):
        """Фикстура GrpcServiceManager"""
        return GrpcServiceManager(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, grpc_manager):
        """Тест инициализации"""
        # Мокаем модули
        with patch('modules.grpc_service.core.grpc_service_manager.TextProcessor') as mock_text, \
             patch('modules.grpc_service.core.grpc_service_manager.AudioProcessor') as mock_audio, \
             patch('modules.grpc_service.core.grpc_service_manager.SessionManager') as mock_session, \
             patch('modules.grpc_service.core.grpc_service_manager.DatabaseManager') as mock_db, \
             patch('modules.grpc_service.core.grpc_service_manager.MemoryManager') as mock_memory:
            
            # Настраиваем моки
            mock_text.return_value.initialize = AsyncMock(return_value=True)
            mock_audio.return_value.initialize = AsyncMock(return_value=True)
            mock_session.return_value.initialize = AsyncMock(return_value=True)
            mock_db.return_value.initialize = AsyncMock(return_value=True)
            mock_memory.return_value.initialize = AsyncMock(return_value=True)
            
            # Тестируем инициализацию
            result = await grpc_manager.initialize()
            
            assert result is True
            assert len(grpc_manager.modules) == 5
            assert len(grpc_manager.integrations) == 5
    
    @pytest.mark.asyncio
    async def test_process_stream_request(self, grpc_manager):
        """Тест обработки StreamRequest"""
        # Мокаем интеграции
        mock_integration = AsyncMock()
        mock_integration.process_request = AsyncMock()
        mock_integration.process_request.return_value = [
            {"type": "text_chunk", "content": "Hello"},
            {"type": "audio_chunk", "content": {"audio_data": b"audio"}}
        ].__aiter__()
        
        grpc_manager.integrations["text_processing"] = mock_integration
        grpc_manager.integrations["audio_generation"] = mock_integration
        
        # Данные запроса
        request_data = {
            "prompt": "Hello",
            "hardware_id": "test_hw_123",
            "session_id": "test_session_456"
        }
        
        # Тестируем обработку
        results = []
        async for result in grpc_manager.process_stream_request(request_data):
            results.append(result)
        
        assert len(results) > 0
        assert any(r["type"] == "text_chunk" for r in results)
        assert any(r["type"] == "audio_chunk" for r in results)
    
    @pytest.mark.asyncio
    async def test_interrupt_session(self, grpc_manager):
        """Тест прерывания сессии"""
        # Мокаем интеграции
        mock_integration = AsyncMock()
        mock_integration.interrupt = AsyncMock(return_value=True)
        
        grpc_manager.integrations["text_processing"] = mock_integration
        grpc_manager.integrations["audio_generation"] = mock_integration
        
        # Тестируем прерывание
        result = await grpc_manager.interrupt_session("test_hw_123")
        
        assert result["success"] is True
        assert "text_processing" in result["interrupted_sessions"]
        assert "audio_generation" in result["interrupted_sessions"]
        assert grpc_manager.global_interrupt_flag is True
        assert grpc_manager.interrupt_hardware_id == "test_hw_123"
    
    @pytest.mark.asyncio
    async def test_session_management(self, grpc_manager):
        """Тест управления сессиями"""
        session_id = "test_session_123"
        hardware_id = "test_hw_456"
        request_data = {"prompt": "test"}
        
        # Регистрируем сессию
        await grpc_manager._register_session(session_id, hardware_id, request_data)
        
        assert session_id in grpc_manager.active_sessions
        assert grpc_manager.active_sessions[session_id]["hardware_id"] == hardware_id
        
        # Очищаем сессию
        await grpc_manager._cleanup_session(session_id)
        
        assert session_id not in grpc_manager.active_sessions
    
    def test_get_status(self, grpc_manager):
        """Тест получения статуса"""
        # Мокаем модули и интеграции
        mock_module = Mock()
        mock_module.get_status.return_value = {"name": "test_module", "status": "ready"}
        
        mock_integration = Mock()
        mock_integration.get_status.return_value = {"name": "test_integration", "initialized": True}
        
        grpc_manager.modules["test_module"] = mock_module
        grpc_manager.integrations["test_integration"] = mock_integration
        
        # Тестируем получение статуса
        status = grpc_manager.get_status()
        
        assert "active_sessions" in status
        assert "modules" in status
        assert "integrations" in status
        assert "global_interrupt_flag" in status
        assert "interrupt_hardware_id" in status
        assert status["active_sessions"] == 0
        assert status["global_interrupt_flag"] is False
    
    @pytest.mark.asyncio
    async def test_cleanup(self, grpc_manager):
        """Тест очистки ресурсов"""
        # Мокаем модули и интеграции
        mock_module = AsyncMock()
        mock_module.cleanup = AsyncMock(return_value=True)
        
        mock_integration = AsyncMock()
        mock_integration.cleanup = AsyncMock(return_value=True)
        
        grpc_manager.modules["test_module"] = mock_module
        grpc_manager.integrations["test_integration"] = mock_integration
        grpc_manager.active_sessions["test_session"] = {"hardware_id": "test_hw"}
        
        # Тестируем очистку
        result = await grpc_manager.cleanup()
        
        assert result is True
        assert len(grpc_manager.active_sessions) == 0
        mock_module.cleanup.assert_called_once()
        mock_integration.cleanup.assert_called_once()
    
    def test_should_interrupt(self, grpc_manager):
        """Тест проверки прерывания"""
        hardware_id = "test_hw_123"
        
        # Без флага прерывания
        assert grpc_manager._should_interrupt(hardware_id) is False
        
        # С флагом прерывания для другого hardware_id
        grpc_manager.global_interrupt_flag = True
        grpc_manager.interrupt_hardware_id = "other_hw_456"
        assert grpc_manager._should_interrupt(hardware_id) is False
        
        # С флагом прерывания для правильного hardware_id
        grpc_manager.interrupt_hardware_id = hardware_id
        assert grpc_manager._should_interrupt(hardware_id) is True
