"""
Тесты для конфигурации Audio Generation модуля
"""

import pytest
import os
from unittest.mock import patch
from modules.audio_generation.config import AudioGenerationConfig

class TestAudioGenerationConfig:
    """Тесты для конфигурации модуля генерации аудио"""
    
    def test_config_initialization(self):
        """Тест инициализации конфигурации"""
        config = {
            'azure_voice_name': 'en-US-JennyNeural',
            'azure_voice_style': 'cheerful',
            'azure_speech_rate': 1.2,
            'azure_speech_pitch': 0.8,
            'azure_speech_volume': 0.9,
            'audio_format': 'riff-24khz-16bit-mono-pcm',
            'sample_rate': 24000,
            'channels': 1,
            'bits_per_sample': 16,
            'streaming_chunk_size': 8192,
            'streaming_enabled': True
        }
        
        audio_config = AudioGenerationConfig(config)
        
        assert audio_config.azure_voice_name == 'en-US-JennyNeural'
        assert audio_config.azure_voice_style == 'cheerful'
        assert audio_config.azure_speech_rate == 1.2
        assert audio_config.azure_speech_pitch == 0.8
        assert audio_config.azure_speech_volume == 0.9
        assert audio_config.audio_format == 'riff-24khz-16bit-mono-pcm'
        assert audio_config.sample_rate == 24000
        assert audio_config.channels == 1
        assert audio_config.bits_per_sample == 16
        assert audio_config.streaming_chunk_size == 8192
        assert audio_config.streaming_enabled is True
    
    def test_config_default_values(self):
        """Тест значений по умолчанию"""
        audio_config = AudioGenerationConfig()
        
        assert audio_config.azure_voice_name == 'en-US-AriaNeural'
        assert audio_config.azure_voice_style == 'friendly'
        assert audio_config.azure_speech_rate == 1.0
        assert audio_config.azure_speech_pitch == 1.0
        assert audio_config.azure_speech_volume == 1.0
        assert audio_config.audio_format == 'riff-16khz-16bit-mono-pcm'
        assert audio_config.sample_rate == 16000
        assert audio_config.channels == 1
        assert audio_config.bits_per_sample == 16
        assert audio_config.streaming_chunk_size == 4096
        assert audio_config.streaming_enabled is True
    
    def test_config_from_environment(self):
        """Тест загрузки конфигурации из переменных окружения"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            audio_config = AudioGenerationConfig()
            
            assert audio_config.azure_speech_key == 'test-key'
            assert audio_config.azure_speech_region == 'eastus'
    
    def test_get_azure_config(self):
        """Тест получения конфигурации Azure"""
        config = {
            'azure_voice_name': 'en-US-JennyNeural',
            'azure_speech_rate': 1.2
        }
        
        audio_config = AudioGenerationConfig(config)
        azure_config = audio_config.get_azure_config()
        
        assert azure_config['voice_name'] == 'en-US-JennyNeural'
        assert azure_config['speech_rate'] == 1.2
        assert azure_config['audio_format'] == 'riff-16khz-16bit-mono-pcm'
        assert azure_config['sample_rate'] == 16000
        assert azure_config['channels'] == 1
        assert azure_config['bits_per_sample'] == 16
    
    def test_get_streaming_config(self):
        """Тест получения конфигурации streaming"""
        config = {
            'streaming_chunk_size': 8192,
            'streaming_enabled': False,
            'sample_rate': 24000
        }
        
        audio_config = AudioGenerationConfig(config)
        streaming_config = audio_config.get_streaming_config()
        
        assert streaming_config['chunk_size'] == 8192
        assert streaming_config['enabled'] is False
        assert streaming_config['sample_rate'] == 24000
        assert streaming_config['channels'] == 1
        assert streaming_config['bits_per_sample'] == 16
    
    def test_validate_success(self):
        """Тест успешной валидации конфигурации"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'azure_speech_rate': 1.0,
                'azure_speech_pitch': 1.0,
                'azure_speech_volume': 0.8,
                'sample_rate': 16000,
                'channels': 1,
                'bits_per_sample': 16,
                'request_timeout': 60,
                'streaming_chunk_size': 4096
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is True
    
    def test_validate_missing_api_key(self):
        """Тест валидации без API ключа"""
        with patch.dict(os.environ, {}, clear=True):
            audio_config = AudioGenerationConfig()
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_missing_region(self):
        """Тест валидации без региона"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key'
            # Нет AZURE_SPEECH_REGION
        }):
            audio_config = AudioGenerationConfig()
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_invalid_speech_rate(self):
        """Тест валидации с некорректной скоростью речи"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'azure_speech_rate': 3.0  # Некорректное значение
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_invalid_speech_pitch(self):
        """Тест валидации с некорректной высотой тона"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'azure_speech_pitch': 3.0  # Некорректное значение
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_invalid_speech_volume(self):
        """Тест валидации с некорректной громкостью"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'azure_speech_volume': 2.0  # Некорректное значение
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_invalid_sample_rate(self):
        """Тест валидации с некорректной частотой дискретизации"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'sample_rate': 5000  # Некорректное значение
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_invalid_channels(self):
        """Тест валидации с некорректным количеством каналов"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'channels': 4  # Некорректное значение
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is False
    
    def test_validate_invalid_bits_per_sample(self):
        """Тест валидации с некорректным количеством бит на сэмпл"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            config = {
                'bits_per_sample': 12  # Некорректное значение
            }
            
            audio_config = AudioGenerationConfig(config)
            result = audio_config.validate()
            
            assert result is False
    
    def test_get_status(self):
        """Тест получения статуса конфигурации"""
        with patch.dict(os.environ, {
            'AZURE_SPEECH_KEY': 'test-key',
            'AZURE_SPEECH_REGION': 'eastus'
        }):
            audio_config = AudioGenerationConfig()
            status = audio_config.get_status()
            
            assert status['azure_speech_key_set'] is True
            assert status['azure_speech_region_set'] is True
            assert status['azure_voice_name'] == 'en-US-AriaNeural'
            assert status['azure_voice_style'] == 'friendly'
            assert status['audio_format'] == 'riff-16khz-16bit-mono-pcm'
            assert status['sample_rate'] == 16000
            assert status['channels'] == 1
            assert status['bits_per_sample'] == 16
            assert status['streaming_enabled'] is True
    
    def test_get_voice_options(self):
        """Тест получения доступных опций голоса"""
        audio_config = AudioGenerationConfig()
        voice_options = audio_config.get_voice_options()
        
        assert 'voice_names' in voice_options
        assert 'voice_styles' in voice_options
        assert 'audio_formats' in voice_options
        
        assert len(voice_options['voice_names']) > 0
        assert len(voice_options['voice_styles']) > 0
        assert len(voice_options['audio_formats']) > 0
        
        assert 'en-US-AriaNeural' in voice_options['voice_names']
        assert 'friendly' in voice_options['voice_styles']
        assert 'riff-16khz-16bit-mono-pcm' in voice_options['audio_formats']

if __name__ == "__main__":
    pytest.main([__file__])
