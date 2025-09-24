"""
Тесты для Gemini Live Provider
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.text_processing.providers.gemini_live_provider import GeminiLiveProvider

class TestGeminiLiveProvider:
    """Тесты для Gemini Live провайдера"""
    
    def test_provider_initialization(self):
        """Тест инициализации провайдера"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'temperature': 0.8,
            'max_tokens': 1024,
            'api_key': 'test-key',
            'timeout': 30
        }
        
        provider = GeminiLiveProvider(config)
        
        assert provider.name == "gemini_live"
        assert provider.priority == 1
        assert provider.model_name == 'gemini-2.0-flash-exp'
        assert provider.temperature == 0.8
        assert provider.max_tokens == 1024
        assert provider.api_key == 'test-key'
        assert provider.timeout == 30
        assert provider.is_available is not None  # Зависит от доступности Gemini Live
        assert "Nexy" in provider.system_prompt
        assert "Google Search" in provider.system_prompt
    
    def test_provider_initialization_without_api_key(self):
        """Тест инициализации без API ключа"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'temperature': 0.8
            # Нет api_key
        }
        
        provider = GeminiLiveProvider(config)
        
        assert provider.name == "gemini_live"
        assert provider.priority == 1
        assert provider.api_key == ''
        assert provider.is_available is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Мокаем Gemini Live компоненты
        with patch('modules.text_processing.providers.gemini_live_provider.GEMINI_LIVE_AVAILABLE', True):
            with patch('modules.text_processing.providers.gemini_live_provider.genai') as mock_genai:
                # Мокаем конфигурацию
                mock_genai.configure = MagicMock()
                
                # Мокаем модель
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=MagicMock(text="Test response"))
                mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
                
                result = await provider.initialize()
                
                assert result is True
                assert provider.is_initialized is True
                assert provider.model is not None
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_gemini(self):
        """Тест неудачной инициализации - Gemini Live недоступен"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Мокаем отсутствие Gemini Live
        with patch('modules.text_processing.providers.gemini_live_provider.GEMINI_LIVE_AVAILABLE', False):
            result = await provider.initialize()
            
            assert result is False
            assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_api_key(self):
        """Тест неудачной инициализации - нет API ключа"""
        config = {
            'model': 'gemini-2.0-flash-exp'
            # Нет api_key
        }
        
        provider = GeminiLiveProvider(config)
        
        result = await provider.initialize()
        
        assert result is False
        assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_process_success(self):
        """Тест успешной обработки текста"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Мокаем Gemini Live
        with patch('modules.text_processing.providers.gemini_live_provider.GEMINI_LIVE_AVAILABLE', True):
            with patch('modules.text_processing.providers.gemini_live_provider.genai') as mock_genai:
                # Мокаем конфигурацию
                mock_genai.configure = MagicMock()
                
                # Мокаем модель и чат
                mock_chat = MagicMock()
                mock_response = MagicMock(text="Hello. How are you? I'm fine.")
                mock_chat.send_message = MagicMock(return_value=mock_response)
                
                mock_model = MagicMock()
                mock_model.start_chat = MagicMock(return_value=mock_chat)
                mock_model.generate_content = MagicMock(return_value=mock_response)
                mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
                
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
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
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
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Мокаем Gemini Live с пустым ответом
        with patch('modules.text_processing.providers.gemini_live_provider.GEMINI_LIVE_AVAILABLE', True):
            with patch('modules.text_processing.providers.gemini_live_provider.genai') as mock_genai:
                mock_genai.configure = MagicMock()
                
                # Мокаем пустой ответ
                mock_response = MagicMock(text="")
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_response)
                mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
                
                await provider.initialize()
                
                with pytest.raises(Exception) as exc_info:
                    results = []
                    async for result in provider.process("Hello"):
                        results.append(result)
                
                assert "No response" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Инициализируем провайдер
        provider.model = MagicMock()
        provider.is_initialized = True
        
        result = await provider.cleanup()
        
        assert result is True
        assert provider.model is None
        assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Тест проверки здоровья - здоровый провайдер"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Мокаем Gemini Live
        with patch('modules.text_processing.providers.gemini_live_provider.GEMINI_LIVE_AVAILABLE', True):
            with patch('modules.text_processing.providers.gemini_live_provider.genai') as mock_genai:
                mock_genai.configure = MagicMock()
                
                mock_response = MagicMock(text="Health check OK")
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_response)
                mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
                
                await provider.initialize()
                
                health = await provider.health_check()
                
                assert health is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Тест проверки здоровья - нездоровый провайдер"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        # Мокаем Gemini Live с ошибкой
        with patch('modules.text_processing.providers.gemini_live_provider.GEMINI_LIVE_AVAILABLE', True):
            with patch('modules.text_processing.providers.gemini_live_provider.genai') as mock_genai:
                mock_genai.configure = MagicMock()
                
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(side_effect=Exception("API Error"))
                mock_genai.GenerativeModel = MagicMock(return_value=mock_model)
                
                await provider.initialize()
                
                health = await provider.health_check()
                
                assert health is False
    
    def test_split_into_sentences(self):
        """Тест разбиения текста на предложения"""
        config = {'api_key': 'test-key'}
        provider = GeminiLiveProvider(config)
        
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
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        status = provider.get_status()
        
        assert status["provider_type"] == "gemini_live"
        assert status["model_name"] == "gemini-2.0-flash-exp"
        assert status["temperature"] == 0.7
        assert status["max_tokens"] == 2048
        assert status["api_key_set"] is True
        assert "gemini_live_available" in status
    
    def test_get_metrics(self):
        """Тест получения метрик провайдера"""
        config = {
            'model': 'gemini-2.0-flash-exp',
            'api_key': 'test-key'
        }
        
        provider = GeminiLiveProvider(config)
        
        metrics = provider.get_metrics()
        
        assert metrics["provider_type"] == "gemini_live"
        assert metrics["model_name"] == "gemini-2.0-flash-exp"
        assert metrics["is_available"] is not None
        assert metrics["api_key_set"] is True

if __name__ == "__main__":
    pytest.main([__file__])
