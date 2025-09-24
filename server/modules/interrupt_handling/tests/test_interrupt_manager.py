"""
Unit тесты для InterruptManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from modules.interrupt_handling.core.interrupt_manager import InterruptManager
from modules.interrupt_handling.config import InterruptHandlingConfig

class TestInterruptManager:
    """Тесты для InterruptManager"""
    
    @pytest.fixture
    def config(self):
        """Фикстура конфигурации"""
        return InterruptHandlingConfig()
    
    @pytest.fixture
    def manager(self, config):
        """Фикстура менеджера прерываний"""
        return InterruptManager(config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, manager):
        """Тест инициализации менеджера"""
        # Мокаем провайдеры
        with pytest.MonkeyPatch().context() as m:
            # Мокаем импорты провайдеров
            m.setattr("modules.interrupt_handling.core.interrupt_manager.GlobalFlagProvider", MagicMock())
            m.setattr("modules.interrupt_handling.core.interrupt_manager.SessionTrackerProvider", MagicMock())
            
            result = await manager.initialize()
            
            assert result is True, "Инициализация должна быть успешной"
            assert manager.is_initialized is True, "Менеджер должен быть инициализирован"
    
    def test_interrupt_session_sync(self, manager):
        """Тест прерывания сессии (синхронная версия)"""
        hardware_id = "test_hardware_123"
        
        # Проверяем начальное состояние
        assert manager.global_interrupt_flag is False, "Глобальный флаг должен быть False"
        assert manager.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None"
        
        # Тестируем установку флагов
        manager._set_global_interrupt_flags(hardware_id)
        
        assert manager.global_interrupt_flag is True, "Глобальный флаг должен быть True"
        assert manager.interrupt_hardware_id == hardware_id, "interrupt_hardware_id должен соответствовать"
        assert manager.interrupt_timestamp is not None, "interrupt_timestamp должен быть установлен"
    
    def test_should_interrupt(self, manager):
        """Тест проверки необходимости прерывания"""
        hardware_id = "test_hardware_123"
        other_hardware_id = "other_hardware_456"
        
        # Проверяем, что изначально прерывание не требуется
        assert manager.should_interrupt(hardware_id) is False, "Прерывание не должно требоваться"
        assert manager.should_interrupt(other_hardware_id) is False, "Прерывание не должно требоваться"
        
        # Устанавливаем флаг для конкретного hardware_id
        manager._set_global_interrupt_flags(hardware_id)
        
        # Проверяем, что прерывание требуется только для нужного hardware_id
        assert manager.should_interrupt(hardware_id) is True, "Прерывание должно требоваться для hardware_id"
        assert manager.should_interrupt(other_hardware_id) is False, "Прерывание не должно требоваться для другого hardware_id"
    
    def test_reset_interrupt_flags(self, manager):
        """Тест сброса флагов прерывания"""
        hardware_id = "test_hardware_123"
        
        # Устанавливаем флаги
        manager._set_global_interrupt_flags(hardware_id)
        assert manager.global_interrupt_flag is True, "Флаг должен быть установлен"
        
        # Сбрасываем флаги
        manager._reset_interrupt_flags()
        
        assert manager.global_interrupt_flag is False, "Флаг должен быть сброшен"
        assert manager.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None"
        assert manager.interrupt_timestamp is None, "interrupt_timestamp должен быть None"
    
    def test_register_unregister_session(self, manager):
        """Тест регистрации и отмены регистрации сессии"""
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
        assert session_id not in manager.active_sessions, "Сессия должна быть удалена из active_sessions"
    
    def test_unregister_nonexistent_session(self, manager):
        """Тест отмены регистрации несуществующей сессии"""
        session_id = "nonexistent_session"
        
        result = manager.unregister_session(session_id)
        assert result is False, "Отмена регистрации несуществующей сессии должна возвращать False"
    
    def test_get_statistics(self, manager):
        """Тест получения статистики"""
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
    
    def test_config_access(self, manager):
        """Тест доступа к конфигурации"""
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
    
    def test_session_counter_increment(self, manager):
        """Тест увеличения счетчика сессий"""
        initial_counter = manager.session_counter
        
        # Регистрируем сессию
        manager.register_session("session_1", "hardware_1", {})
        assert manager.session_counter == initial_counter + 1, "Счетчик сессий должен увеличиться"
        
        # Регистрируем еще одну сессию
        manager.register_session("session_2", "hardware_2", {})
        assert manager.session_counter == initial_counter + 2, "Счетчик сессий должен увеличиться еще раз"
    
    def test_multiple_sessions_same_hardware(self, manager):
        """Тест множественных сессий для одного hardware_id"""
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
