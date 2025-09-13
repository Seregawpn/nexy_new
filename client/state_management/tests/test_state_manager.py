"""
Тесты для модуля управления состояниями
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock

from state_management.core.state_manager import StateManager
from state_management.core.types import AppState, StateConfig
from state_management.core.state_validator import StateValidator
from state_management.monitoring.state_monitor import StateMonitor
from state_management.recovery.state_recovery import StateRecovery


class TestStateValidator:
    """Тесты для валидатора состояний"""
    
    def setup_method(self):
        self.validator = StateValidator()
    
    def test_can_transition_valid(self):
        """Тест валидных переходов"""
        assert self.validator.can_transition(AppState.SLEEPING, AppState.LISTENING)
        assert self.validator.can_transition(AppState.LISTENING, AppState.PROCESSING)
        assert self.validator.can_transition(AppState.PROCESSING, AppState.SLEEPING)
        assert self.validator.can_transition(AppState.ERROR, AppState.SLEEPING)
    
    def test_can_transition_invalid(self):
        """Тест невалидных переходов"""
        assert not self.validator.can_transition(AppState.SLEEPING, AppState.PROCESSING)
        assert not self.validator.can_transition(AppState.PROCESSING, AppState.LISTENING)
        assert not self.validator.can_transition(AppState.SHUTDOWN, AppState.SLEEPING)
    
    def test_can_transition_same_state(self):
        """Тест перехода в то же состояние"""
        assert self.validator.can_transition(AppState.SLEEPING, AppState.SLEEPING)
    
    def test_validate_state(self):
        """Тест валидации состояния"""
        assert self.validator.validate_state(AppState.SLEEPING)
        assert self.validator.validate_state(AppState.LISTENING)
        assert not self.validator.validate_state("invalid_state")
    
    def test_get_transition_type(self):
        """Тест определения типа перехода"""
        assert self.validator.get_transition_type(AppState.SLEEPING, AppState.LISTENING) is not None
        assert self.validator.get_transition_type(AppState.SLEEPING, AppState.SLEEPING) is None


class TestStateMonitor:
    """Тесты для монитора состояний"""
    
    def setup_method(self):
        self.monitor = StateMonitor()
    
    def test_record_transition(self):
        """Тест записи перехода"""
        self.monitor.record_transition(AppState.SLEEPING, AppState.LISTENING, 1.0, True, "test")
        
        metrics = self.monitor.get_metrics()
        assert metrics.total_transitions == 1
        assert metrics.successful_transitions == 1
        assert metrics.failed_transitions == 0
    
    def test_record_error(self):
        """Тест записи ошибки"""
        self.monitor.record_error(Exception("test error"), "test context")
        
        metrics = self.monitor.get_metrics()
        assert metrics.error_count == 1
    
    def test_record_recovery(self):
        """Тест записи восстановления"""
        self.monitor.record_recovery()
        
        metrics = self.monitor.get_metrics()
        assert metrics.recovery_count == 1
    
    def test_get_success_rate(self):
        """Тест получения процента успешности"""
        self.monitor.record_transition(AppState.SLEEPING, AppState.LISTENING, 1.0, True, "test")
        self.monitor.record_transition(AppState.LISTENING, AppState.PROCESSING, 1.0, False, "test")
        
        success_rate = self.monitor.get_success_rate()
        assert success_rate == 0.5


class TestStateRecovery:
    """Тесты для системы восстановления"""
    
    def setup_method(self):
        self.recovery = StateRecovery()
        self.state_manager = Mock()
        self.recovery.set_state_manager(self.state_manager)
    
    @pytest.mark.asyncio
    async def test_recover_from_error(self):
        """Тест восстановления из ошибки"""
        self.state_manager._transition_to_state = AsyncMock(return_value=True)
        
        result = await self.recovery._recover_from_error(Exception("test error"))
        assert result is True
        self.state_manager._transition_to_state.assert_called_once_with(AppState.SLEEPING, "error_recovery")
    
    @pytest.mark.asyncio
    async def test_recover_from_processing(self):
        """Тест восстановления из обработки"""
        self.state_manager._transition_to_state = AsyncMock(return_value=True)
        
        result = await self.recovery._recover_from_processing(Exception("test error"))
        assert result is True
        self.state_manager._transition_to_state.assert_called_once_with(AppState.SLEEPING, "processing_recovery")
    
    @pytest.mark.asyncio
    async def test_recover_with_retry_success(self):
        """Тест восстановления с повторными попытками (успех)"""
        self.state_manager._transition_to_state = AsyncMock(return_value=True)
        
        result = await self.recovery.recover_with_retry(AppState.ERROR, Exception("test error"))
        assert result is True


class TestStateManager:
    """Тесты для основного менеджера состояний"""
    
    def setup_method(self):
        self.config = StateConfig()
        self.state_manager = StateManager(self.config)
    
    def test_initial_state(self):
        """Тест начального состояния"""
        assert self.state_manager.state == AppState.SLEEPING
        assert self.state_manager.is_sleeping()
        assert not self.state_manager.is_listening()
        assert not self.state_manager.is_processing()
        assert not self.state_manager.is_error()
        assert not self.state_manager.is_shutdown()
    
    def test_state_property(self):
        """Тест свойства состояния"""
        self.state_manager.state = AppState.LISTENING
        assert self.state_manager.state == AppState.LISTENING
        assert self.state_manager.is_listening()
    
    def test_get_state_name(self):
        """Тест получения имени состояния"""
        assert self.state_manager.get_state_name() == "sleeping"
        self.state_manager.state = AppState.LISTENING
        assert self.state_manager.get_state_name() == "listening"
    
    @pytest.mark.asyncio
    async def test_start_listening(self):
        """Тест начала прослушивания"""
        result = await self.state_manager.start_listening()
        assert result is True
        assert self.state_manager.state == AppState.LISTENING
    
    @pytest.mark.asyncio
    async def test_stop_listening(self):
        """Тест остановки прослушивания"""
        self.state_manager.state = AppState.LISTENING
        result = await self.state_manager.stop_listening()
        assert result is True
        assert self.state_manager.state == AppState.SLEEPING
    
    @pytest.mark.asyncio
    async def test_start_processing(self):
        """Тест начала обработки"""
        self.state_manager.state = AppState.LISTENING
        result = await self.state_manager.start_processing()
        assert result is True
        assert self.state_manager.state == AppState.PROCESSING
    
    @pytest.mark.asyncio
    async def test_stop_processing(self):
        """Тест остановки обработки"""
        self.state_manager.state = AppState.PROCESSING
        result = await self.state_manager.stop_processing()
        assert result is True
        assert self.state_manager.state == AppState.SLEEPING
    
    @pytest.mark.asyncio
    async def test_error_state(self):
        """Тест состояния ошибки"""
        result = await self.state_manager.error(Exception("test error"), "test context")
        assert result is True
        assert self.state_manager.state == AppState.ERROR
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Тест завершения работы"""
        result = await self.state_manager.shutdown()
        assert result is True
        assert self.state_manager.state == AppState.SHUTDOWN
    
    def test_callbacks(self):
        """Тест установки callback'ов"""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        
        self.state_manager.set_state_changed_callback(callback1)
        self.state_manager.set_error_callback(callback2)
        self.state_manager.set_recovery_callback(callback3)
        
        assert self.state_manager.on_state_changed == callback1
        assert self.state_manager.on_error == callback2
        assert self.state_manager.on_recovery == callback3
    
    def test_metrics(self):
        """Тест получения метрик"""
        metrics = self.state_manager.get_metrics()
        assert metrics is not None
        assert metrics.total_transitions == 0
    
    def test_state_history(self):
        """Тест получения истории состояний"""
        history = self.state_manager.get_state_history()
        assert isinstance(history, list)
        assert len(history) == 0


@pytest.mark.asyncio
async def test_integration():
    """Интеграционный тест"""
    config = StateConfig()
    state_manager = StateManager(config)
    
    # Начинаем прослушивание
    await state_manager.start_listening()
    assert state_manager.is_listening()
    
    # Переходим к обработке
    await state_manager.start_processing()
    assert state_manager.is_processing()
    
    # Завершаем обработку
    await state_manager.stop_processing()
    assert state_manager.is_sleeping()
    
    # Проверяем метрики
    metrics = state_manager.get_metrics()
    assert metrics.total_transitions >= 3
    assert metrics.successful_transitions >= 3


if __name__ == "__main__":
    pytest.main([__file__])
