"""
Тесты для FallbackManager модуля Text Processing
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from modules.text_processing.fallback_manager import TextProcessingFallbackManager
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

class TestTextProcessingFallbackManager:
    """Тесты для fallback менеджера модуля обработки текста"""
    
    def test_fallback_manager_initialization(self):
        """Тест инициализации fallback менеджера"""
        config = {
            'circuit_breaker_threshold': 2,
            'circuit_breaker_timeout': 60,
            'fallback_timeout': 10
        }
        
        manager = TextProcessingFallbackManager(config)
        
        assert len(manager.providers) == 0
        assert manager.fallback_manager is not None
        assert manager.fallback_manager.module_name == "text_processing"
    
    def test_register_providers(self):
        """Тест регистрации провайдеров"""
        manager = TextProcessingFallbackManager()
        
        provider1 = TestProvider("gemini_live", 1, {})
        provider2 = TestProvider("langchain", 2, {})
        
        providers = [provider1, provider2]
        manager.register_providers(providers)
        
        assert len(manager.providers) == 2
        assert manager.providers[0].name == "gemini_live"
        assert manager.providers[1].name == "langchain"
    
    @pytest.mark.asyncio
    async def test_process_text_success(self):
        """Тест успешной обработки текста"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        results = []
        async for result in manager.process_text("Hello world"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Success from gemini_live"
        assert provider.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_text_with_fallback(self):
        """Тест обработки текста с fallback"""
        manager = TextProcessingFallbackManager()
        
        provider1 = TestProvider("gemini_live", 1, {}, should_fail=True)
        provider2 = TestProvider("langchain", 2, {}, should_fail=False)
        manager.register_providers([provider1, provider2])
        
        results = []
        async for result in manager.process_text("Hello world"):
            results.append(result)
        
        assert len(results) == 1
        assert results[0] == "Success from langchain"
        assert provider1.call_count == 1
        assert provider2.call_count == 1
    
    @pytest.mark.asyncio
    async def test_process_text_all_providers_failed(self):
        """Тест обработки когда все провайдеры failed"""
        manager = TextProcessingFallbackManager()
        
        provider1 = TestProvider("gemini_live", 1, {}, should_fail=True)
        provider2 = TestProvider("langchain", 2, {}, should_fail=True)
        manager.register_providers([provider1, provider2])
        
        results = []
        async for result in manager.process_text("Hello world"):
            results.append(result)
        
        assert len(results) == 1
        assert "All text_processing services are currently unavailable" in results[0]
    
    @pytest.mark.asyncio
    async def test_process_text_exception_handling(self):
        """Тест обработки исключений"""
        manager = TextProcessingFallbackManager()
        
        # Мокаем fallback_manager чтобы он выбросил исключение
        manager.fallback_manager.process_with_fallback = AsyncMock(
            side_effect=Exception("Test error")
        )
        
        results = []
        async for result in manager.process_text("Hello world"):
            results.append(result)
        
        assert len(results) == 1
        assert "Text processing failed" in results[0]
        assert "Test error" in results[0]
    
    def test_get_status(self):
        """Тест получения статуса менеджера"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        status = manager.get_status()
        
        assert status["module_name"] == "text_processing"
        assert "providers" in status
        assert "gemini_live" in status["providers"]
    
    def test_get_metrics(self):
        """Тест получения метрик менеджера"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        metrics = manager.get_metrics()
        
        assert metrics["module_name"] == "text_processing"
        assert "total_requests" in metrics
        assert "successful_requests" in metrics
        assert "failed_requests" in metrics
    
    def test_reset_metrics(self):
        """Тест сброса метрик менеджера"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        # Устанавливаем некоторые метрики
        provider.total_requests = 10
        provider.successful_requests = 8
        
        manager.reset_metrics()
        
        # Проверяем, что метрики сброшены
        assert provider.total_requests == 0
        assert provider.successful_requests == 0
    
    def test_get_healthy_providers(self):
        """Тест получения здоровых провайдеров"""
        manager = TextProcessingFallbackManager()
        
        provider1 = TestProvider("gemini_live", 1, {})
        provider2 = TestProvider("langchain", 2, {})
        manager.register_providers([provider1, provider2])
        
        healthy = manager.get_healthy_providers()
        assert len(healthy) == 2
        
        # Отключаем один провайдер
        manager.fallback_manager.circuit_breakers["gemini_live"] = True
        
        healthy = manager.get_healthy_providers()
        assert len(healthy) == 1
        assert healthy[0].name == "langchain"
    
    def test_get_failed_providers(self):
        """Тест получения failed провайдеров"""
        manager = TextProcessingFallbackManager()
        
        provider1 = TestProvider("gemini_live", 1, {})
        provider2 = TestProvider("langchain", 2, {})
        manager.register_providers([provider1, provider2])
        
        failed = manager.get_failed_providers()
        assert len(failed) == 0
        
        # Отключаем один провайдер
        manager.fallback_manager.circuit_breakers["gemini_live"] = True
        
        failed = manager.get_failed_providers()
        assert len(failed) == 1
        assert failed[0].name == "gemini_live"
    
    def test_get_provider_by_name(self):
        """Тест получения провайдера по имени"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        found_provider = manager.get_provider_by_name("gemini_live")
        assert found_provider is not None
        assert found_provider.name == "gemini_live"
        
        not_found = manager.get_provider_by_name("nonexistent")
        assert not_found is None
    
    def test_get_provider_status(self):
        """Тест получения статуса провайдера"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        status = manager.get_provider_status("gemini_live")
        assert status is not None
        assert status["name"] == "gemini_live"
        
        not_found_status = manager.get_provider_status("nonexistent")
        assert not_found_status is None
    
    def test_get_provider_metrics(self):
        """Тест получения метрик провайдера"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        metrics = manager.get_provider_metrics("gemini_live")
        assert metrics is not None
        assert metrics["name"] == "gemini_live"
        
        not_found_metrics = manager.get_provider_metrics("nonexistent")
        assert not_found_metrics is None
    
    def test_force_reset_provider(self):
        """Тест принудительного сброса провайдера"""
        manager = TextProcessingFallbackManager()
        
        provider = TestProvider("gemini_live", 1, {})
        manager.register_providers([provider])
        
        # Устанавливаем некоторые метрики и circuit breaker
        provider.error_count = 5
        manager.fallback_manager.circuit_breakers["gemini_live"] = True
        
        result = manager.force_reset_provider("gemini_live")
        
        assert result is True
        assert provider.error_count == 0
        assert manager.fallback_manager.circuit_breakers["gemini_live"] is False
        
        # Тест с несуществующим провайдером
        result = manager.force_reset_provider("nonexistent")
        assert result is False
    
    def test_get_summary(self):
        """Тест получения сводки по провайдерам"""
        manager = TextProcessingFallbackManager()
        
        provider1 = TestProvider("gemini_live", 1, {})
        provider2 = TestProvider("langchain", 2, {})
        manager.register_providers([provider1, provider2])
        
        # Устанавливаем некоторые метрики
        provider1.total_requests = 10
        provider1.successful_requests = 8
        
        summary = manager.get_summary()
        
        assert summary["total_providers"] == 2
        assert summary["healthy_providers"] == 2
        assert summary["failed_providers"] == 0
        assert len(summary["providers"]) == 2
        
        # Проверяем информацию о провайдерах
        gemini_info = next(p for p in summary["providers"] if p["name"] == "gemini_live")
        assert gemini_info["priority"] == 1
        assert gemini_info["total_requests"] == 10
        assert gemini_info["success_rate"] == 0.8
    
    def test_str_representation(self):
        """Тест строкового представления менеджера"""
        manager = TextProcessingFallbackManager()
        
        str_repr = str(manager)
        
        assert "TextProcessingFallbackManager" in str_repr
        assert "providers=0" in str_repr
    
    def test_repr_representation(self):
        """Тест представления менеджера для отладки"""
        manager = TextProcessingFallbackManager()
        
        repr_str = repr(manager)
        
        assert "TextProcessingFallbackManager" in repr_str
        assert "providers=0" in repr_str
        assert "healthy=0" in repr_str
        assert "failed=0" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
