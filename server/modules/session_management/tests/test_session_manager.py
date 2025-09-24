"""
Тесты для основного SessionManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.session_management.core.session_manager import SessionManager
from modules.session_management.config import SessionManagementConfig

class TestSessionManager:
    """Тесты для основного менеджера сессий"""
    
    def test_session_manager_initialization(self):
        """Тест инициализации менеджера"""
        config = {
            'session_timeout': 1800,
            'max_concurrent_sessions': 50,
            'hardware_id_length': 24
        }
        
        manager = SessionManager(config)
        
        assert manager.config is not None
        assert manager.hardware_id_provider is None
        assert manager.session_tracker is None
        assert manager.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'session_timeout': 1800,
            'max_concurrent_sessions': 50
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                # Мокаем экземпляры провайдеров
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware.name = "hardware_id"
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker.name = "session_tracker"
                mock_tracker_class.return_value = mock_tracker
                
                result = await manager.initialize()
                
                assert result is True
                assert manager.is_initialized is True
                assert manager.hardware_id_provider is not None
                assert manager.session_tracker is not None
    
    @pytest.mark.asyncio
    async def test_initialize_config_validation_failure(self):
        """Тест неудачной инициализации - невалидная конфигурация"""
        config = {
            'session_timeout': -1  # Некорректное значение
        }
        
        manager = SessionManager(config)
        
        result = await manager.initialize()
        
        assert result is False
        assert manager.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_no_providers_initialized(self):
        """Тест неудачной инициализации - ни один провайдер не инициализировался"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры, которые не могут инициализироваться
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=False)
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=False)
                mock_tracker_class.return_value = mock_tracker
                
                result = await manager.initialize()
                
                assert result is False
                assert manager.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_create_session_success(self):
        """Тест успешного создания сессии"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter(["test-hardware-id"]))))
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter([{
                    'session_id': 'test-session-id',
                    'hardware_id': 'test-hardware-id',
                    'status': 'active'
                }]))))
                mock_tracker_class.return_value = mock_tracker
                
                # Инициализируем менеджер
                await manager.initialize()
                
                # Создаем сессию
                session_data = await manager.create_session(
                    user_agent="Test Agent",
                    context={"test": "data"}
                )
                
                assert session_data['session_id'] == 'test-session-id'
                assert session_data['hardware_id'] == 'test-hardware-id'
                assert session_data['status'] == 'active'
    
    @pytest.mark.asyncio
    async def test_create_session_not_initialized(self):
        """Тест создания сессии без инициализации"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Не инициализируем менеджер
        
        with pytest.raises(Exception) as exc_info:
            await manager.create_session()
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_get_session_status(self):
        """Тест получения статуса сессии"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker.get_session_status = AsyncMock(return_value={
                    'session_id': 'test-session-id',
                    'status': 'active'
                })
                mock_tracker_class.return_value = mock_tracker
                
                # Инициализируем менеджер
                await manager.initialize()
                
                # Получаем статус сессии
                status = await manager.get_session_status('test-session-id')
                
                assert status['session_id'] == 'test-session-id'
                assert status['status'] == 'active'
    
    @pytest.mark.asyncio
    async def test_interrupt_session(self):
        """Тест прерывания сессии"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker.interrupt_session = AsyncMock(return_value=True)
                mock_tracker_class.return_value = mock_tracker
                
                # Инициализируем менеджер
                await manager.initialize()
                
                # Прерываем сессию
                result = await manager.interrupt_session('test-session-id', 'user_request')
                
                assert result is True
    
    @pytest.mark.asyncio
    async def test_interrupt_all_sessions(self):
        """Тест прерывания всех сессий"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker.interrupt_all_sessions = AsyncMock(return_value=5)
                mock_tracker_class.return_value = mock_tracker
                
                # Инициализируем менеджер
                await manager.initialize()
                
                # Прерываем все сессии
                count = await manager.interrupt_all_sessions('global_interrupt')
                
                assert count == 5
    
    @pytest.mark.asyncio
    async def test_get_hardware_id(self):
        """Тест получения Hardware ID"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter(["test-hardware-id"]))))
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker_class.return_value = mock_tracker
                
                # Инициализируем менеджер
                await manager.initialize()
                
                # Получаем Hardware ID
                hardware_id = await manager.get_hardware_id()
                
                assert hardware_id == 'test-hardware-id'
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        with patch('modules.session_management.core.session_manager.HardwareIDProvider') as mock_hardware_class:
            with patch('modules.session_management.core.session_manager.SessionTracker') as mock_tracker_class:
                mock_hardware = AsyncMock()
                mock_hardware.initialize = AsyncMock(return_value=True)
                mock_hardware.cleanup = AsyncMock(return_value=True)
                mock_hardware_class.return_value = mock_hardware
                
                mock_tracker = AsyncMock()
                mock_tracker.initialize = AsyncMock(return_value=True)
                mock_tracker.cleanup = AsyncMock(return_value=True)
                mock_tracker_class.return_value = mock_tracker
                
                # Инициализируем менеджер
                await manager.initialize()
                
                # Очищаем ресурсы
                result = await manager.cleanup()
                
                assert result is True
                assert manager.is_initialized is False
    
    def test_get_status(self):
        """Тест получения статуса менеджера"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        status = manager.get_status()
        
        assert "is_initialized" in status
        assert "config_status" in status
        assert "hardware_id_provider" in status
        assert "session_tracker" in status
        assert status["hardware_id_provider"] is None
        assert status["session_tracker"] is None
    
    def test_get_metrics(self):
        """Тест получения метрик менеджера"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        metrics = manager.get_metrics()
        
        assert "is_initialized" in metrics
        assert "hardware_id_provider" in metrics
        assert "session_tracker" in metrics
    
    def test_get_session_statistics(self):
        """Тест получения статистики сессий"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем session_tracker
        manager.session_tracker = MagicMock()
        manager.session_tracker.get_session_statistics.return_value = {
            'active_sessions': 5,
            'total_sessions': 10
        }
        
        stats = manager.get_session_statistics()
        
        assert stats['active_sessions'] == 5
        assert stats['total_sessions'] == 10
    
    def test_get_security_settings(self):
        """Тест получения настроек безопасности"""
        config = {
            'session_timeout': 1800,
            'require_hardware_id': True,
            'validate_session_ownership': True
        }
        
        manager = SessionManager(config)
        
        security_settings = manager.get_security_settings()
        
        assert security_settings['require_hardware_id'] is True
        assert security_settings['validate_session_ownership'] is True
    
    def test_get_performance_settings(self):
        """Тест получения настроек производительности"""
        config = {
            'session_timeout': 1800,
            'max_concurrent_sessions': 50,
            'session_cleanup_interval': 300
        }
        
        manager = SessionManager(config)
        
        performance_settings = manager.get_performance_settings()
        
        assert performance_settings['session_timeout'] == 1800
        assert performance_settings['max_concurrent_sessions'] == 50
        assert performance_settings['session_cleanup_interval'] == 300
    
    def test_get_tracking_settings(self):
        """Тест получения настроек отслеживания"""
        config = {
            'tracking_enabled': True,
            'track_user_agents': True,
            'track_ip_addresses': False
        }
        
        manager = SessionManager(config)
        
        tracking_settings = manager.get_tracking_settings()
        
        assert tracking_settings['tracking_enabled'] is True
        assert tracking_settings['track_user_agents'] is True
        assert tracking_settings['track_ip_addresses'] is False
    
    def test_reset_metrics(self):
        """Тест сброса метрик менеджера"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        # Мокаем провайдеры
        manager.hardware_id_provider = MagicMock()
        manager.hardware_id_provider.reset_metrics = MagicMock()
        
        manager.session_tracker = MagicMock()
        manager.session_tracker.reset_metrics = MagicMock()
        
        # Сбрасываем метрики
        manager.reset_metrics()
        
        manager.hardware_id_provider.reset_metrics.assert_called_once()
        manager.session_tracker.reset_metrics.assert_called_once()
    
    def test_get_summary(self):
        """Тест получения сводки по менеджеру"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        summary = manager.get_summary()
        
        assert "is_initialized" in summary
        assert "hardware_id_available" in summary
        assert "session_tracker_available" in summary
        assert "config_valid" in summary
        assert "session_statistics" in summary
        assert "security_settings" in summary
    
    def test_str_representation(self):
        """Тест строкового представления менеджера"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        str_repr = str(manager)
        
        assert "SessionManager" in str_repr
        assert "initialized=False" in str_repr
        assert "providers=2" in str_repr
    
    def test_repr_representation(self):
        """Тест представления менеджера для отладки"""
        config = {
            'session_timeout': 1800
        }
        
        manager = SessionManager(config)
        
        repr_str = repr(manager)
        
        assert "SessionManager(" in repr_str
        assert "initialized=False" in repr_str
        assert "hardware_id_available=False" in repr_str
        assert "session_tracker_available=False" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
