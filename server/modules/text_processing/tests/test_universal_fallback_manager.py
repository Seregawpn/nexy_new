"""
Тесты для UniversalFallbackManager
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from integration.core.universal_fallback_manager import UniversalFallbackManager
from integration.core.universal_provider_interface import UniversalProviderInterface, ProviderStatus

class TestProvider(UniversalProviderInterface):
    """Тестовый провайдер для проверки fallback менеджера"""
    
    def __init__(self, name: str, priority: int, config: dict, should_fail: bool = False):
        super().__init__(name, priority, config)
        self.should_fail = should_fail
        self.call_count = 0
    
    async def initialize(self) -> bool:
        self.is_initialized = True
        return True
    
    async def process(self, input_data):
        self.call_count += 1
        self.total_requests += 1
        
        if self.should_fail:
            self.report_error(f"Provider {self.name} failed")
            yield f"Error from {self.name}"
        else:
            self.report_success()
            yield f"Success from {self.name}"
    
    async def cleanup(self) -> bool:
        return True

class TestUniversalFallbackManager:
    """Тесты для универсального менеджера fallback"""
    
    def test_fallback_manager_initialization(self):
        """Тест инициализации менеджера fallback"""
        config = {
            'circuit_breaker_threshold': 2,
            'circuit_breaker_timeout': 60,
            'timeout': 10
        }
        manager = UniversalFallbackManager("test_module", config)
        
        assert manager.module_name == "test_module"
        assert manager.config == config
        assert manager.failure_threshold == 2
        assert manager.recovery_timeout == 60
        assert manager.timeout == 10
        assert len(manager.providers) == 0
        assert len(manager.circuit_breakers) == 0
        assert manager.total_requests == 0
        assert manager.successful_requests == 0
        assert manager.failed_requests == 0
        assert manager.fallback_switches == 0
    
    def test_register_providers(self):
        """Тест регистрации провайдеров"""
        manager = UniversalFallbackManager("test_module")
        
        provider1 = TestProvider("provider1", 2, {})
        provider2 = TestProvider("provider2", 1, {})  # Более высокий приоритет
        provider3 = TestProvider("provider3", 3, {})  # Более низкий приоритет
        
        providers = [provider1, provider2, provider3]
        manager.register_providers(providers)
        
        # Проверяем, что провайдеры отсортированы по приоритету
        assert len(manager.providers) == 3
        assert manager.providers[0].name == "provider2"  # Приоритет 1
        assert manager.providers[1].name == "provider1"  # Приоритет 2
        assert manager.providers[2].name == "provider3"  # Приоритет 3
        
        # Проверяем circuit breakers
        assert len(manager.circuit_breakers) == 3
        assert manager.circuit_breakers["provider1"] is False
        assert manager.circuit_breakers["provider2"] is False
        assert manager.circuit_breakers["provider3"] is False
    
    @pytest.mark.asyncio
    async def test_process_with_successful_provider(self):
        """Тест обработки с успешным провайдером"""
        manager = UniversalFallbackManager("test_module")
        
        provider = TestProvider("provider1", 1, {})
        manager.register_providers([provider])
        
        results = []
        async for result in manager.process_with_fallback("test_data"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Success from provider1"
        assert manager.total_requests == 1
        assert manager.successful_requests == 1
        assert manager.failed_requests == 0
        assert manager.fallback_switches == 0
        assert provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_with_fallback_switch(self):
        """Тест переключения на fallback провайдер"""
        manager = UniversalFallbackManager("test_module")
        
        provider1 = TestProvider("provider1", 1, {}, should_fail=True)
        provider2 = TestProvider("provider2", 2, {}, should_fail=False)
        manager.register_providers([provider1, provider2])
        
        results = []
        async for result in manager.process_with_fallback("test_data"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Success from provider2"
        assert manager.total_requests == 1
        assert manager.successful_requests == 1
        assert manager.failed_requests == 0
        assert manager.fallback_switches == 1
        assert provider1.call_count == 1
        assert provider2.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_with_all_providers_failed(self):
        """Тест обработки когда все провайдеры failed"""
        manager = UniversalFallbackManager("test_module")
        
        provider1 = TestProvider("provider1", 1, {}, should_fail=True)
        provider2 = TestProvider("provider2", 2, {}, should_fail=True)
        manager.register_providers([provider1, provider2])
        
        results = []
        async for result in manager.process_with_fallback("test_data"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Error: All test_module services are currently unavailable."
        assert manager.total_requests == 1
        assert manager.successful_requests == 0
        assert manager.failed_requests == 1
        assert manager.fallback_switches == 1
        assert provider1.call_count == 1
        assert provider2.call_count == 1
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(self):
        """Тест активации circuit breaker"""
        manager = UniversalFallbackManager("test_module", {
            'circuit_breaker_threshold': 2
        })
        
        provider = TestProvider("provider1", 1, {}, should_fail=True)
        manager.register_providers([provider])
        
        # Первые 2 запроса - circuit breaker не активируется
        for _ in range(2):
            results = []
            async for result in manager.process_with_fallback("test_data"):
                results.append(result)
            assert manager.circuit_breakers["provider1"] is False
        
        # 3-й запрос - circuit breaker активируется
        results = []
        async for result in manager.process_with_fallback("test_data"):
            results.append(result)
        
        assert manager.circuit_breakers["provider1"] is True
        assert provider.status == ProviderStatus.FAILED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self):
        """Тест сброса circuit breaker"""
        manager = UniversalFallbackManager("test_module", {
            'circuit_breaker_threshold': 1,
            'circuit_breaker_timeout': 0  # Немедленный сброс для теста
        })
        
        provider = TestProvider("provider1", 1, {}, should_fail=True)
        manager.register_providers([provider])
        
        # Активируем circuit breaker
        results = []
        async for result in manager.process_with_fallback("test_data"):
            results.append(result)
        
        assert manager.circuit_breakers["provider1"] is True
        
        # Проверяем сброс circuit breaker
        provider.should_fail = False  # Теперь провайдер работает
        provider.last_success = 0  # Симулируем старый успех
        
        results = []
        async for result in manager.process_with_fallback("test_data"):
            results.append(result)
        
        assert manager.circuit_breakers["provider1"] is False
    
    def test_get_status(self):
        """Тест получения статуса менеджера"""
        manager = UniversalFallbackManager("test_module")
        
        provider = TestProvider("provider1", 1, {})
        manager.register_providers([provider])
        
        status = manager.get_status()
        
        assert status["module_name"] == "test_module"
        assert status["total_requests"] == 0
        assert status["successful_requests"] == 0
        assert status["failed_requests"] == 0
        assert status["fallback_switches"] == 0
        assert status["success_rate"] == 0
        assert "provider1" in status["providers"]
        assert "config" in status
    
    def test_get_metrics(self):
        """Тест получения метрик менеджера"""
        manager = UniversalFallbackManager("test_module")
        
        provider = TestProvider("provider1", 1, {})
        manager.register_providers([provider])
        
        metrics = manager.get_metrics()
        
        assert metrics["module_name"] == "test_module"
        assert metrics["total_requests"] == 0
        assert metrics["successful_requests"] == 0
        assert metrics["failed_requests"] == 0
        assert metrics["fallback_switches"] == 0
        assert metrics["success_rate"] == 0
        assert metrics["active_providers"] == 1
        assert metrics["failed_providers"] == 0
        assert metrics["provider_count"] == 1
    
    def test_reset_metrics(self):
        """Тест сброса метрик менеджера"""
        manager = UniversalFallbackManager("test_module")
        
        provider = TestProvider("provider1", 1, {})
        manager.register_providers([provider])
        
        # Устанавливаем некоторые метрики
        manager.total_requests = 10
        manager.successful_requests = 8
        manager.failed_requests = 2
        manager.fallback_switches = 3
        provider.error_count = 2
        manager.circuit_breakers["provider1"] = True
        
        # Сбрасываем метрики
        manager.reset_metrics()
        
        assert manager.total_requests == 0
        assert manager.successful_requests == 0
        assert manager.failed_requests == 0
        assert manager.fallback_switches == 0
        assert provider.error_count == 0
        assert manager.circuit_breakers["provider1"] is False
    
    def test_get_healthy_providers(self):
        """Тест получения здоровых провайдеров"""
        manager = UniversalFallbackManager("test_module")
        
        provider1 = TestProvider("provider1", 1, {})
        provider2 = TestProvider("provider2", 2, {})
        manager.register_providers([provider1, provider2])
        
        # Все провайдеры здоровы
        healthy = manager.get_healthy_providers()
        assert len(healthy) == 2
        
        # Отключаем один провайдер
        manager.circuit_breakers["provider1"] = True
        
        healthy = manager.get_healthy_providers()
        assert len(healthy) == 1
        assert healthy[0].name == "provider2"
    
    def test_get_failed_providers(self):
        """Тест получения failed провайдеров"""
        manager = UniversalFallbackManager("test_module")
        
        provider1 = TestProvider("provider1", 1, {})
        provider2 = TestProvider("provider2", 2, {})
        manager.register_providers([provider1, provider2])
        
        # Все провайдеры здоровы
        failed = manager.get_failed_providers()
        assert len(failed) == 0
        
        # Отключаем один провайдер
        manager.circuit_breakers["provider1"] = True
        
        failed = manager.get_failed_providers()
        assert len(failed) == 1
        assert failed[0].name == "provider1"
    
    def test_str_representation(self):
        """Тест строкового представления менеджера"""
        manager = UniversalFallbackManager("test_module")
        
        str_repr = str(manager)
        
        assert "test_module" in str_repr
        assert "providers=0" in str_repr
    
    def test_repr_representation(self):
        """Тест представления менеджера для отладки"""
        manager = UniversalFallbackManager("test_module")
        
        repr_str = repr(manager)
        
        assert "UniversalFallbackManager" in repr_str
        assert "module_name='test_module'" in repr_str
        assert "providers=0" in repr_str
        assert "success_rate=0.00" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
