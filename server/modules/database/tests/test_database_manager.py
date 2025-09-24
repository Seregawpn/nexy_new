"""
Тесты для основного DatabaseManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.database.core.database_manager import DatabaseManager
from modules.database.config import DatabaseConfig

class TestDatabaseManager:
    """Тесты для основного менеджера базы данных"""
    
    def test_database_manager_initialization(self):
        """Тест инициализации менеджера"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'test_user',
            'password': 'test_pass'
        }
        
        manager = DatabaseManager(config)
        
        assert manager.config is not None
        assert manager.postgresql_provider is None
        assert manager.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            # Мокаем экземпляр провайдера
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.name = "postgresql"
            mock_provider_class.return_value = mock_provider
            
            result = await manager.initialize()
            
            assert result is True
            assert manager.is_initialized is True
            assert manager.postgresql_provider is not None
    
    @pytest.mark.asyncio
    async def test_initialize_config_validation_failure(self):
        """Тест неудачной инициализации - невалидная конфигурация"""
        config = {
            'host': '',  # Некорректное значение
            'port': -1   # Некорректное значение
        }
        
        manager = DatabaseManager(config)
        
        result = await manager.initialize()
        
        assert result is False
        assert manager.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_provider_failure(self):
        """Тест неудачной инициализации - провайдер не может инициализироваться"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер, который не может инициализироваться
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=False)
            mock_provider_class.return_value = mock_provider
            
            result = await manager.initialize()
            
            assert result is False
            assert manager.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Тест успешного создания пользователя"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.create_user = AsyncMock(return_value='user-id-123')
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Создаем пользователя
            user_id = await manager.create_user('hardware-id-hash', {'test': 'data'})
            
            assert user_id == 'user-id-123'
    
    @pytest.mark.asyncio
    async def test_create_user_not_initialized(self):
        """Тест создания пользователя без инициализации"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Не инициализируем менеджер
        
        user_id = await manager.create_user('hardware-id-hash')
        
        assert user_id is None
    
    @pytest.mark.asyncio
    async def test_get_user_by_hardware_id(self):
        """Тест получения пользователя по hardware ID"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.get_user_by_hardware_id = AsyncMock(return_value={'id': 'user-id', 'hardware_id_hash': 'hash'})
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Получаем пользователя
            user = await manager.get_user_by_hardware_id('hardware-id-hash')
            
            assert user['id'] == 'user-id'
            assert user['hardware_id_hash'] == 'hash'
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Тест создания сессии"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.create_session = AsyncMock(return_value='session-id-123')
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Создаем сессию
            session_id = await manager.create_session('user-id-123', {'test': 'data'})
            
            assert session_id == 'session-id-123'
    
    @pytest.mark.asyncio
    async def test_end_session(self):
        """Тест завершения сессии"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.end_session = AsyncMock(return_value=True)
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Завершаем сессию
            result = await manager.end_session('session-id-123')
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_create_command(self):
        """Тест создания команды"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.create_command = AsyncMock(return_value='command-id-123')
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Создаем команду
            command_id = await manager.create_command('session-id-123', 'Test prompt', {'test': 'data'}, 'en')
            
            assert command_id == 'command-id-123'
    
    @pytest.mark.asyncio
    async def test_create_llm_answer(self):
        """Тест создания ответа LLM"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.create_llm_answer = AsyncMock(return_value='answer-id-123')
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Создаем ответ LLM
            answer_id = await manager.create_llm_answer(
                'command-id-123', 
                'Test prompt', 
                'Test response',
                {'model': 'test'},
                {'time': 1000}
            )
            
            assert answer_id == 'answer-id-123'
    
    @pytest.mark.asyncio
    async def test_create_screenshot(self):
        """Тест создания скриншота"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.create_screenshot = AsyncMock(return_value='screenshot-id-123')
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Создаем скриншот
            screenshot_id = await manager.create_screenshot('session-id-123', '/path/to/file.png', None, {'test': 'data'})
            
            assert screenshot_id == 'screenshot-id-123'
    
    @pytest.mark.asyncio
    async def test_create_performance_metric(self):
        """Тест создания метрики производительности"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.create_performance_metric = AsyncMock(return_value='metric-id-123')
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Создаем метрику
            metric_id = await manager.create_performance_metric('session-id-123', 'response_time', {'time': 1000})
            
            assert metric_id == 'metric-id-123'
    
    @pytest.mark.asyncio
    async def test_get_user_statistics(self):
        """Тест получения статистики пользователя"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.get_user_statistics = AsyncMock(return_value={'total_sessions': 5, 'total_commands': 10})
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Получаем статистику
            stats = await manager.get_user_statistics('user-id-123')
            
            assert stats['total_sessions'] == 5
            assert stats['total_commands'] == 10
    
    @pytest.mark.asyncio
    async def test_get_session_commands(self):
        """Тест получения команд сессии"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.get_session_commands = AsyncMock(return_value=[{'id': 'cmd1', 'prompt': 'test'}])
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Получаем команды сессии
            commands = await manager.get_session_commands('session-id-123')
            
            assert len(commands) == 1
            assert commands[0]['id'] == 'cmd1'
    
    @pytest.mark.asyncio
    async def test_get_user_memory(self):
        """Тест получения памяти пользователя"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.get_user_memory = AsyncMock(return_value={'short': 'short memory', 'long': 'long memory'})
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Получаем память пользователя
            memory = await manager.get_user_memory('hardware-id-hash')
            
            assert memory['short'] == 'short memory'
            assert memory['long'] == 'long memory'
    
    @pytest.mark.asyncio
    async def test_update_user_memory(self):
        """Тест обновления памяти пользователя"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.update_user_memory = AsyncMock(return_value=True)
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Обновляем память пользователя
            result = await manager.update_user_memory('hardware-id-hash', 'new short', 'new long')
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_short_term_memory(self):
        """Тест очистки устаревшей краткосрочной памяти"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.cleanup_expired_short_term_memory = AsyncMock(return_value=5)
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Очищаем устаревшую память
            count = await manager.cleanup_expired_short_term_memory(24)
            
            assert count == 5
    
    @pytest.mark.asyncio
    async def test_get_memory_statistics(self):
        """Тест получения статистики памяти"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.get_memory_statistics = AsyncMock(return_value={'total_users': 100, 'users_with_memory': 50})
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Получаем статистику памяти
            stats = await manager.get_memory_statistics()
            
            assert stats['total_users'] == 100
            assert stats['users_with_memory'] == 50
    
    @pytest.mark.asyncio
    async def test_get_users_with_active_memory(self):
        """Тест получения пользователей с активной памятью"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.get_users_with_active_memory = AsyncMock(return_value=[{'hardware_id_hash': 'hash1', 'memory_updated_at': '2024-01-01'}])
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Получаем пользователей с активной памятью
            users = await manager.get_users_with_active_memory(10)
            
            assert len(users) == 1
            assert users[0]['hardware_id_hash'] == 'hash1'
    
    @pytest.mark.asyncio
    async def test_execute_query(self):
        """Тест универсального выполнения запроса"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter([{'success': True, 'data': {'id': 'test'}}]))))
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Выполняем запрос
            result = await manager.execute_query('read', 'users', {}, {'id': 'test'})
            
            assert result['success'] is True
            assert result['data']['id'] == 'test'
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        with patch('modules.database.core.database_manager.PostgreSQLProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.cleanup = AsyncMock(return_value=True)
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем менеджер
            await manager.initialize()
            
            # Очищаем ресурсы
            result = await manager.cleanup()
            
            assert result is True
            assert manager.is_initialized is False
    
    def test_get_status(self):
        """Тест получения статуса менеджера"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        status = manager.get_status()
        
        assert "is_initialized" in status
        assert "config_status" in status
        assert "postgresql_provider" in status
        assert status["postgresql_provider"] is None
    
    def test_get_metrics(self):
        """Тест получения метрик менеджера"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        metrics = manager.get_metrics()
        
        assert "is_initialized" in metrics
        assert "postgresql_provider" in metrics
    
    def test_get_config_status(self):
        """Тест получения статуса конфигурации"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        config_status = manager.get_config_status()
        
        assert "host" in config_status
        assert "port" in config_status
        assert "database" in config_status
    
    def test_get_security_settings(self):
        """Тест получения настроек безопасности"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'ssl_mode': 'require'
        }
        
        manager = DatabaseManager(config)
        
        security_settings = manager.get_security_settings()
        
        assert "ssl_mode" in security_settings
        assert "verify_ssl" in security_settings
    
    def test_get_performance_settings(self):
        """Тест получения настроек производительности"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'fetch_size': 1000,
            'batch_size': 100
        }
        
        manager = DatabaseManager(config)
        
        performance_settings = manager.get_performance_settings()
        
        assert "fetch_size" in performance_settings
        assert "batch_size" in performance_settings
    
    def test_get_monitoring_settings(self):
        """Тест получения настроек мониторинга"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'enable_metrics': True
        }
        
        manager = DatabaseManager(config)
        
        monitoring_settings = manager.get_monitoring_settings()
        
        assert "enable_metrics" in monitoring_settings
        assert "health_check_interval" in monitoring_settings
    
    def test_get_cleanup_settings(self):
        """Тест получения настроек очистки"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'cleanup_interval': 3600
        }
        
        manager = DatabaseManager(config)
        
        cleanup_settings = manager.get_cleanup_settings()
        
        assert "cleanup_interval" in cleanup_settings
        assert "cleanup_batch_size" in cleanup_settings
    
    def test_get_schema_settings(self):
        """Тест получения настроек схемы"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'schema_name': 'public'
        }
        
        manager = DatabaseManager(config)
        
        schema_settings = manager.get_schema_settings()
        
        assert "schema_name" in schema_settings
        assert "table_prefix" in schema_settings
    
    def test_reset_metrics(self):
        """Тест сброса метрик менеджера"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        # Мокаем провайдер
        manager.postgresql_provider = MagicMock()
        manager.postgresql_provider.reset_metrics = MagicMock()
        
        # Сбрасываем метрики
        manager.reset_metrics()
        
        manager.postgresql_provider.reset_metrics.assert_called_once()
    
    def test_get_summary(self):
        """Тест получения сводки по менеджеру"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        summary = manager.get_summary()
        
        assert "is_initialized" in summary
        assert "postgresql_provider_available" in summary
        assert "config_valid" in summary
        assert "security_settings" in summary
        assert "performance_settings" in summary
    
    def test_str_representation(self):
        """Тест строкового представления менеджера"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        str_repr = str(manager)
        
        assert "DatabaseManager" in str_repr
        assert "initialized=False" in str_repr
        assert "provider=1" in str_repr
    
    def test_repr_representation(self):
        """Тест представления менеджера для отладки"""
        config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db'
        }
        
        manager = DatabaseManager(config)
        
        repr_str = repr(manager)
        
        assert "DatabaseManager(" in repr_str
        assert "initialized=False" in repr_str
        assert "postgresql_provider_available=False" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
