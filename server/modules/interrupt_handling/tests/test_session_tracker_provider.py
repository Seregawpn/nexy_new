"""
Unit тесты для SessionTrackerProvider
"""

import pytest
import time
from modules.interrupt_handling.providers.session_tracker_provider import SessionTrackerProvider
from modules.interrupt_handling.config import InterruptHandlingConfig

class TestSessionTrackerProvider:
    """Тесты для SessionTrackerProvider"""
    
    @pytest.fixture
    def config(self):
        """Фикстура конфигурации"""
        return InterruptHandlingConfig()
    
    @pytest.fixture
    def provider(self, config):
        """Фикстура провайдера отслеживания сессий"""
        return SessionTrackerProvider(config.config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, provider):
        """Тест инициализации провайдера"""
        result = await provider.initialize()
        
        assert result is True, "Инициализация должна быть успешной"
        assert provider.is_initialized is True, "Провайдер должен быть инициализирован"
        assert len(provider.active_sessions) == 0, "Активные сессии должны быть пустыми"
        assert provider.session_counter == 0, "Счетчик сессий должен быть 0"
    
    @pytest.mark.asyncio
    async def test_register_session(self, provider):
        """Тест регистрации сессии"""
        await provider.initialize()
        
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
    async def test_register_session_without_id(self, provider):
        """Тест регистрации сессии без ID"""
        await provider.initialize()
        
        result = await provider.register_session("", "hardware_456", {})
        
        assert result["success"] is False, "Регистрация сессии без ID должна быть неуспешной"
        assert "Session ID is required" in result["error"], "Должно быть сообщение об ошибке"
    
    @pytest.mark.asyncio
    async def test_unregister_session(self, provider):
        """Тест отмены регистрации сессии"""
        await provider.initialize()
        
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
    
    @pytest.mark.asyncio
    async def test_unregister_nonexistent_session(self, provider):
        """Тест отмены регистрации несуществующей сессии"""
        await provider.initialize()
        
        result = await provider.unregister_session("nonexistent_session")
        
        assert result["success"] is False, "Отмена регистрации несуществующей сессии должна быть неуспешной"
        assert "not found" in result["error"], "Должно быть сообщение об ошибке"
    
    @pytest.mark.asyncio
    async def test_cleanup_sessions_for_hardware(self, provider):
        """Тест очистки сессий для hardware_id"""
        await provider.initialize()
        
        hardware_id = "hardware_123"
        other_hardware_id = "hardware_456"
        
        # Регистрируем несколько сессий
        await provider.register_session("session_1", hardware_id, {"test": "data1"})
        await provider.register_session("session_2", hardware_id, {"test": "data2"})
        await provider.register_session("session_3", other_hardware_id, {"test": "data3"})
        
        assert len(provider.active_sessions) == 3, "Должно быть 3 активные сессии"
        
        # Очищаем сессии для конкретного hardware_id
        result = await provider.cleanup_sessions_for_hardware(hardware_id)
        
        assert result["success"] is True, "Очистка сессий должна быть успешной"
        assert result["hardware_id"] == hardware_id, "hardware_id должен соответствовать"
        assert result["sessions_count"] == 2, "Должно быть очищено 2 сессии"
        assert result["remaining_sessions"] == 1, "Должна остаться 1 сессия"
        
        # Проверяем, что сессии для hardware_id удалены
        assert "session_1" not in provider.active_sessions, "session_1 должна быть удалена"
        assert "session_2" not in provider.active_sessions, "session_2 должна быть удалена"
        assert "session_3" in provider.active_sessions, "session_3 должна остаться"
        assert provider.total_sessions_cleaned == 2, "Счетчик очищенных сессий должен быть 2"
    
    def test_get_session_status(self, provider):
        """Тест получения статуса сессии"""
        session_id = "session_123"
        hardware_id = "hardware_456"
        session_data = {"test": "data"}
        
        # Регистрируем сессию
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
    
    def test_get_session_status_nonexistent(self, provider):
        """Тест получения статуса несуществующей сессии"""
        result = provider.get_session_status("nonexistent_session")
        
        assert result["found"] is False, "Несуществующая сессия не должна быть найдена"
        assert result["session_id"] == "nonexistent_session", "session_id должен соответствовать"
    
    def test_get_all_sessions(self, provider):
        """Тест получения всех сессий"""
        # Регистрируем несколько сессий
        provider.active_sessions["session_1"] = {
            "session_id": "session_1",
            "hardware_id": "hardware_123",
            "start_time": time.time(),
            "last_activity": time.time(),
            "data": {},
            "status": "active"
        }
        provider.active_sessions["session_2"] = {
            "session_id": "session_2", 
            "hardware_id": "hardware_456",
            "start_time": time.time(),
            "last_activity": time.time(),
            "data": {},
            "status": "active"
        }
        
        result = provider.get_all_sessions()
        
        assert result["total_sessions"] == 2, "Общее количество сессий должно быть 2"
        assert len(result["sessions"]) == 2, "Должно быть 2 сессии в списке"
        
        # Проверяем структуру каждой сессии
        for session_info in result["sessions"]:
            assert "session_id" in session_info, "Сессия должна содержать session_id"
            assert "hardware_id" in session_info, "Сессия должна содержать hardware_id"
            assert "duration" in session_info, "Сессия должна содержать duration"
            assert "status" in session_info, "Сессия должна содержать status"
    
    def test_get_tracker_status(self, provider):
        """Тест получения статуса трекера"""
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
    
    @pytest.mark.asyncio
    async def test_process_operations(self, provider):
        """Тест обработки различных операций"""
        await provider.initialize()
        
        session_id = "session_123"
        hardware_id = "hardware_456"
        session_data = {"test": "data"}
        
        # Тест операции register_session
        result = await provider.process({
            "operation": "register_session",
            "session_id": session_id,
            "hardware_id": hardware_id,
            "session_data": session_data
        })
        assert result["success"] is True, "Операция register_session должна быть успешной"
        
        # Тест операции get_session_status
        result = provider.process({
            "operation": "get_session_status",
            "session_id": session_id
        })
        assert result["found"] is True, "Сессия должна быть найдена"
        
        # Тест операции unregister_session
        result = await provider.process({
            "operation": "unregister_session",
            "session_id": session_id
        })
        assert result["success"] is True, "Операция unregister_session должна быть успешной"
        
        # Тест операции get_status
        result = provider.process({"operation": "get_status"})
        assert "active_sessions" in result, "Статус должен содержать active_sessions"
    
    @pytest.mark.asyncio
    async def test_process_unknown_operation(self, provider):
        """Тест обработки неизвестной операции"""
        await provider.initialize()
        
        result = await provider.process({"operation": "unknown_operation"})
        assert result["success"] is False, "Неизвестная операция должна возвращать False"
        assert "Unknown operation" in result["error"], "Должно быть сообщение об ошибке"
    
    @pytest.mark.asyncio
    async def test_cleanup(self, provider):
        """Тест очистки ресурсов"""
        await provider.initialize()
        
        # Регистрируем несколько сессий
        await provider.register_session("session_1", "hardware_1", {})
        await provider.register_session("session_2", "hardware_2", {})
        
        # Очищаем ресурсы
        result = await provider.cleanup()
        
        assert result is True, "Очистка должна быть успешной"
        assert provider.is_initialized is False, "Провайдер не должен быть инициализирован"
        assert len(provider.active_sessions) == 0, "Активные сессии должны быть очищены"
        assert provider.total_sessions_created == 0, "Счетчик созданных сессий должен быть сброшен"
    
    def test_max_concurrent_sessions_tracking(self, provider):
        """Тест отслеживания максимального количества одновременных сессий"""
        # Регистрируем сессии
        provider.active_sessions["session_1"] = {"start_time": time.time()}
        provider.active_sessions["session_2"] = {"start_time": time.time()}
        provider.active_sessions["session_3"] = {"start_time": time.time()}
        
        # Проверяем, что max_concurrent_sessions обновился
        assert provider.max_concurrent_sessions == 3, "Максимальное количество сессий должно быть 3"
        
        # Удаляем одну сессию
        del provider.active_sessions["session_1"]
        
        # max_concurrent_sessions не должен уменьшиться
        assert provider.max_concurrent_sessions == 3, "Максимальное количество сессий не должно уменьшиться"
