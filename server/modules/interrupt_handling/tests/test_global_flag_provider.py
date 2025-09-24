"""
Unit тесты для GlobalFlagProvider
"""

import pytest
import time
from modules.interrupt_handling.providers.global_flag_provider import GlobalFlagProvider
from modules.interrupt_handling.config import InterruptHandlingConfig

class TestGlobalFlagProvider:
    """Тесты для GlobalFlagProvider"""
    
    @pytest.fixture
    def config(self):
        """Фикстура конфигурации"""
        return InterruptHandlingConfig()
    
    @pytest.fixture
    def provider(self, config):
        """Фикстура провайдера глобальных флагов"""
        return GlobalFlagProvider(config.config)
    
    @pytest.mark.asyncio
    async def test_initialization(self, provider):
        """Тест инициализации провайдера"""
        result = await provider.initialize()
        
        assert result is True, "Инициализация должна быть успешной"
        assert provider.is_initialized is True, "Провайдер должен быть инициализирован"
        assert provider.global_interrupt_flag is False, "Глобальный флаг должен быть False по умолчанию"
        assert provider.interrupt_hardware_id is None, "interrupt_hardware_id должен быть None по умолчанию"
    
    @pytest.mark.asyncio
    async def test_set_interrupt_flag(self, provider):
        """Тест установки флага прерывания"""
        await provider.initialize()
        
        hardware_id = "test_hardware_123"
        result = await provider.set_interrupt_flag(hardware_id)
        
        assert result["success"] is True, "Установка флага должна быть успешной"
        assert result["hardware_id"] == hardware_id, "hardware_id должен соответствовать"
        assert provider.global_interrupt_flag is True, "Глобальный флаг должен быть установлен"
        assert provider.interrupt_hardware_id == hardware_id, "interrupt_hardware_id должен соответствовать"
        assert provider.interrupt_timestamp is not None, "interrupt_timestamp должен быть установлен"
        assert provider.flag_set_count == 1, "Счетчик установок должен увеличиться"
    
    @pytest.mark.asyncio
    async def test_reset_flags(self, provider):
        """Тест сброса флагов"""
        await provider.initialize()
        
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
    
    def test_check_interrupt_flag(self, provider):
        """Тест проверки флага прерывания"""
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
    
    def test_check_interrupt_flag_timeout(self, provider):
        """Тест проверки флага прерывания с таймаутом"""
        hardware_id = "test_hardware_123"
        
        # Устанавливаем флаг с устаревшим timestamp
        provider.global_interrupt_flag = True
        provider.interrupt_hardware_id = hardware_id
        provider.interrupt_timestamp = time.time() - 10  # 10 секунд назад
        
        result = provider.check_interrupt_flag(hardware_id)
        assert result["should_interrupt"] is False, "Прерывание не должно требоваться при истечении таймаута"
        assert result["timeout_expired"] is True, "Таймаут должен быть истекшим"
    
    def test_get_flag_status(self, provider):
        """Тест получения статуса флагов"""
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
    
    @pytest.mark.asyncio
    async def test_process_operations(self, provider):
        """Тест обработки различных операций"""
        await provider.initialize()
        
        hardware_id = "test_hardware_123"
        
        # Тест операции set_interrupt_flag
        result = await provider.process({"operation": "set_interrupt_flag", "hardware_id": hardware_id})
        assert result["success"] is True, "Операция set_interrupt_flag должна быть успешной"
        
        # Тест операции check_flag
        result = provider.process({"operation": "check_flag", "hardware_id": hardware_id})
        assert result["should_interrupt"] is True, "Проверка флага должна возвращать True"
        
        # Тест операции reset_flags
        result = await provider.process({"operation": "reset_flags"})
        assert result["success"] is True, "Операция reset_flags должна быть успешной"
        
        # Тест операции get_status
        result = provider.process({"operation": "get_status"})
        assert "global_interrupt_flag" in result, "Статус должен содержать global_interrupt_flag"
    
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
        
        # Устанавливаем некоторые данные
        await provider.set_interrupt_flag("test_hardware")
        
        # Очищаем ресурсы
        result = await provider.cleanup()
        
        assert result is True, "Очистка должна быть успешной"
        assert provider.is_initialized is False, "Провайдер не должен быть инициализирован"
        assert provider.global_interrupt_flag is False, "Глобальный флаг должен быть сброшен"
        assert provider.flag_set_count == 0, "Счетчик установок должен быть сброшен"
    
    def test_flag_statistics(self, provider):
        """Тест статистики флагов"""
        # Проверяем начальную статистику
        stats = provider.get_flag_status()
        assert stats['flag_set_count'] == 0, "Начальный счетчик установок должен быть 0"
        assert stats['flag_reset_count'] == 0, "Начальный счетчик сбросов должен быть 0"
    
    @pytest.mark.asyncio
    async def test_multiple_flag_operations(self, provider):
        """Тест множественных операций с флагами"""
        await provider.initialize()
        
        hardware_id = "test_hardware_123"
        
        # Множественные установки и сбросы
        for i in range(3):
            await provider.set_interrupt_flag(f"{hardware_id}_{i}")
            await provider.reset_flags()
        
        stats = provider.get_flag_status()
        assert stats['flag_set_count'] == 3, "Счетчик установок должен быть 3"
        assert stats['flag_reset_count'] == 3, "Счетчик сбросов должен быть 3"
