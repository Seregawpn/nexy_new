"""
Tests for WelcomePlayer
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch, AsyncMock

from ..core.welcome_player import WelcomePlayer
from ..core.types import WelcomeConfig, WelcomeState, WelcomeResult


class TestWelcomePlayer:
    """Тесты для WelcomePlayer"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.config = WelcomeConfig(
            enabled=True,
            text="Test welcome message",
            audio_file="test_audio.mp3",
            fallback_to_tts=True,
            delay_sec=0.1,
            volume=0.8
        )
        self.player = WelcomePlayer(self.config)
    
    def test_initialization(self):
        """Тест инициализации плеера"""
        assert self.player.config == self.config
        assert self.player.state == WelcomeState.IDLE
        assert self.player._prerecorded_audio is None
        assert self.player._prerecorded_loaded is False
    
    def test_set_callbacks(self):
        """Тест установки коллбеков"""
        on_started = Mock()
        on_completed = Mock()
        on_error = Mock()
        
        self.player.set_callbacks(on_started, on_completed, on_error)
        
        assert self.player._on_started == on_started
        assert self.player._on_completed == on_completed
        assert self.player._on_error == on_error
    
    def test_is_ready(self):
        """Тест проверки готовности плеера"""
        # IDLE состояние - готов
        self.player.state = WelcomeState.IDLE
        assert self.player.is_ready() is True
        
        # COMPLETED состояние - готов
        self.player.state = WelcomeState.COMPLETED
        assert self.player.is_ready() is True
        
        # LOADING состояние - не готов
        self.player.state = WelcomeState.LOADING
        assert self.player.is_ready() is False
        
        # PLAYING состояние - не готов
        self.player.state = WelcomeState.PLAYING
        assert self.player.is_ready() is False
        
        # ERROR состояние - не готов
        self.player.state = WelcomeState.ERROR
        assert self.player.is_ready() is False
    
    def test_reset(self):
        """Тест сброса состояния плеера"""
        # Устанавливаем состояние
        self.player.state = WelcomeState.PLAYING
        self.player._prerecorded_audio = np.array([1, 2, 3])
        self.player._prerecorded_loaded = True
        
        # Сбрасываем
        self.player.reset()
        
        # Проверяем сброс
        assert self.player.state == WelcomeState.IDLE
        assert self.player._prerecorded_audio is None
        assert self.player._prerecorded_loaded is False
    
    @pytest.mark.asyncio
    async def test_play_welcome_disabled(self):
        """Тест воспроизведения при отключенном модуле"""
        self.config.enabled = False
        
        result = await self.player.play_welcome()
        
        assert result.success is False
        assert result.method == "none"
        assert "отключен" in result.error.lower() or "disabled" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_play_welcome_no_fallback(self):
        """Тест воспроизведения без fallback"""
        self.config.fallback_to_tts = False
        
        with patch.object(self.player, '_play_prerecorded', return_value=WelcomeResult(
            success=False, method="prerecorded", duration_sec=0.0, error="No audio file"
        )):
            result = await self.player.play_welcome()
        
        assert result.success is False
        assert result.method == "none"
        assert "все методы" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_play_welcome_success_prerecorded(self):
        """Тест успешного воспроизведения предзаписанного аудио"""
        expected_result = WelcomeResult(
            success=True,
            method="prerecorded",
            duration_sec=2.5,
            metadata={"samples": 120000}
        )
        
        with patch.object(self.player, '_play_prerecorded', return_value=expected_result):
            result = await self.player.play_welcome()
        
        assert result == expected_result
        assert self.player.state == WelcomeState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_play_welcome_success_tts(self):
        """Тест успешного воспроизведения через TTS"""
        # Предзаписанное аудио не удалось
        prerecorded_result = WelcomeResult(
            success=False,
            method="prerecorded",
            duration_sec=0.0,
            error="No audio file"
        )
        
        # TTS успешно
        tts_result = WelcomeResult(
            success=True,
            method="tts",
            duration_sec=2.0,
            metadata={"samples": 96000}
        )
        
        with patch.object(self.player, '_play_prerecorded', return_value=prerecorded_result), \
             patch.object(self.player, '_play_tts_fallback', return_value=tts_result):
            result = await self.player.play_welcome()
        
        assert result == tts_result
        assert self.player.state == WelcomeState.COMPLETED
    
    @pytest.mark.asyncio
    async def test_play_welcome_exception(self):
        """Тест обработки исключения при воспроизведении"""
        with patch.object(self.player, '_play_prerecorded', side_effect=Exception("Test error")):
            result = await self.player.play_welcome()
        
        assert result.success is False
        assert result.method == "error"
        assert "критическая ошибка" in result.error.lower()
        assert self.player.state == WelcomeState.ERROR
    
    @pytest.mark.asyncio
    async def test_play_prerecorded_success(self):
        """Тест успешного воспроизведения предзаписанного аудио"""
        # Мокаем загрузку аудио
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        self.player._prerecorded_audio = test_audio
        self.player._prerecorded_loaded = True
        
        result = await self.player._play_prerecorded()
        
        assert result.success is True
        assert result.method == "prerecorded"
        assert result.duration_sec > 0
        assert "samples" in result.metadata
    
    @pytest.mark.asyncio
    async def test_play_prerecorded_no_audio(self):
        """Тест воспроизведения предзаписанного аудио без файла"""
        self.player._prerecorded_loaded = True
        self.player._prerecorded_audio = None
        
        result = await self.player._play_prerecorded()
        
        assert result.success is False
        assert result.method == "prerecorded"
        assert "не найдено" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_play_tts_fallback_success(self):
        """Тест успешного TTS fallback"""
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        
        with patch.object(self.player.audio_generator, 'generate_audio', return_value=test_audio):
            result = await self.player._play_tts_fallback()
        
        assert result.success is True
        assert result.method == "tts"
        assert result.duration_sec > 0
        assert "samples" in result.metadata
    
    @pytest.mark.asyncio
    async def test_play_tts_fallback_no_audio(self):
        """Тест TTS fallback без генерации аудио"""
        with patch.object(self.player.audio_generator, 'generate_audio', return_value=None):
            result = await self.player._play_tts_fallback()
        
        assert result.success is False
        assert result.method == "tts"
        assert "не удалось сгенерировать" in result.error.lower()
    
    @pytest.mark.asyncio
    async def test_play_tts_fallback_exception(self):
        """Тест TTS fallback с исключением"""
        with patch.object(self.player.audio_generator, 'generate_audio', side_effect=Exception("TTS error")):
            result = await self.player._play_tts_fallback()
        
        assert result.success is False
        assert result.method == "tts"
        assert "ошибка tts fallback" in result.error.lower()
    
    def test_get_audio_data(self):
        """Тест получения аудио данных"""
        # Нет аудио данных
        assert self.player.get_audio_data() is None
        
        # Есть аудио данные
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        self.player._prerecorded_audio = test_audio
        assert np.array_equal(self.player.get_audio_data(), test_audio)
