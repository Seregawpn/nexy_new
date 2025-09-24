"""
Тесты для основного TextProcessor
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.text_processing.core.text_processor import TextProcessor
from modules.text_processing.config import TextProcessingConfig

class TestTextProcessor:
    """Тесты для основного процессора текста"""
    
    def test_text_processor_initialization(self):
        """Тест инициализации процессора"""
        config = {
            'gemini_temperature': 0.8,
            'gemini_max_tokens': 1024,
            'fallback_timeout': 30
        }
        
        processor = TextProcessor(config)
        
        assert processor.config is not None
        assert processor.fallback_manager is not None
        assert processor.is_initialized is False
        assert len(processor.providers) == 0
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'gemini_api_key': 'test-key',
            'gemini_temperature': 0.8
        }
        
        processor = TextProcessor(config)
        
        # Мокаем провайдеры
        with patch('modules.text_processing.core.text_processor.GeminiLiveProvider') as mock_gemini_class:
            with patch('modules.text_processing.core.text_processor.LangChainProvider') as mock_langchain_class:
                # Мокаем экземпляры провайдеров
                mock_gemini = AsyncMock()
                mock_gemini.initialize = AsyncMock(return_value=True)
                mock_gemini.name = "gemini_live"
                mock_gemini_class.return_value = mock_gemini
                
                mock_langchain = AsyncMock()
                mock_langchain.initialize = AsyncMock(return_value=True)
                mock_langchain.name = "langchain"
                mock_langchain_class.return_value = mock_langchain
                
                result = await processor.initialize()
                
                assert result is True
                assert processor.is_initialized is True
                assert len(processor.providers) == 2
                assert processor.providers[0].name == "gemini_live"
                assert processor.providers[1].name == "langchain"
    
    @pytest.mark.asyncio
    async def test_initialize_config_validation_failure(self):
        """Тест неудачной инициализации - невалидная конфигурация"""
        config = {
            # Нет API ключа
            'gemini_temperature': 0.8
        }
        
        processor = TextProcessor(config)
        
        result = await processor.initialize()
        
        assert result is False
        assert processor.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_no_providers_initialized(self):
        """Тест неудачной инициализации - ни один провайдер не инициализировался"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем провайдеры, которые не могут инициализироваться
        with patch('modules.text_processing.core.text_processor.GeminiLiveProvider') as mock_gemini_class:
            with patch('modules.text_processing.core.text_processor.LangChainProvider') as mock_langchain_class:
                mock_gemini = AsyncMock()
                mock_gemini.initialize = AsyncMock(return_value=False)
                mock_gemini_class.return_value = mock_gemini
                
                mock_langchain = AsyncMock()
                mock_langchain.initialize = AsyncMock(return_value=False)
                mock_langchain_class.return_value = mock_langchain
                
                result = await processor.initialize()
                
                assert result is False
                assert processor.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_process_text_success(self):
        """Тест успешной обработки текста"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем провайдеры
        with patch('modules.text_processing.core.text_processor.GeminiLiveProvider') as mock_gemini_class:
            with patch('modules.text_processing.core.text_processor.LangChainProvider') as mock_langchain_class:
                mock_gemini = AsyncMock()
                mock_gemini.initialize = AsyncMock(return_value=True)
                mock_gemini_class.return_value = mock_gemini
                
                mock_langchain = AsyncMock()
                mock_langchain.initialize = AsyncMock(return_value=True)
                mock_langchain_class.return_value = mock_langchain
                
                # Инициализируем процессор
                await processor.initialize()
                
                # Мокаем fallback_manager
                processor.fallback_manager.process_text = AsyncMock(
                    return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter(["Hello world"])))
                )
                
                # Обрабатываем текст
                results = []
                async for result in processor.process_text("Hello"):
                    results.append(result)
                
                assert len(results) == 1
                assert results[0] == "Hello world"
    
    @pytest.mark.asyncio
    async def test_process_text_not_initialized(self):
        """Тест обработки текста без инициализации"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Не инициализируем процессор
        
        results = []
        async for result in processor.process_text("Hello"):
            results.append(result)
        
        assert len(results) == 1
        assert "not initialized" in results[0]
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем провайдеры
        with patch('modules.text_processing.core.text_processor.GeminiLiveProvider') as mock_gemini_class:
            with patch('modules.text_processing.core.text_processor.LangChainProvider') as mock_langchain_class:
                mock_gemini = AsyncMock()
                mock_gemini.initialize = AsyncMock(return_value=True)
                mock_gemini.cleanup = AsyncMock(return_value=True)
                mock_gemini_class.return_value = mock_gemini
                
                mock_langchain = AsyncMock()
                mock_langchain.initialize = AsyncMock(return_value=True)
                mock_langchain.cleanup = AsyncMock(return_value=True)
                mock_langchain_class.return_value = mock_langchain
                
                # Инициализируем процессор
                await processor.initialize()
                
                # Очищаем ресурсы
                result = await processor.cleanup()
                
                assert result is True
                assert processor.is_initialized is False
    
    def test_get_status(self):
        """Тест получения статуса процессора"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        status = processor.get_status()
        
        assert "is_initialized" in status
        assert "config_status" in status
        assert "fallback_manager" in status
        assert "providers" in status
        assert isinstance(status["providers"], list)
    
    def test_get_metrics(self):
        """Тест получения метрик процессора"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        metrics = processor.get_metrics()
        
        assert "is_initialized" in metrics
        assert "fallback_manager" in metrics
        assert "providers" in metrics
        assert isinstance(metrics["providers"], list)
    
    def test_get_healthy_providers(self):
        """Тест получения здоровых провайдеров"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем fallback_manager
        processor.fallback_manager.get_healthy_providers = MagicMock(return_value=["provider1"])
        
        healthy = processor.get_healthy_providers()
        
        assert healthy == ["provider1"]
    
    def test_get_failed_providers(self):
        """Тест получения failed провайдеров"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем fallback_manager
        processor.fallback_manager.get_failed_providers = MagicMock(return_value=["provider2"])
        
        failed = processor.get_failed_providers()
        
        assert failed == ["provider2"]
    
    def test_reset_metrics(self):
        """Тест сброса метрик процессора"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем fallback_manager
        processor.fallback_manager.reset_metrics = MagicMock()
        
        processor.reset_metrics()
        
        processor.fallback_manager.reset_metrics.assert_called_once()
    
    def test_get_summary(self):
        """Тест получения сводки по процессору"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        # Мокаем fallback_manager
        processor.fallback_manager.get_summary = MagicMock(return_value={"test": "summary"})
        
        summary = processor.get_summary()
        
        assert "is_initialized" in summary
        assert "total_providers" in summary
        assert "healthy_providers" in summary
        assert "failed_providers" in summary
        assert "config_valid" in summary
        assert "fallback_summary" in summary
        assert summary["fallback_summary"] == {"test": "summary"}
    
    def test_str_representation(self):
        """Тест строкового представления процессора"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        str_repr = str(processor)
        
        assert "TextProcessor" in str_repr
        assert "initialized=False" in str_repr
        assert "providers=0" in str_repr
    
    def test_repr_representation(self):
        """Тест представления процессора для отладки"""
        config = {
            'gemini_api_key': 'test-key'
        }
        
        processor = TextProcessor(config)
        
        repr_str = repr(processor)
        
        assert "TextProcessor(" in repr_str
        assert "initialized=False" in repr_str
        assert "providers=0" in repr_str
        assert "healthy=0" in repr_str
        assert "failed=0" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
