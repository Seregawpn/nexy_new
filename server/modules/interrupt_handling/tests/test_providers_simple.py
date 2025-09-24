"""
Упрощенные тесты для провайдеров Interrupt Handling Module
"""

import pytest
import asyncio
import time
from modules.interrupt_handling.providers.global_flag_provider import GlobalFlagProvider
from modules.interrupt_handling.providers.session_tracker_provider import SessionTrackerProvider
from modules.interrupt_handling.config import InterruptHandlingConfig

class TestGlobalFlagProviderSimple:
    """Упрощенные тесты для GlobalFlagProvider"""
    
    def test_provider_creation(self):
        """Тест создания провайдера"""
        config = InterruptHandlingConfig()
        provider = GlobalFlagProvider(config.config)
        
        # Проверяем, что провайдер создался
        assert provider is not None, "Провайдер должен быть создан"
        assert provider.name == "global_flag_provider", "Имя должно соответствовать"
        assert hasattr(provider, 'global_interrupt_flag'), "Должен иметь global_interrupt_flag"
        assert hasattr(provider, 'interrupt_hardware_id'), "Должен иметь interrupt_hardware_id"
    
    def test_initial_state(self):
        """Тест начального состояния"""
        config = InterruptHandlingConfig()
        provider = GlobalFlagProvider(config.config)
        
        # Проверяем начальное состояние
        assert provider.global_interrupt_flag is False, "Глобальный флаг должен быть False"
        assert provider.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None"
        assert provider.interrupt_timestamp is None, "interrupt_timestamp должен быть None"
        assert provider.flag_set_count == 0, "Счетчик установок должен быть 0"
        assert provider.flag_reset_count == 0, "Счетчик сбросов должен быть 0"
    
    @pytest.mark.asyncio
    async def test_set_interrupt_flag(self):
        """Тест установки флага прерывания"""
        config = InterruptHandlingConfig()
        provider = GlobalFlagProvider(config.config)
        
        hardware_id = "test_hardware_123"
        result = await provider.set_interrupt_flag(hardware_id)
        
        assert result["success"] is True, "Установка флага должна быть успешной"
        assert result["hardware_id"] == hardware_id, "hardware_id должен соответствовать"
        assert provider.global_interrupt_flag is True, "Глобальный флаг должен быть установлен"
        assert provider.interrupt_hardware_id == hardware_id, "interrupt_hardware_id должен соответствовать"
        assert provider.interrupt_timestamp is not None, "interrupt_timestamp должен быть установлен"
        assert provider.flag_set_count == 1, "Счетчик установок должен увеличиться"
    
    @pytest.mark.asyncio
    async def test_reset_flags(self):
        """Тест сброса флагов"""
        config = InterruptHandlingConfig()
        provider = GlobalFlagProvider(config.config)
        
        # Сначала устанавливаем флаг
        hardware_id = "test_hardware_123"
        await provider.set_interrupt_flag(hardware_id)
        
        # Затем сбрасываем
        result = await provider.reset_flags()
        
        assert result["success"] is True, "Сброс флагов должен быть успешным"
        assert result["old_hardware_id"] == hardware_id, "Старый hardware_id должен соответствовать"
        assert provider.global_interrupt_flag is False, "Глобальный флаг должен быть сброшен"
        assert provider.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None"
        assert provider.interrupt_timestamp is None, "interrupt_timestamp должен быть None"
        assert provider.flag_reset_count == 1, "Счетчик сбросов должен увеличиться"
    
    def test_check_interrupt_flag(self):
        """Тест проверки флага прерывания"""
        config = InterruptHandlingConfig()
        provider = GlobalFlagProvider(config.config)
        
        hardware_id = "test_hardware_123"
        other_hardware_id = "other_hardware_456"
        
        # Проверяем изначальное состояние
        result = provider.check_interrupt_flag(hardware_id)
        assert result["should_interrupt"] is False, "Прерывание не должно требоваться изначально"
        assert result["global_flag"] is False, "Глобальный флаг должен быть False"
        
        # Устанавливаем флаг вручную
        provider.global_interrupt_flag = True
        provider.interrupt_hardware_id = hardware_id
        
        # Проверяем для правильного hardware_id
        result = provider.check_interrupt_flag(hardware_id)
        assert result["should_interrupt"] is True, "Прерывание должно требоваться для правильного hardware_id"
        assert result["global_flag"] is True, "Глобальный флаг должен быть True"
        assert result["interrupt_hardware_id"] == hardware_id, "interrupt_hardware_id должен соответствовать"
        
        # Проверяем для другого hardware_id
        result = provider.check_interrupt_flag(other_hardware_id)
        assert result["should_interrupt"] is False, "Прерывание не должно требоваться для другого hardware_id"
    
    def test_get_flag_status(self):
        """Тест получения статуса флагов"""
        config = InterruptHandlingConfig()
        provider = GlobalFlagProvider(config.config)
        
        result = provider.get_flag_status()
        
        # Проверяем структуру результата
        required_keys = [
            'global_interrupt_flag',
            'interrupt_hardware_id',
            'interrupt_timestamp',
            'flag_set_count',
            'flag_reset_count',
            'last_interrupt_time',
            'uptime'
        ]
        
        for key in required_keys:
            assert key in result, f"Статус флагов должен содержать ключ {key}"
        
        # Проверяем начальные значения
        assert result['global_interrupt_flag'] is False, "Глобальный флаг должен быть False"
        assert result['interrupt_hardware_id'] is None, "interrupt_hardware_id должен быть None"
        assert result['flag_set_count'] == 0, "Счетчик установок должен быть 0"
        assert result['flag_reset_count'] == 0, "Счетчик сбросов должен быть 0"

class TestSessionTrackerProviderSimple:
    """Упрощенные тесты для SessionTrackerProvider"""
    
    def test_provider_creation(self):
        """Тест создания провайдера"""
        config = InterruptHandlingConfig()
        provider = SessionTrackerProvider(config.config)
        
        # Проверяем, что провайдер создался
        assert provider is not None, "Провайдер должен быть создан"
        assert provider.name == "session_tracker_provider", "Имя должно соответствовать"
        assert hasattr(provider, 'active_sessions'), "Должен иметь active_sessions"
        assert hasattr(provider, 'session_counter'), "Должен иметь session_counter"
    
    def test_initial_state(self):
        """Тест начального состояния"""
        config = InterruptHandlingConfig()
        provider = SessionTrackerProvider(config.config)
        
        # Проверяем начальное состояние
        assert len(provider.active_sessions) == 0, "Активные сессии должны быть пустыми"
        assert provider.session_counter == 0, "Счетчик сессий должен быть 0"
        assert provider.total_sessions_created == 0, "Счетчик созданных сессий должен быть 0"
        assert provider.total_sessions_cleaned == 0, "Счетчик очищенных сессий должен быть 0"
        assert provider.max_concurrent_sessions == 0, "Максимальное количество сессий должно быть 0"
    
    @pytest.mark.asyncio
    async def test_register_session(self):
        """Тест регистрации сессии"""
        config = InterruptHandlingConfig()
        provider = SessionTrackerProvider(config.config)
        
        session_id = "session_123"
        hardware_id = "hardware_456"
        session_data = {"test": "data", "user_id": "user_789"}
        
        result = await provider.register_session(session_id, hardware_id, session_data)
        
        assert result["success"] is True, "Регистрация сессии должна быть успешной"
        assert result["session_id"] == session_id, "session_id должен соответствовать"
        assert result["hardware_id"] == hardware_id, "hardware_id должен соответствовать"
        assert result["total_sessions"] == 1, "Общее количество сессий должно быть 1"
        
        # Проверяем, что сессия зарегистрирована
        assert session_id in provider.active_sessions, "Сессия должна быть в active_sessions"
        assert provider.total_sessions_created == 1, "Счетчик созданных сессий должен увеличиться"
    
    @pytest.mark.asyncio
    async def test_unregister_session(self):
        """Тест отмены регистрации сессии"""
        config = InterruptHandlingConfig()
        provider = SessionTrackerProvider(config.config)
        
        session_id = "session_123"
        hardware_id = "hardware_456"
        session_data = {"test": "data"}
        
        # Сначала регистрируем сессию
        await provider.register_session(session_id, hardware_id, session_data)
        assert len(provider.active_sessions) == 1, "Должна быть 1 активная сессия"
        
        # Затем отменяем регистрацию
        result = await provider.unregister_session(session_id)
        
        assert result["success"] is True, "Отмена регистрации должна быть успешной"
        assert result["session_id"] == session_id, "session_id должен соответствовать"
        assert result["total_sessions"] == 0, "Общее количество сессий должно быть 0"
        assert result["duration"] > 0, "Продолжительность сессии должна быть положительной"
        
        # Проверяем, что сессия удалена
        assert session_id not in provider.active_sessions, "Сессия должна быть удалена"
        assert provider.total_sessions_cleaned == 1, "Счетчик очищенных сессий должен увеличиться"
    
    def test_get_session_status(self):
        """Тест получения статуса сессии"""
        config = InterruptHandlingConfig()
        provider = SessionTrackerProvider(config.config)
        
        session_id = "session_123"
        hardware_id = "hardware_456"
        session_data = {"test": "data"}
        
        # Регистрируем сессию вручную
        provider.active_sessions[session_id] = {
            "session_id": session_id,
            "hardware_id": hardware_id,
            "start_time": time.time(),
            "last_activity": time.time(),
            "data": session_data,
            "status": "active"
        }
        
        result = provider.get_session_status(session_id)
        
        assert result["found"] is True, "Сессия должна быть найдена"
        assert result["session_id"] == session_id, "session_id должен соответствовать"
        assert result["hardware_id"] == hardware_id, "hardware_id должен соответствовать"
        assert result["duration"] >= 0, "Продолжительность должна быть неотрицательной"
        assert result["status"] == "active", "Статус должен быть 'active'"
        assert result["data_keys"] == ["test"], "Ключи данных должны соответствовать"
    
    def test_get_tracker_status(self):
        """Тест получения статуса трекера"""
        config = InterruptHandlingConfig()
        provider = SessionTrackerProvider(config.config)
        
        # Устанавливаем некоторые данные
        provider.total_sessions_created = 5
        provider.total_sessions_cleaned = 3
        provider.max_concurrent_sessions = 2
        provider.session_counter = 5
        
        result = provider.get_tracker_status()
        
        # Проверяем структуру результата
        required_keys = [
            'active_sessions',
            'total_created',
            'total_cleaned',
            'max_concurrent',
            'session_counter',
            'timestamp'
        ]
        
        for key in required_keys:
            assert key in result, f"Статус трекера должен содержать ключ {key}"
        
        # Проверяем значения
        assert result['total_created'] == 5, "total_created должен соответствовать"
        assert result['total_cleaned'] == 3, "total_cleaned должен соответствовать"
        assert result['max_concurrent'] == 2, "max_concurrent должен соответствовать"
        assert result['session_counter'] == 5, "session_counter должен соответствовать"
