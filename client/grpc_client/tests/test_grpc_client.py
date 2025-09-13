"""
Тесты для gRPC клиента
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock

from ..core.grpc_client import GrpcClient
from ..core.types import ConnectionState, RetryStrategy
from ..config.grpc_config import create_test_config


class TestGrpcClient:
    """Тесты для GrpcClient"""
    
    def test_initialization(self):
        """Тест инициализации клиента"""
        client = GrpcClient()
        assert client is not None
        assert client.connection_manager is not None
        assert client.retry_manager is not None
    
    def test_config_loading(self):
        """Тест загрузки конфигурации"""
        config = create_test_config()
        client = GrpcClient(config)
        assert client.config == config
    
    def test_server_initialization(self):
        """Тест инициализации серверов"""
        config = create_test_config()
        client = GrpcClient(config)
        assert len(client.connection_manager.servers) > 0
        assert 'test' in client.connection_manager.servers
    
    def test_connection_state(self):
        """Тест состояния соединения"""
        client = GrpcClient()
        assert client.get_connection_state() == ConnectionState.DISCONNECTED
        assert not client.is_connected()
    
    def test_metrics(self):
        """Тест метрик"""
        client = GrpcClient()
        metrics = client.get_metrics()
        assert metrics is not None
        assert metrics.total_connections == 0
        assert metrics.successful_connections == 0
        assert metrics.failed_connections == 0
    
    @pytest.mark.asyncio
    async def test_connect_disconnect(self):
        """Тест подключения и отключения"""
        client = GrpcClient(create_test_config())
        
        # Мокаем gRPC канал
        mock_channel = AsyncMock()
        mock_channel.channel_ready.return_value = None
        mock_channel.get_state.return_value = 2  # READY state
        
        # Подменяем создание канала
        original_connect = client.connection_manager._connect
        client.connection_manager._connect = AsyncMock(return_value=True)
        client.connection_manager.channel = mock_channel
        
        # Тестируем подключение
        result = await client.connect()
        assert result is True
        
        # Тестируем отключение
        await client.disconnect()
        assert client.get_connection_state() == ConnectionState.DISCONNECTED
    
    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Тест retry механизма"""
        client = GrpcClient()
        
        # Создаем операцию, которая падает первые 2 раза
        call_count = 0
        async def failing_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception(f"Attempt {call_count} failed")
            return "success"
        
        # Тестируем retry
        result = await client.execute_with_retry(failing_operation)
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        client = GrpcClient()
        
        # Мокаем cleanup методы
        client.connection_manager.cleanup = AsyncMock()
        
        # Тестируем cleanup
        await client.cleanup()
        client.connection_manager.cleanup.assert_called_once()


if __name__ == "__main__":
    # Запуск тестов
    pytest.main([__file__, "-v"])
