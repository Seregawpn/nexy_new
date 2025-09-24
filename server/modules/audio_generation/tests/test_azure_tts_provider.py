"""
Тесты для Azure TTS Provider
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from modules.audio_generation.providers.azure_tts_provider import AzureTTSProvider

class TestAzureTTSProvider:
    """Тесты для Azure TTS провайдера"""
    
    def test_provider_initialization(self):
        """Тест инициализации провайдера"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus',
            'voice_name': 'en-US-JennyNeural',
            'voice_style': 'cheerful',
            'speech_rate': 1.2,
            'speech_pitch': 0.8,
            'speech_volume': 0.9,
            'audio_format': 'riff-24khz-16bit-mono-pcm',
            'sample_rate': 24000,
            'channels': 1,
            'bits_per_sample': 16,
            'timeout': 30
        }
        
        provider = AzureTTSProvider(config)
        
        assert provider.name == "azure_tts"
        assert provider.priority == 1
        assert provider.speech_key == 'test-key'
        assert provider.speech_region == 'eastus'
        assert provider.voice_name == 'en-US-JennyNeural'
        assert provider.voice_style == 'cheerful'
        assert provider.speech_rate == 1.2
        assert provider.speech_pitch == 0.8
        assert provider.speech_volume == 0.9
        assert provider.audio_format == 'riff-24khz-16bit-mono-pcm'
        assert provider.sample_rate == 24000
        assert provider.channels == 1
        assert provider.bits_per_sample == 16
        assert provider.timeout == 30
        assert provider.is_available is not None  # Зависит от доступности Azure Speech SDK
    
    def test_provider_initialization_without_credentials(self):
        """Тест инициализации без учетных данных"""
        config = {
            'voice_name': 'en-US-JennyNeural'
            # Нет speech_key и speech_region
        }
        
        provider = AzureTTSProvider(config)
        
        assert provider.name == "azure_tts"
        assert provider.priority == 1
        assert provider.speech_key == ''
        assert provider.speech_region == ''
        assert provider.is_available is False
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Тест успешной инициализации"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Мокаем Azure Speech SDK компоненты
        with patch('modules.audio_generation.providers.azure_tts_provider.AZURE_SPEECH_AVAILABLE', True):
            with patch('modules.audio_generation.providers.azure_tts_provider.speechsdk') as mock_speechsdk:
                # Мокаем SpeechConfig
                mock_speech_config = MagicMock()
                mock_speechsdk.SpeechConfig.return_value = mock_speech_config
                
                # Мокаем SpeechSynthesizer
                mock_synthesizer = MagicMock()
                mock_synthesizer.speak_text_async.return_value.get.return_value = MagicMock(
                    reason=mock_speechsdk.ResultReason.SynthesizingAudioCompleted
                )
                mock_speechsdk.SpeechSynthesizer.return_value = mock_synthesizer
                
                # Мокаем ResultReason
                mock_speechsdk.ResultReason.SynthesizingAudioCompleted = "SynthesizingAudioCompleted"
                
                result = await provider.initialize()
                
                assert result is True
                assert provider.is_initialized is True
                assert provider.speech_config is not None
                assert provider.synthesizer is not None
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_azure_sdk(self):
        """Тест неудачной инициализации - Azure Speech SDK недоступен"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Мокаем отсутствие Azure Speech SDK
        with patch('modules.audio_generation.providers.azure_tts_provider.AZURE_SPEECH_AVAILABLE', False):
            result = await provider.initialize()
            
            assert result is False
            assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_credentials(self):
        """Тест неудачной инициализации - нет учетных данных"""
        config = {
            'voice_name': 'en-US-JennyNeural'
            # Нет speech_key и speech_region
        }
        
        provider = AzureTTSProvider(config)
        
        result = await provider.initialize()
        
        assert result is False
        assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_process_success(self):
        """Тест успешной генерации речи"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Мокаем Azure Speech SDK
        with patch('modules.audio_generation.providers.azure_tts_provider.AZURE_SPEECH_AVAILABLE', True):
            with patch('modules.audio_generation.providers.azure_tts_provider.speechsdk') as mock_speechsdk:
                mock_speech_config = MagicMock()
                mock_speechsdk.SpeechConfig.return_value = mock_speech_config
                
                # Мокаем успешный синтез
                mock_result = MagicMock()
                mock_result.reason = mock_speechsdk.ResultReason.SynthesizingAudioCompleted
                mock_result.audio_data = b'test audio data'
                
                mock_synthesizer = MagicMock()
                mock_synthesizer.speak_ssml_async.return_value.get.return_value = mock_result
                mock_synthesizer.speak_text_async.return_value.get.return_value = MagicMock(
                    reason=mock_speechsdk.ResultReason.SynthesizingAudioCompleted
                )
                mock_speechsdk.SpeechSynthesizer.return_value = mock_synthesizer
                mock_speechsdk.ResultReason.SynthesizingAudioCompleted = "SynthesizingAudioCompleted"
                
                # Инициализируем провайдер
                await provider.initialize()
                
                # Генерируем речь
                results = []
                async for result in provider.process("Hello world"):
                    results.append(result)
                
                assert len(results) > 0
                assert b'test audio data' in results[0]
                assert provider.total_requests == 1
                assert provider.successful_requests == 1
    
    @pytest.mark.asyncio
    async def test_process_not_initialized(self):
        """Тест генерации речи без инициализации"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Не инициализируем провайдер
        
        with pytest.raises(Exception) as exc_info:
            results = []
            async for result in provider.process("Hello world"):
                results.append(result)
        
        assert "not initialized" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_process_empty_response(self):
        """Тест генерации речи с пустым ответом"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Мокаем Azure Speech SDK с пустым ответом
        with patch('modules.audio_generation.providers.azure_tts_provider.AZURE_SPEECH_AVAILABLE', True):
            with patch('modules.audio_generation.providers.azure_tts_provider.speechsdk') as mock_speechsdk:
                mock_speech_config = MagicMock()
                mock_speechsdk.SpeechConfig.return_value = mock_speech_config
                
                # Мокаем пустой ответ
                mock_result = MagicMock()
                mock_result.reason = mock_speechsdk.ResultReason.SynthesizingAudioCompleted
                mock_result.audio_data = b''  # Пустые аудио данные
                
                mock_synthesizer = MagicMock()
                mock_synthesizer.speak_ssml_async.return_value.get.return_value = mock_result
                mock_synthesizer.speak_text_async.return_value.get.return_value = MagicMock(
                    reason=mock_speechsdk.ResultReason.SynthesizingAudioCompleted
                )
                mock_speechsdk.SpeechSynthesizer.return_value = mock_synthesizer
                mock_speechsdk.ResultReason.SynthesizingAudioCompleted = "SynthesizingAudioCompleted"
                
                await provider.initialize()
                
                with pytest.raises(Exception) as exc_info:
                    results = []
                    async for result in provider.process("Hello world"):
                        results.append(result)
                
                assert "No audio data" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Тест очистки ресурсов"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Инициализируем провайдер
        provider.speech_config = MagicMock()
        provider.synthesizer = MagicMock()
        provider.is_initialized = True
        
        result = await provider.cleanup()
        
        assert result is True
        assert provider.speech_config is None
        assert provider.synthesizer is None
        assert provider.is_initialized is False
    
    @pytest.mark.asyncio
    async def test_health_check_healthy(self):
        """Тест проверки здоровья - здоровый провайдер"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Мокаем Azure Speech SDK
        with patch('modules.audio_generation.providers.azure_tts_provider.AZURE_SPEECH_AVAILABLE', True):
            with patch('modules.audio_generation.providers.azure_tts_provider.speechsdk') as mock_speechsdk:
                mock_speech_config = MagicMock()
                mock_speechsdk.SpeechConfig.return_value = mock_speech_config
                
                mock_synthesizer = MagicMock()
                mock_synthesizer.speak_text_async.return_value.get.return_value = MagicMock(
                    reason=mock_speechsdk.ResultReason.SynthesizingAudioCompleted
                )
                mock_speechsdk.SpeechSynthesizer.return_value = mock_synthesizer
                mock_speechsdk.ResultReason.SynthesizingAudioCompleted = "SynthesizingAudioCompleted"
                
                await provider.initialize()
                
                health = await provider.health_check()
                
                assert health is True
    
    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self):
        """Тест проверки здоровья - нездоровый провайдер"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        # Мокаем Azure Speech SDK с ошибкой
        with patch('modules.audio_generation.providers.azure_tts_provider.AZURE_SPEECH_AVAILABLE', True):
            with patch('modules.audio_generation.providers.azure_tts_provider.speechsdk') as mock_speechsdk:
                mock_speech_config = MagicMock()
                mock_speechsdk.SpeechConfig.return_value = mock_speech_config
                
                mock_synthesizer = MagicMock()
                mock_synthesizer.speak_text_async.return_value.get.side_effect = Exception("API Error")
                mock_speechsdk.SpeechSynthesizer.return_value = mock_synthesizer
                
                await provider.initialize()
                
                health = await provider.health_check()
                
                assert health is False
    
    def test_create_ssml(self):
        """Тест создания SSML"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus',
            'voice_name': 'en-US-JennyNeural',
            'voice_style': 'cheerful',
            'speech_rate': 1.2,
            'speech_pitch': 0.8,
            'speech_volume': 0.9
        }
        
        provider = AzureTTSProvider(config)
        
        text = "Hello & welcome <everyone>!"
        ssml = provider._create_ssml(text)
        
        assert "en-US-JennyNeural" in ssml
        assert "cheerful" in ssml
        assert "1.2" in ssml
        assert "0.8" in ssml
        assert "0.9" in ssml
        assert "&amp;" in ssml  # Экранированный &
        assert "&lt;everyone&gt;" in ssml  # Экранированные <>
    
    def test_get_status(self):
        """Тест получения статуса провайдера"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        status = provider.get_status()
        
        assert status["provider_type"] == "azure_tts"
        assert status["voice_name"] == "en-US-AriaNeural"
        assert status["voice_style"] == "friendly"
        assert status["speech_rate"] == 1.0
        assert status["speech_pitch"] == 1.0
        assert status["speech_volume"] == 1.0
        assert status["audio_format"] == "riff-16khz-16bit-mono-pcm"
        assert status["sample_rate"] == 16000
        assert status["channels"] == 1
        assert status["bits_per_sample"] == 16
        assert status["speech_key_set"] is True
        assert status["speech_region_set"] is True
        assert "azure_speech_available" in status
    
    def test_get_metrics(self):
        """Тест получения метрик провайдера"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus'
        }
        
        provider = AzureTTSProvider(config)
        
        metrics = provider.get_metrics()
        
        assert metrics["provider_type"] == "azure_tts"
        assert metrics["voice_name"] == "en-US-AriaNeural"
        assert metrics["audio_format"] == "riff-16khz-16bit-mono-pcm"
        assert metrics["is_available"] is not None
        assert metrics["speech_key_set"] is True
        assert metrics["speech_region_set"] is True
    
    def test_get_audio_info(self):
        """Тест получения информации об аудио"""
        config = {
            'speech_key': 'test-key',
            'speech_region': 'eastus',
            'voice_name': 'en-US-JennyNeural',
            'voice_style': 'cheerful',
            'speech_rate': 1.2
        }
        
        provider = AzureTTSProvider(config)
        
        audio_info = provider.get_audio_info()
        
        assert audio_info["voice_name"] == "en-US-JennyNeural"
        assert audio_info["voice_style"] == "cheerful"
        assert audio_info["speech_rate"] == 1.2
        assert audio_info["format"] == "riff-16khz-16bit-mono-pcm"
        assert audio_info["sample_rate"] == 16000

if __name__ == "__main__":
    pytest.main([__file__])
