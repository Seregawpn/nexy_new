"""
Tests for WelcomeAudioGenerator
"""

import pytest
import asyncio
import numpy as np
import subprocess
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from ..core.audio_generator import WelcomeAudioGenerator
from ..core.types import WelcomeConfig


class TestWelcomeAudioGenerator:
    """Тесты для WelcomeAudioGenerator"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.config = WelcomeConfig(
            enabled=True,
            text="Test welcome message",
            audio_file="test_audio.mp3",
            fallback_to_tts=True,
            delay_sec=0.1,
            volume=0.8,
            sample_rate=48000,
            channels=1
        )
        self.generator = WelcomeAudioGenerator(self.config)
    
    def test_initialization(self):
        """Тест инициализации генератора"""
        assert self.generator.config == self.config
        assert self.generator._cache is None
        assert self.generator._cache_path is None
    
    @pytest.mark.asyncio
    async def test_generate_audio_success_macos_say(self):
        """Тест успешной генерации через macOS say"""
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        
        with patch.object(self.generator, '_generate_with_macos_say', return_value=test_audio):
            result = await self.generator.generate_audio("Test message")
        
        assert result is not None
        assert np.array_equal(result, test_audio)
    
    @pytest.mark.asyncio
    async def test_generate_audio_fallback_tone(self):
        """Тест fallback на tone генерацию"""
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        
        with patch.object(self.generator, '_generate_with_macos_say', return_value=None), \
             patch.object(self.generator, '_generate_fallback_tone', return_value=test_audio):
            result = await self.generator.generate_audio("Test message")
        
        assert result is not None
        assert np.array_equal(result, test_audio)
    
    @pytest.mark.asyncio
    async def test_generate_audio_all_failed(self):
        """Тест когда все методы генерации не удались"""
        with patch.object(self.generator, '_generate_with_macos_say', return_value=None), \
             patch.object(self.generator, '_generate_fallback_tone', return_value=None):
            result = await self.generator.generate_audio("Test message")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_audio_exception(self):
        """Тест обработки исключения при генерации"""
        with patch.object(self.generator, '_generate_with_macos_say', side_effect=Exception("Test error")):
            result = await self.generator.generate_audio("Test message")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_with_macos_say_success(self):
        """Тест успешной генерации через macOS say"""
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        
        with patch('subprocess.run') as mock_run, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('pydub.AudioSegment.from_file') as mock_audio, \
             patch('pathlib.Path.exists', return_value=True):
            
            # Настраиваем моки
            mock_run.return_value.returncode = 0
            mock_run.return_value.stderr = ""
            mock_temp.return_value.__enter__.return_value.name = "/tmp/test.aiff"
            mock_audio.return_value.get_array_of_samples.return_value = test_audio
            mock_audio.return_value.frame_rate = 48000
            mock_audio.return_value.channels = 1
            
            result = await self.generator._generate_with_macos_say("Test message")
        
        assert result is not None
        assert np.array_equal(result, test_audio)
    
    @pytest.mark.asyncio
    async def test_generate_with_macos_say_failure(self):
        """Тест неудачной генерации через macOS say"""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = "Error"
            
            result = await self.generator._generate_with_macos_say("Test message")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_generate_with_macos_say_timeout(self):
        """Тест таймаута macOS say"""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("say", 10)):
            result = await self.generator._generate_with_macos_say("Test message")
        
        assert result is None
    
    def test_generate_fallback_tone_success(self):
        """Тест успешной генерации fallback tone"""
        result = self.generator._generate_fallback_tone("Test message")
        
        assert result is not None
        assert isinstance(result, np.ndarray)
        assert result.dtype == np.int16
        assert len(result) > 0
        
        # Проверяем, что это моно аудио
        assert result.ndim == 1
    
    def test_generate_fallback_tone_exception(self):
        """Тест обработки исключения в fallback tone"""
        with patch('numpy.linspace', side_effect=Exception("Test error")):
            result = self.generator._generate_fallback_tone("Test message")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_save_audio_to_file_success(self):
        """Тест успешного сохранения аудио в файл"""
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        output_path = Path("/tmp/test_audio.mp3")
        
        with patch('pydub.AudioSegment') as mock_audio_segment, \
             patch('pathlib.Path.mkdir'):
            
            mock_audio_segment.return_value.export.return_value = None
            
            result = await self.generator.save_audio_to_file(test_audio, output_path)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_save_audio_to_file_exception(self):
        """Тест обработки исключения при сохранении"""
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        output_path = Path("/tmp/test_audio.mp3")
        
        with patch('pydub.AudioSegment', side_effect=Exception("Test error")), \
             patch('pathlib.Path.mkdir'):
            result = await self.generator.save_audio_to_file(test_audio, output_path)
        
        assert result is False
