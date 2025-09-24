"""
Универсальные тесты соответствия стандартам
"""

import pytest
from modules.interrupt_handling.core.interrupt_manager import InterruptManager
from modules.interrupt_handling.config import InterruptHandlingConfig

class TestUniversalCompliance:
    """Тесты соответствия универсальным стандартам"""
    
    def test_interrupt_manager_has_required_methods(self):
        """Тест наличия обязательных методов у InterruptManager"""
        manager = InterruptManager()
        
        # Проверяем наличие обязательных методов
        required_methods = [
            'initialize',
            'process', 
            'cleanup',
            'interrupt_session',
            'register_module',
            'register_callback',
            'should_interrupt',
            'register_session',
            'unregister_session',
            'get_statistics'
        ]
        
        for method_name in required_methods:
            assert hasattr(manager, method_name), f"InterruptManager должен иметь метод {method_name}"
            assert callable(getattr(manager, method_name)), f"Метод {method_name} должен быть вызываемым"
    
    def test_interrupt_handling_config_has_required_methods(self):
        """Тест наличия обязательных методов у InterruptHandlingConfig"""
        config = InterruptHandlingConfig()
        
        # Проверяем наличие обязательных методов
        required_methods = [
            'get',
            'get_module_config',
            'is_module_interrupt_enabled',
            'get_module_interrupt_methods',
            'get_module_timeout',
            'get_global_settings',
            'get_session_settings',
            'get_performance_settings'
        ]
        
        for method_name in required_methods:
            assert hasattr(config, method_name), f"InterruptHandlingConfig должен иметь метод {method_name}"
            assert callable(getattr(config, method_name)), f"Метод {method_name} должен быть вызываемым"
    
    def test_config_structure(self):
        """Тест структуры конфигурации"""
        config = InterruptHandlingConfig()
        
        # Проверяем наличие обязательных ключей конфигурации
        required_config_keys = [
            'global_interrupt_enabled',
            'interrupt_check_interval',
            'interrupt_timeout',
            'session_cleanup_delay',
            'max_active_sessions',
            'session_timeout',
            'modules',
            'log_interrupts',
            'log_timing',
            'interrupt_priority',
            'cleanup_on_interrupt',
            'force_cleanup'
        ]
        
        for key in required_config_keys:
            assert config.get(key) is not None, f"Конфигурация должна содержать ключ {key}"
    
    def test_modules_config_structure(self):
        """Тест структуры конфигурации модулей"""
        config = InterruptHandlingConfig()
        
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
            assert 'interrupt_methods' in module_config, f"Конфигурация модуля {module_name} должна содержать 'interrupt_methods'"
            assert 'timeout' in module_config, f"Конфигурация модуля {module_name} должна содержать 'timeout'"
    
    def test_global_settings_structure(self):
        """Тест структуры глобальных настроек"""
        config = InterruptHandlingConfig()
        global_settings = config.get_global_settings()
        
        required_global_keys = ['global_interrupt_enabled', 'interrupt_check_interval', 'interrupt_timeout']
        for key in required_global_keys:
            assert key in global_settings, f"Глобальные настройки должны содержать ключ {key}"
        
        assert isinstance(global_settings['global_interrupt_enabled'], bool), "global_interrupt_enabled должен быть булевым значением"
        assert isinstance(global_settings['interrupt_check_interval'], float), "interrupt_check_interval должен быть числом с плавающей точкой"
        assert isinstance(global_settings['interrupt_timeout'], float), "interrupt_timeout должен быть числом с плавающей точкой"
    
    def test_session_settings_structure(self):
        """Тест структуры настроек сессий"""
        config = InterruptHandlingConfig()
        session_settings = config.get_session_settings()
        
        required_session_keys = ['session_cleanup_delay', 'max_active_sessions', 'session_timeout']
        for key in required_session_keys:
            assert key in session_settings, f"Настройки сессий должны содержать ключ {key}"
        
        assert isinstance(session_settings['session_cleanup_delay'], float), "session_cleanup_delay должен быть числом с плавающей точкой"
        assert isinstance(session_settings['max_active_sessions'], int), "max_active_sessions должен быть числом"
        assert isinstance(session_settings['session_timeout'], int), "session_timeout должен быть числом"
    
    def test_performance_settings_structure(self):
        """Тест структуры настроек производительности"""
        config = InterruptHandlingConfig()
        performance_settings = config.get_performance_settings()
        
        required_performance_keys = ['interrupt_priority', 'cleanup_on_interrupt', 'force_cleanup']
        for key in required_performance_keys:
            assert key in performance_settings, f"Настройки производительности должны содержать ключ {key}"
        
        assert isinstance(performance_settings['cleanup_on_interrupt'], bool), "cleanup_on_interrupt должен быть булевым значением"
        assert isinstance(performance_settings['force_cleanup'], bool), "force_cleanup должен быть булевым значением"
    
    def test_manager_initialization(self):
        """Тест инициализации менеджера"""
        config = InterruptHandlingConfig()
        manager = InterruptManager(config)
        
        # Проверяем начальное состояние
        assert manager.config is not None, "Конфигурация должна быть установлена"
        assert isinstance(manager.active_sessions, dict), "active_sessions должен быть словарем"
        assert isinstance(manager.registered_modules, dict), "registered_modules должен быть словарем"
        assert isinstance(manager.interrupt_callbacks, set), "interrupt_callbacks должен быть множеством"
        assert manager.global_interrupt_flag is False, "global_interrupt_flag должен быть False по умолчанию"
        assert manager.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None по умолчанию"
    
    def test_manager_statistics_structure(self):
        """Тест структуры статистики менеджера"""
        manager = InterruptManager()
        stats = manager.get_statistics()
        
        required_stats_keys = [
            'total_interrupts',
            'successful_interrupts',
            'failed_interrupts',
            'success_rate',
            'active_sessions',
            'registered_modules',
            'registered_callbacks',
            'global_interrupt_flag',
            'interrupt_hardware_id'
        ]
        
        for key in required_stats_keys:
            assert key in stats, f"Статистика должна содержать ключ {key}"
        
        assert isinstance(stats['total_interrupts'], int), "total_interrupts должен быть числом"
        assert isinstance(stats['success_rate'], (int, float)), "success_rate должен быть числом"
        assert isinstance(stats['active_sessions'], int), "active_sessions должен быть числом"
        assert isinstance(stats['global_interrupt_flag'], bool), "global_interrupt_flag должен быть булевым значением"
    
    def test_module_interrupt_enabled_check(self):
        """Тест проверки включения прерывания для модулей"""
        config = InterruptHandlingConfig()
        
        # Проверяем, что все модули включены по умолчанию
        required_modules = [
            'text_processing',
            'audio_generation',
            'session_management', 
            'database',
            'memory_management'
        ]
        
        for module_name in required_modules:
            assert config.is_module_interrupt_enabled(module_name), f"Прерывание модуля {module_name} должно быть включено по умолчанию"
    
    def test_module_interrupt_methods_config(self):
        """Тест конфигурации методов прерывания модулей"""
        config = InterruptHandlingConfig()
        
        # Проверяем, что у всех модулей есть методы прерывания
        required_modules = [
            'text_processing',
            'audio_generation',
            'session_management',
            'database', 
            'memory_management'
        ]
        
        for module_name in required_modules:
            methods = config.get_module_interrupt_methods(module_name)
            assert isinstance(methods, list), f"Методы прерывания модуля {module_name} должны быть списком"
            assert len(methods) > 0, f"Модуль {module_name} должен иметь хотя бы один метод прерывания"
    
    def test_module_timeout_config(self):
        """Тест конфигурации таймаутов модулей"""
        config = InterruptHandlingConfig()
        
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
            assert isinstance(timeout, float), f"Таймаут модуля {module_name} должен быть числом с плавающей точкой"
            assert timeout > 0, f"Таймаут модуля {module_name} должен быть положительным"
