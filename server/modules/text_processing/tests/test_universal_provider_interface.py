"""
Тесты для UniversalProviderInterface
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from integration.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

class TestProvider(UniversalProviderInterface):
    """Тестовый провайдер для проверки интерфейса"""
    
    def __init__(self, name: str, priority: int, config: dict):
        super().__init__(name, priority, config)
        self._custom_health = True
    
    async def initialize(self) -> bool:
        self.is_initialized = True
        return True
    
    async def process(self, input_data):
        self.total_requests += 1
        if input_data == "error":
            self.report_error("Test error")
            yield "Error occurred"
        else:
            self.report_success()
            yield f"Processed: {input_data}"
    
    async def cleanup(self) -> bool:
        return True
    
    async def _custom_health_check(self) -> bool:
        return self._custom_health
    
    def set_custom_health(self, health: bool):
        """Установить кастомное здоровье для тестов"""
        self._custom_health = health

class TestUniversalProviderInterface:
    """Тесты для универсального интерфейса провайдеров"""
    
    def test_provider_initialization(self):
        """Тест инициализации провайдера"""
        config = {"test": "value"}
        provider = TestProvider("test_provider", 1, config)
        
        assert provider.name == "test_provider"
        assert provider.priority == 1
        assert provider.config == config
        assert provider.status == ProviderStatus.UNKNOWN
        assert provider.error_count == 0
        assert provider.last_error is None
        assert provider.last_success is None
        assert not provider.is_initialized
    
    @pytest.mark.asyncio
    async def test_provider_initialize(self):
        """Тест инициализации провайдера"""
        provider = TestProvider("test_provider", 1, {})
        
        result = await provider.initialize()
        
        assert result is True
        assert provider.is_initialized is True
    
    @pytest.mark.asyncio
    async def test_provider_process_success(self):
        """Тест успешной обработки данных"""
        provider = TestProvider("test_provider", 1, {})
        await provider.initialize()
        
        results = []
        async for result in provider.process("test_data"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Processed: test_data"
        assert provider.total_requests == 1
        assert provider.successful_requests == 1
        assert provider.failed_requests == 0
        assert provider.status == ProviderStatus.HEALTHY
        assert provider.error_count == 0
        assert provider.last_success is not None
    
    @pytest.mark.asyncio
    async def test_provider_process_error(self):
        """Тест обработки с ошибкой"""
        provider = TestProvider("test_provider", 1, {})
        await provider.initialize()
        
        results = []
        async for result in provider.process("error"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Error occurred"
        assert provider.total_requests == 1
        assert provider.successful_requests == 0
        assert provider.failed_requests == 1
        assert provider.error_count == 1
        assert provider.last_error == "Test error"
        assert provider.status == ProviderStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_provider_health_check_healthy(self):
        """Тест проверки здоровья - здоровый провайдер"""
        provider = TestProvider("test_provider", 1, {})
        await provider.initialize()
        
        health = await provider.health_check()
        
        assert health is True
    
    @pytest.mark.asyncio
    async def test_provider_health_check_not_initialized(self):
        """Тест проверки здоровья - не инициализированный провайдер"""
        provider = TestProvider("test_provider", 1, {})
        
        health = await provider.health_check()
        
        assert health is False
    
    @pytest.mark.asyncio
    async def test_provider_health_check_failed(self):
        """Тест проверки здоровья - failed провайдер"""
        provider = TestProvider("test_provider", 1, {})
        await provider.initialize()
        provider.status = ProviderStatus.FAILED
        
        health = await provider.health_check()
        
        assert health is False
    
    @pytest.mark.asyncio
    async def test_provider_health_check_custom_unhealthy(self):
        """Тест проверки здоровья - кастомная проверка unhealthy"""
        provider = TestProvider("test_provider", 1, {})
        await provider.initialize()
        provider.set_custom_health(False)
        
        health = await provider.health_check()
        
        assert health is False
    
    def test_provider_report_success(self):
        """Тест сообщения об успехе"""
        provider = TestProvider("test_provider", 1, {})
        
        provider.report_success()
        
        assert provider.status == ProviderStatus.HEALTHY
        assert provider.error_count == 0
        assert provider.last_success is not None
        assert provider.successful_requests == 1
    
    def test_provider_report_error(self):
        """Тест сообщения об ошибке"""
        provider = TestProvider("test_provider", 1, {})
        
        provider.report_error("Test error")
        
        assert provider.error_count == 1
        assert provider.last_error == "Test error"
        assert provider.failed_requests == 1
        assert provider.status == ProviderStatus.DEGRADED
    
    def test_provider_report_multiple_errors(self):
        """Тест множественных ошибок"""
        provider = TestProvider("test_provider", 1, {})
        
        # Первые 2 ошибки - DEGRADED
        provider.report_error("Error 1")
        assert provider.status == ProviderStatus.DEGRADED
        
        provider.report_error("Error 2")
        assert provider.status == ProviderStatus.DEGRADED
        
        # 3-я ошибка - FAILED
        provider.report_error("Error 3")
        assert provider.status == ProviderStatus.FAILED
        assert provider.error_count == 3
    
    def test_provider_get_status(self):
        """Тест получения статуса провайдера"""
        provider = TestProvider("test_provider", 1, {})
        
        status = provider.get_status()
        
        assert status["name"] == "test_provider"
        assert status["priority"] == 1
        assert status["status"] == ProviderStatus.UNKNOWN.value
        assert status["is_initialized"] is False
        assert status["error_count"] == 0
        assert status["last_error"] is None
        assert status["last_success"] is None
        assert status["total_requests"] == 0
        assert status["successful_requests"] == 0
        assert status["failed_requests"] == 0
        assert status["success_rate"] == 0
    
    def test_provider_get_metrics(self):
        """Тест получения метрик провайдера"""
        provider = TestProvider("test_provider", 1, {})
        
        metrics = provider.get_metrics()
        
        assert metrics["name"] == "test_provider"
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["success_rate"] == 0
        assert metrics["error_count"] == 0
        assert metrics["last_success"] is None
        assert metrics["uptime"] is None
    
    def test_provider_reset_metrics(self):
        """Тест сброса метрик провайдера"""
        provider = TestProvider("test_provider", 1, {})
        
        # Устанавливаем некоторые метрики
        provider.total_requests = 10
        provider.successful_requests = 8
        provider.failed_requests = 2
        provider.error_count = 2
        provider.last_error = "Test error"
        provider.status = ProviderStatus.DEGRADED
        
        # Сбрасываем метрики
        provider.reset_metrics()
        
        assert provider.total_requests == 0
        assert provider.successful_requests == 0
        assert provider.failed_requests == 0
        assert provider.error_count == 0
        assert provider.last_error is None
        assert provider.status == ProviderStatus.UNKNOWN
    
    def test_provider_str_representation(self):
        """Тест строкового представления провайдера"""
        provider = TestProvider("test_provider", 1, {})
        
        str_repr = str(provider)
        
        assert "test_provider" in str_repr
        assert "priority=1" in str_repr
        assert "unknown" in str_repr
    
    def test_provider_repr_representation(self):
        """Тест представления провайдера для отладки"""
        provider = TestProvider("test_provider", 1, {})
        
        repr_str = repr(provider)
        
        assert "UniversalProviderInterface" in repr_str
        assert "name='test_provider'" in repr_str
        assert "priority=1" in repr_str
        assert "status='unknown'" in repr_str
        assert "initialized=False" in repr_str
        assert "errors=0" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
