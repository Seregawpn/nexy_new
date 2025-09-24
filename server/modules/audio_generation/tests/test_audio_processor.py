"""
Тесты для основного AudioProcessor
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.audio_generation.core.audio_processor import AudioProcessor
from modules.audio_generation.config import AudioGenerationConfig

class TestAudioProcessor:
    """Тесты для основного процессора аудио"""
    
    def test_audio_processor_initialization(self):
        """Тест инициализации процессора"""
        config = {
            'azure_voice_name': 'en-US-JennyNeural',
            'azure_speech_rate': 1.2,
            'sample_rate': 24000,
            'streaming_enabled': True
        }
        
        processor = AudioProcessor(config)
        
        assert processor.config is not None
        assert processor.provider is None
        assert processor.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus',
            'azure_voice_name': 'en-US-JennyNeural'
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            # Мокаем экземпляр провайдера
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.name = "azure_tts"
            mock_provider.is_available = True
            mock_provider_class.return_value = mock_provider
            
            result = await processor.initialize()
            
            assert result is True
            assert processor.is_initialized is True
            assert processor.provider is not None
            assert processor.provider.name == "azure_tts"
    
    @pytest.mark.asyncio
    async def test_initialize_config_validation_failure(self):
        """Тест неудачной инициализации - невалидная конфигурация"""
        config = {
            'azure_voice_name': 'en-US-JennyNeural'
            # Нет API ключей
        }
        
        processor = AudioProcessor(config)
        
        result = await processor.initialize()
        
        assert result is False
        assert processor.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_provider_failure(self):
        """Тест неудачной инициализации - провайдер не инициализировался"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер, который не может инициализироваться
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=False)
            mock_provider_class.return_value = mock_provider
            
            result = await processor.initialize()
            
            assert result is False
            assert processor.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_generate_speech_success(self):
        """Тест успешной генерации речи"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter([b'audio chunk 1', b'audio chunk 2']))))
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем процессор
            await processor.initialize()
            
            # Генерируем речь
            results = []
            async for result in processor.generate_speech("Hello world"):
                results.append(result)
            
            assert len(results) == 2
            assert results[0] == b'audio chunk 1'
            assert results[1] == b'audio chunk 2'
    
    @pytest.mark.asyncio
    async def test_generate_speech_not_initialized(self):
        """Тест генерации речи без инициализации"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Не инициализируем процессор
        
        with pytest.raises(Exception) as exc_info:
            results = []
            async for result in processor.generate_speech("Hello world"):
                results.append(result)
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_generate_speech_streaming_success(self):
        """Тест успешной потоковой генерации речи"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus',
            'streaming_enabled': True,
            'streaming_chunk_size': 1024
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            # Мокаем большой chunk, который будет разбит на меньшие
            large_chunk = b'x' * 2048  # 2KB chunk
            mock_provider.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter([large_chunk]))))
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем процессор
            await processor.initialize()
            
            # Генерируем речь с streaming
            results = []
            async for result in processor.generate_speech_streaming("Hello world"):
                results.append(result)
            
            assert len(results) == 2  # 2KB chunk разбит на 2 части по 1KB
            assert len(results[0]) == 1024
            assert len(results[1]) == 1024
    
    @pytest.mark.asyncio
    async def test_generate_speech_streaming_disabled(self):
        """Тест потоковой генерации речи с отключенным streaming"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus',
            'streaming_enabled': False
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.process = AsyncMock(return_value=AsyncMock(__aiter__=AsyncMock(return_value=iter([b'audio chunk']))))
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем процессор
            await processor.initialize()
            
            # Генерируем речь с streaming (должен fallback на обычную генерацию)
            results = []
            async for result in processor.generate_speech_streaming("Hello world"):
                results.append(result)
            
            assert len(results) == 1
            assert results[0] == b'audio chunk'
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.cleanup = AsyncMock(return_value=True)
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем процессор
            await processor.initialize()
            
            # Очищаем ресурсы
            result = await processor.cleanup()
            
            assert result is True
            assert processor.is_initialized is False
    
    def test_get_status(self):
        """Тест получения статуса процессора"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        status = processor.get_status()
        
        assert "is_initialized" in status
        assert "config_status" in status
        assert "provider" in status
        assert status["provider"] is None  # Провайдер еще не создан
    
    def test_get_metrics(self):
        """Тест получения метрик процессора"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        metrics = processor.get_metrics()
        
        assert "is_initialized" in metrics
        assert "provider" in metrics
        assert metrics["provider"] is None  # Провайдер еще не создан
    
    def test_get_audio_info(self):
        """Тест получения информации об аудио"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus',
            'azure_voice_name': 'en-US-JennyNeural',
            'sample_rate': 24000
        }
        
        processor = AudioProcessor(config)
        
        audio_info = processor.get_audio_info()
        
        assert audio_info["voice_name"] == "en-US-JennyNeural"
        assert audio_info["sample_rate"] == 24000
        assert audio_info["format"] == "riff-16khz-16bit-mono-pcm"
    
    def test_get_voice_options(self):
        """Тест получения доступных опций голоса"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        voice_options = processor.get_voice_options()
        
        assert 'voice_names' in voice_options
        assert 'voice_styles' in voice_options
        assert 'audio_formats' in voice_options
        assert len(voice_options['voice_names']) > 0
    
    def test_update_voice_settings(self):
        """Тест обновления настроек голоса"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.voice_name = 'en-US-AriaNeural'
            mock_provider.voice_style = 'friendly'
            mock_provider.speech_rate = 1.0
            mock_provider.speech_pitch = 1.0
            mock_provider.speech_volume = 1.0
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем процессор
            await processor.initialize()
            
            # Обновляем настройки голоса
            new_settings = {
                'voice_name': 'en-US-JennyNeural',
                'voice_style': 'cheerful',
                'speech_rate': 1.2
            }
            
            result = processor.update_voice_settings(new_settings)
            
            assert result is True
            assert processor.config.azure_voice_name == 'en-US-JennyNeural'
            assert processor.config.azure_voice_style == 'cheerful'
            assert processor.config.azure_speech_rate == 1.2
    
    def test_update_voice_settings_not_initialized(self):
        """Тест обновления настроек голоса без инициализации"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Не инициализируем процессор
        
        new_settings = {
            'voice_name': 'en-US-JennyNeural'
        }
        
        result = processor.update_voice_settings(new_settings)
        
        assert result is False
    
    def test_reset_metrics(self):
        """Тест сброса метрик процессора"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        # Мокаем провайдер
        with patch('modules.audio_generation.core.audio_processor.AzureTTSProvider') as mock_provider_class:
            mock_provider = AsyncMock()
            mock_provider.initialize = AsyncMock(return_value=True)
            mock_provider.reset_metrics = MagicMock()
            mock_provider_class.return_value = mock_provider
            
            # Инициализируем процессор
            await processor.initialize()
            
            # Сбрасываем метрики
            processor.reset_metrics()
            
            mock_provider.reset_metrics.assert_called_once()
    
    def test_get_summary(self):
        """Тест получения сводки по процессору"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        summary = processor.get_summary()
        
        assert "is_initialized" in summary
        assert "provider_name" in summary
        assert "provider_available" in summary
        assert "config_valid" in summary
        assert "audio_info" in summary
        assert summary["provider_name"] == "azure_tts"
    
    def test_str_representation(self):
        """Тест строкового представления процессора"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        str_repr = str(processor)
        
        assert "AudioProcessor" in str_repr
        assert "initialized=False" in str_repr
        assert "provider=none" in str_repr
    
    def test_repr_representation(self):
        """Тест представления процессора для отладки"""
        config = {
            'azure_speech_key': 'test-key',
            'azure_speech_region': 'eastus'
        }
        
        processor = AudioProcessor(config)
        
        repr_str = repr(processor)
        
        assert "AudioProcessor(" in repr_str
        assert "initialized=False" in repr_str
        assert "provider=none" in repr_str
        assert "available=False" in repr_str

if __name__ == "__main__":
    pytest.main([__file__])
