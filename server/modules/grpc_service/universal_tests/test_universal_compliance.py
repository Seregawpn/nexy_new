"""
Универсальные тесты соответствия стандартам
"""

import pytest
from modules.grpc_service.core.grpc_service_manager import GrpcServiceManager
from modules.grpc_service.config import GrpcServiceConfig

class TestUniversalCompliance:
    """Тесты соответствия универсальным стандартам"""
    
    def test_grpc_service_manager_has_required_methods(self):
        """Тест наличия обязательных методов у GrpcServiceManager"""
        manager = GrpcServiceManager()
        
        # Проверяем наличие обязательных методов
        required_methods = [
            'initialize',
            'process_stream_request', 
            'interrupt_session',
            'get_status',
            'cleanup'
        ]
        
        for method_name in required_methods:
            assert hasattr(manager, method_name), f"GrpcServiceManager должен иметь метод {method_name}"
            assert callable(getattr(manager, method_name)), f"Метод {method_name} должен быть вызываемым"
    
    def test_grpc_service_config_has_required_methods(self):
        """Тест наличия обязательных методов у GrpcServiceConfig"""
        config = GrpcServiceConfig()
        
        # Проверяем наличие обязательных методов
        required_methods = [
            'get',
            'get_module_config',
            'is_module_enabled',
            'get_module_timeout',
            'get_grpc_settings',
            'get_session_settings',
            'get_interrupt_settings'
        ]
        
        for method_name in required_methods:
            assert hasattr(config, method_name), f"GrpcServiceConfig должен иметь метод {method_name}"
            assert callable(getattr(config, method_name)), f"Метод {method_name} должен быть вызываемым"
    
    def test_config_structure(self):
        """Тест структуры конфигурации"""
        config = GrpcServiceConfig()
        
        # Проверяем наличие обязательных ключей конфигурации
        required_config_keys = [
            'grpc_host',
            'grpc_port',
            'use_tls',
            'max_sessions',
            'session_timeout',
            'interrupt_check_interval',
            'max_processing_time',
            'log_level',
            'log_requests',
            'max_concurrent_requests',
            'request_timeout',
            'modules'
        ]
        
        for key in required_config_keys:
            assert config.get(key) is not None, f"Конфигурация должна содержать ключ {key}"
    
    def test_modules_config_structure(self):
        """Тест структуры конфигурации модулей"""
        config = GrpcServiceConfig()
        
        # Проверяем конфигурацию каждого модуля
        required_modules = [
            'text_processing',
            'audio_generation', 
            'session_management',
            'database',
            'memory_management'
        ]
        
        for module_name in required_modules:
            module_config = config.get_module_config(module_name)
            assert module_config is not None, f"Конфигурация модуля {module_name} должна существовать"
            assert 'enabled' in module_config, f"Конфигурация модуля {module_name} должна содержать 'enabled'"
            assert 'timeout' in module_config, f"Конфигурация модуля {module_name} должна содержать 'timeout'"
    
    def test_grpc_settings_structure(self):
        """Тест структуры настроек gRPC"""
        config = GrpcServiceConfig()
        grpc_settings = config.get_grpc_settings()
        
        required_grpc_keys = ['host', 'port', 'use_tls']
        for key in required_grpc_keys:
            assert key in grpc_settings, f"Настройки gRPC должны содержать ключ {key}"
        
        assert isinstance(grpc_settings['port'], int), "Порт должен быть числом"
        assert isinstance(grpc_settings['use_tls'], bool), "use_tls должен быть булевым значением"
    
    def test_session_settings_structure(self):
        """Тест структуры настроек сессий"""
        config = GrpcServiceConfig()
        session_settings = config.get_session_settings()
        
        required_session_keys = ['max_sessions', 'session_timeout']
        for key in required_session_keys:
            assert key in session_settings, f"Настройки сессий должны содержать ключ {key}"
        
        assert isinstance(session_settings['max_sessions'], int), "max_sessions должен быть числом"
        assert isinstance(session_settings['session_timeout'], int), "session_timeout должен быть числом"
    
    def test_interrupt_settings_structure(self):
        """Тест структуры настроек прерывания"""
        config = GrpcServiceConfig()
        interrupt_settings = config.get_interrupt_settings()
        
        required_interrupt_keys = ['check_interval', 'max_processing_time']
        for key in required_interrupt_keys:
            assert key in interrupt_settings, f"Настройки прерывания должны содержать ключ {key}"
        
        assert isinstance(interrupt_settings['check_interval'], float), "check_interval должен быть числом с плавающей точкой"
        assert isinstance(interrupt_settings['max_processing_time'], int), "max_processing_time должен быть числом"
    
    def test_manager_initialization(self):
        """Тест инициализации менеджера"""
        config = GrpcServiceConfig()
        manager = GrpcServiceManager(config)
        
        # Проверяем начальное состояние
        assert manager.config is not None, "Конфигурация должна быть установлена"
        assert isinstance(manager.modules, dict), "modules должен быть словарем"
        assert isinstance(manager.integrations, dict), "integrations должен быть словарем"
        assert isinstance(manager.active_sessions, dict), "active_sessions должен быть словарем"
        assert manager.global_interrupt_flag is False, "global_interrupt_flag должен быть False по умолчанию"
        assert manager.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None по умолчанию"
    
    def test_manager_status_structure(self):
        """Тест структуры статуса менеджера"""
        manager = GrpcServiceManager()
        status = manager.get_status()
        
        required_status_keys = [
            'active_sessions',
            'modules',
            'integrations',
            'global_interrupt_flag',
            'interrupt_hardware_id'
        ]
        
        for key in required_status_keys:
            assert key in status, f"Статус должен содержать ключ {key}"
        
        assert isinstance(status['active_sessions'], int), "active_sessions должен быть числом"
        assert isinstance(status['modules'], dict), "modules должен быть словарем"
        assert isinstance(status['integrations'], dict), "integrations должен быть словарем"
        assert isinstance(status['global_interrupt_flag'], bool), "global_interrupt_flag должен быть булевым значением"
    
    def test_module_enabled_check(self):
        """Тест проверки включения модулей"""
        config = GrpcServiceConfig()
        
        # Проверяем, что все модули включены по умолчанию
        required_modules = [
            'text_processing',
            'audio_generation',
            'session_management', 
            'database',
            'memory_management'
        ]
        
        for module_name in required_modules:
            assert config.is_module_enabled(module_name), f"Модуль {module_name} должен быть включен по умолчанию"
    
    def test_module_timeout_config(self):
        """Тест конфигурации таймаутов модулей"""
        config = GrpcServiceConfig()
        
        # Проверяем, что у всех модулей есть таймауты
        required_modules = [
            'text_processing',
            'audio_generation',
            'session_management',
            'database', 
            'memory_management'
        ]
        
        for module_name in required_modules:
            timeout = config.get_module_timeout(module_name)
            assert isinstance(timeout, int), f"Таймаут модуля {module_name} должен быть числом"
            assert timeout > 0, f"Таймаут модуля {module_name} должен быть положительным"
