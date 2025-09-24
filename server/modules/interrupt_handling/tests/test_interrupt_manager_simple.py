"""
Упрощенные тесты для InterruptManager
"""

import pytest
import asyncio
import time
from modules.interrupt_handling.core.interrupt_manager import InterruptManager
from modules.interrupt_handling.config import InterruptHandlingConfig

class TestInterruptManagerSimple:
    """Упрощенные тесты для InterruptManager"""
    
    def test_manager_creation(self):
        """Тест создания менеджера"""
        config = InterruptHandlingConfig()
        manager = InterruptManager(config)
        
        # Проверяем, что менеджер создался
        assert manager is not None, "Менеджер должен быть создан"
        assert manager.name == "interrupt_handling", "Имя должно соответствовать"
        assert hasattr(manager, 'global_interrupt_flag'), "Должен иметь global_interrupt_flag"
        assert hasattr(manager, 'interrupt_hardware_id'), "Должен иметь interrupt_hardware_id"
    
    def test_initial_state(self):
        """Тест начального состояния"""
        manager = InterruptManager()
        
        # Проверяем начальное состояние
        assert manager.global_interrupt_flag is False, "Глобальный флаг должен быть False"
        assert manager.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None"
        assert manager.interrupt_timestamp is None, "interrupt_timestamp должен быть None"
        assert len(manager.active_sessions) == 0, "Активные сессии должны быть пустыми"
        assert len(manager.registered_modules) == 0, "Зарегистрированные модули должны быть пустыми"
    
    def test_register_unregister_session(self):
        """Тест регистрации и отмены регистрации сессии"""
        manager = InterruptManager()
        
        session_id = "session_123"
        hardware_id = "hardware_456"
        session_data = {"test": "data"}
        
        # Регистрируем сессию
        result = manager.register_session(session_id, hardware_id, session_data)
        assert result is True, "Регистрация сессии должна быть успешной"
        assert session_id in manager.active_sessions, "Сессия должна быть в active_sessions"
        
        # Проверяем данные сессии
        session_info = manager.active_sessions[session_id]
        assert session_info["hardware_id"] == hardware_id, "hardware_id должен соответствовать"
        assert session_info["data"] == session_data, "Данные сессии должны соответствовать"
        
        # Отменяем регистрацию сессии
        result = manager.unregister_session(session_id)
        assert result is True, "Отмена регистрации должна быть успешной"
        assert session_id not in manager.active_sessions, "Сессия должна быть удалена"
    
    def test_unregister_nonexistent_session(self):
        """Тест отмены регистрации несуществующей сессии"""
        manager = InterruptManager()
        
        result = manager.unregister_session("nonexistent_session")
        assert result is False, "Отмена регистрации несуществующей сессии должна возвращать False"
    
    def test_should_interrupt_initial(self):
        """Тест проверки прерывания в начальном состоянии"""
        manager = InterruptManager()
        
        hardware_id = "test_hardware_123"
        
        # В начальном состоянии прерывание не должно требоваться
        should_interrupt = manager.should_interrupt(hardware_id)
        assert should_interrupt is False, "Прерывание не должно требоваться в начальном состоянии"
    
    def test_reset_interrupt_flags(self):
        """Тест сброса флагов прерывания"""
        manager = InterruptManager()
        
        # Устанавливаем флаги вручную (для тестирования)
        manager.global_interrupt_flag = True
        manager.interrupt_hardware_id = "test_hardware"
        manager.interrupt_timestamp = 1234567890
        
        # Сбрасываем флаги
        manager._reset_interrupt_flags()
        
        assert manager.global_interrupt_flag is False, "Флаг должен быть сброшен"
        assert manager.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None"
        assert manager.interrupt_timestamp is None, "interrupt_timestamp должен быть None"
    
    def test_get_statistics(self):
        """Тест получения статистики"""
        manager = InterruptManager()
        stats = manager.get_statistics()
        
        # Проверяем структуру статистики
        required_keys = [
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
        
        for key in required_keys:
            assert key in stats, f"Статистика должна содержать ключ {key}"
        
        # Проверяем начальные значения
        assert stats['total_interrupts'] == 0, "Начальное количество прерываний должно быть 0"
        assert stats['success_rate'] == 0, "Начальный процент успеха должен быть 0"
        assert stats['active_sessions'] == 0, "Начальное количество активных сессий должно быть 0"
        assert stats['registered_modules'] == 0, "Начальное количество зарегистрированных модулей должно быть 0"
    
    def test_config_access(self):
        """Тест доступа к конфигурации"""
        config = InterruptHandlingConfig()
        manager = InterruptManager(config)
        
        # Проверяем доступ к основным настройкам
        assert manager.config.get("global_interrupt_enabled") is not None, "Должна быть доступна настройка global_interrupt_enabled"
        assert manager.config.get("interrupt_timeout") is not None, "Должна быть доступна настройка interrupt_timeout"
        
        # Проверяем настройки модулей
        text_config = manager.config.get_module_config("text_processing")
        assert text_config is not None, "Должна быть доступна конфигурация text_processing"
        assert "enabled" in text_config, "Конфигурация модуля должна содержать 'enabled'"
        
        # Проверяем методы прерывания
        methods = manager.config.get_module_interrupt_methods("text_processing")
        assert isinstance(methods, list), "Методы прерывания должны быть списком"
        assert len(methods) > 0, "Должен быть хотя бы один метод прерывания"
    
    def test_session_counter_increment(self):
        """Тест увеличения счетчика сессий"""
        manager = InterruptManager()
        initial_counter = manager.session_counter
        
        # Регистрируем сессию
        manager.register_session("session_1", "hardware_1", {})
        assert manager.session_counter == initial_counter + 1, "Счетчик сессий должен увеличиться"
        
        # Регистрируем еще одну сессию
        manager.register_session("session_2", "hardware_2", {})
        assert manager.session_counter == initial_counter + 2, "Счетчик сессий должен увеличиться еще раз"
    
    def test_multiple_sessions_same_hardware(self):
        """Тест множественных сессий для одного hardware_id"""
        manager = InterruptManager()
        hardware_id = "hardware_123"
        
        # Регистрируем несколько сессий для одного hardware_id
        session_ids = ["session_1", "session_2", "session_3"]
        for session_id in session_ids:
            manager.register_session(session_id, hardware_id, {"test": "data"})
        
        # Проверяем, что все сессии зарегистрированы
        assert len(manager.active_sessions) == 3, "Должно быть 3 активные сессии"
        
        # Проверяем, что все сессии имеют правильный hardware_id
        for session_id in session_ids:
            assert manager.active_sessions[session_id]["hardware_id"] == hardware_id, f"Сессия {session_id} должна иметь правильный hardware_id"
    
    def test_manual_flag_setting(self):
        """Тест ручной установки флагов для тестирования"""
        manager = InterruptManager()
        hardware_id = "test_hardware_123"
        
        # Устанавливаем флаги вручную с текущим временем
        manager.global_interrupt_flag = True
        manager.interrupt_hardware_id = hardware_id
        manager.interrupt_timestamp = time.time()  # Используем текущее время
        
        # Проверяем, что флаги установлены
        assert manager.global_interrupt_flag is True, "Глобальный флаг должен быть установлен"
        assert manager.interrupt_hardware_id == hardware_id, "interrupt_hardware_id должен соответствовать"
        
        # Проверяем should_interrupt
        should_interrupt = manager.should_interrupt(hardware_id)
        assert should_interrupt is True, "Прерывание должно требоваться для правильного hardware_id"
        
        # Проверяем для другого hardware_id
        should_interrupt_other = manager.should_interrupt("other_hardware")
        assert should_interrupt_other is False, "Прерывание не должно требоваться для другого hardware_id"
