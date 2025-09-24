"""
Тесты для LangChain Provider
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.text_processing.providers.langchain_provider import LangChainProvider

class TestLangChainProvider:
    """Тесты для LangChain провайдера"""
    
    def test_provider_initialization(self):
        """Тест инициализации провайдера"""
        config = {
            'model': 'gemini-pro',
            'temperature': 0.8,
            'api_key': 'test-key',
            'timeout': 30
        }
        
        provider = LangChainProvider(config)
        
        assert provider.name == "langchain"
        assert provider.priority == 2
        assert provider.model_name == 'gemini-pro'
        assert provider.temperature == 0.8
        assert provider.api_key == 'test-key'
        assert provider.timeout == 30
        assert provider.is_available is not None  # Зависит от доступности LangChain
        assert "Nexy" in provider.system_prompt
    
    def test_provider_initialization_without_api_key(self):
        """Тест инициализации без API ключа"""
        config = {
            'model': 'gemini-pro',
            'temperature': 0.8
            # Нет api_key
        }
        
        provider = LangChainProvider(config)
        
        assert provider.name == "langchain"
        assert provider.priority == 2
        assert provider.api_key == ''
        assert provider.is_available is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Мокаем LangChain компоненты
        with patch('modules.text_processing.providers.langchain_provider.LANGCHAIN_AVAILABLE', True):
            with patch('modules.text_processing.providers.langchain_provider.ChatGoogleGenerativeAI') as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.agenerate = AsyncMock(return_value=MagicMock(
                    generations=[[MagicMock(text="Test response")]]
                ))
                mock_llm_class.return_value = mock_llm
                
                result = await provider.initialize()
                
                assert result is True
                assert provider.is_initialized is True
                assert provider.llm is not None
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_langchain(self):
        """Тест неудачной инициализации - LangChain недоступен"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Мокаем отсутствие LangChain
        with patch('modules.text_processing.providers.langchain_provider.LANGCHAIN_AVAILABLE', False):
            result = await provider.initialize()
            
            assert result is False
            assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_api_key(self):
        """Тест неудачной инициализации - нет API ключа"""
        config = {
            'model': 'gemini-pro'
            # Нет api_key
        }
        
        provider = LangChainProvider(config)
        
        result = await provider.initialize()
        
        assert result is False
        assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_process_success(self):
        """Тест успешной обработки текста"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Мокаем LangChain
        with patch('modules.text_processing.providers.langchain_provider.LANGCHAIN_AVAILABLE', True):
            with patch('modules.text_processing.providers.langchain_provider.ChatGoogleGenerativeAI') as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.agenerate = AsyncMock(return_value=MagicMock(
                    generations=[[MagicMock(text="Hello. How are you? I'm fine.")]]
                ))
                mock_llm_class.return_value = mock_llm
                
                # Инициализируем провайдер
                await provider.initialize()
                
                # Обрабатываем текст
                results = []
                async for result in provider.process("Hello"):
                    results.append(result)
                
                assert len(results) > 0
                assert any("Hello" in result for result in results)
                assert provider.total_requests == 1
                assert provider.successful_requests == 1
    
    @pytest.mark.asyncio
    async def test_process_not_initialized(self):
        """Тест обработки без инициализации"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Не инициализируем провайдер
        
        with pytest.raises(Exception) as exc_info:
            results = []
            async for result in provider.process("Hello"):
                results.append(result)
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_empty_response(self):
        """Тест обработки с пустым ответом"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Мокаем LangChain с пустым ответом
        with patch('modules.text_processing.providers.langchain_provider.LANGCHAIN_AVAILABLE', True):
            with patch('modules.text_processing.providers.langchain_provider.ChatGoogleGenerativeAI') as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.agenerate = AsyncMock(return_value=MagicMock(
                    generations=[[MagicMock(text="")]]  # Пустой ответ
                ))
                mock_llm_class.return_value = mock_llm
                
                await provider.initialize()
                
                with pytest.raises(Exception) as exc_info:
                    results = []
                    async for result in provider.process("Hello"):
                        results.append(result)
                
                assert "Empty response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Инициализируем провайдер
        provider.llm = MagicMock()
        provider.is_initialized = True
        
        result = await provider.cleanup()
        
        assert result is True
        assert provider.llm is None
        assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Тест проверки здоровья - здоровый провайдер"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Мокаем LangChain
        with patch('modules.text_processing.providers.langchain_provider.LANGCHAIN_AVAILABLE', True):
            with patch('modules.text_processing.providers.langchain_provider.ChatGoogleGenerativeAI') as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.agenerate = AsyncMock(return_value=MagicMock(
                    generations=[[MagicMock(text="Health check OK")]]
                ))
                mock_llm_class.return_value = mock_llm
                
                await provider.initialize()
                
                health = await provider.health_check()
                
                assert health is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Тест проверки здоровья - нездоровый провайдер"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        # Мокаем LangChain с ошибкой
        with patch('modules.text_processing.providers.langchain_provider.LANGCHAIN_AVAILABLE', True):
            with patch('modules.text_processing.providers.langchain_provider.ChatGoogleGenerativeAI') as mock_llm_class:
                mock_llm = AsyncMock()
                mock_llm.agenerate = AsyncMock(side_effect=Exception("API Error"))
                mock_llm_class.return_value = mock_llm
                
                await provider.initialize()
                
                health = await provider.health_check()
                
                assert health is False
    
    def test_split_into_sentences(self):
        """Тест разбиения текста на предложения"""
        config = {'api_key': 'test-key'}
        provider = LangChainProvider(config)
        
        # Тест с обычным текстом
        text = "Hello world. How are you? I'm fine!"
        sentences = provider._split_into_sentences(text)
        
        assert len(sentences) == 3
        assert "Hello world." in sentences
        assert "How are you?" in sentences
        assert "I'm fine!" in sentences
        
        # Тест с пустым текстом
        empty_sentences = provider._split_into_sentences("")
        assert len(empty_sentences) == 0
        
        # Тест с текстом без знаков препинания
        no_punctuation = provider._split_into_sentences("Hello world")
        assert len(no_punctuation) == 1
        assert "Hello world." in no_punctuation
    
    def test_get_status(self):
        """Тест получения статуса провайдера"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        status = provider.get_status()
        
        assert status["provider_type"] == "langchain"
        assert status["model_name"] == "gemini-pro"
        assert status["temperature"] == 0.7
        assert status["api_key_set"] is True
        assert "langchain_available" in status
    
    def test_get_metrics(self):
        """Тест получения метрик провайдера"""
        config = {
            'model': 'gemini-pro',
            'api_key': 'test-key'
        }
        
        provider = LangChainProvider(config)
        
        metrics = provider.get_metrics()
        
        assert metrics["provider_type"] == "langchain"
        assert metrics["model_name"] == "gemini-pro"
        assert metrics["is_available"] is not None
        assert metrics["api_key_set"] is True

if __name__ == "__main__":
    pytest.main([__file__])
