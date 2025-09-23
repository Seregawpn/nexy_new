"""
Tests for WelcomeMessageIntegration
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock

from integration.integrations.welcome_message_integration import WelcomeMessageIntegration
from integration.core.event_bus import EventBus
from integration.core.state_manager import ApplicationStateManager
from integration.core.error_handler import ErrorHandler


class TestWelcomeMessageIntegration:
    """Тесты для WelcomeMessageIntegration"""
    
    def setup_method(self):
        """Настройка для каждого теста"""
        self.event_bus = EventBus()
        self.state_manager = ApplicationStateManager()
        self.error_handler = ErrorHandler(self.event_bus)
        
        self.integration = WelcomeMessageIntegration(
            event_bus=self.event_bus,
            state_manager=self.state_manager,
            error_handler=self.error_handler
        )
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Тест инициализации интеграции"""
        success = await self.integration.initialize()
        
        assert success is True
        assert self.integration._initialized is True
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Тест запуска и остановки интеграции"""
        await self.integration.initialize()
        
        # Запуск
        success = await self.integration.start()
        assert success is True
        assert self.integration._running is True
        
        # Остановка
        success = await self.integration.stop()
        assert success is True
        assert self.integration._running is False
    
    @pytest.mark.asyncio
    async def test_on_app_startup_disabled(self):
        """Тест обработки запуска при отключенном модуле"""
        await self.integration.initialize()
        await self.integration.start()
        
        # Отключаем модуль
        self.integration.config.enabled = False
        
        # Мокаем play_welcome_message
        with patch.object(self.integration, '_play_welcome_message') as mock_play:
            await self.integration._on_app_startup({"type": "app.startup"})
            
            # Должна быть задержка, но play_welcome_message не должен вызываться
            await asyncio.sleep(0.2)  # Ждем дольше чем delay_sec
            
            # Проверяем, что play_welcome_message не был вызван
            mock_play.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_on_app_startup_enabled(self):
        """Тест обработки запуска при включенном модуле"""
        await self.integration.initialize()
        await self.integration.start()
        
        # Включаем модуль
        self.integration.config.enabled = True
        
        # Мокаем play_welcome_message
        with patch.object(self.integration, '_play_welcome_message') as mock_play:
            await self.integration._on_app_startup({"type": "app.startup"})
            
            # Ждем задержку + немного больше
            await asyncio.sleep(1.2)
            
            # Проверяем, что play_welcome_message был вызван
            mock_play.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_play_welcome_message_success(self):
        """Тест успешного воспроизведения приветствия"""
        await self.integration.initialize()
        await self.integration.start()
        
        # Мокаем welcome_player.play_welcome
        mock_result = Mock()
        mock_result.success = True
        mock_result.method = "prerecorded"
        mock_result.duration_sec = 2.5
        mock_result.metadata = {"samples": 120000}
        
        with patch.object(self.integration.welcome_player, 'play_welcome', return_value=mock_result), \
             patch.object(self.integration, '_send_audio_to_playback') as mock_send:
            
            await self.integration._play_welcome_message()
            
            # Проверяем, что play_welcome был вызван
            self.integration.welcome_player.play_welcome.assert_called_once()
            
            # Проверяем, что аудио было отправлено
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_play_welcome_message_failure(self):
        """Тест неудачного воспроизведения приветствия"""
        await self.integration.initialize()
        await self.integration.start()
        
        # Мокаем welcome_player.play_welcome с ошибкой
        mock_result = Mock()
        mock_result.success = False
        mock_result.method = "none"
        mock_result.duration_sec = 0.0
        mock_result.error = "Test error"
        
        with patch.object(self.integration.welcome_player, 'play_welcome', return_value=mock_result), \
             patch.object(self.integration, '_send_audio_to_playback') as mock_send:
            
            await self.integration._play_welcome_message()
            
            # Проверяем, что play_welcome был вызван
            self.integration.welcome_player.play_welcome.assert_called_once()
            
            # Проверяем, что аудио НЕ было отправлено
            mock_send.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_send_audio_to_playback(self):
        """Тест отправки аудио в SpeechPlaybackIntegration"""
        await self.integration.initialize()
        await self.integration.start()
        
        import numpy as np
        test_audio = np.array([1, 2, 3, 4, 5], dtype=np.int16)
        
        # Мокаем get_audio_data
        with patch.object(self.integration.welcome_player, 'get_audio_data', return_value=test_audio), \
             patch.object(self.integration.event_bus, 'publish') as mock_publish:
            
            await self.integration._send_audio_to_playback(test_audio)
            
            # Проверяем, что событие было опубликовано
            mock_publish.assert_called_once()
            
            # Проверяем параметры события
            call_args = mock_publish.call_args
            assert call_args[0][0] == "playback.signal"
            
            data = call_args[0][1]
            assert "pcm" in data
            assert data["sample_rate"] == self.integration.config.sample_rate
            assert data["channels"] == self.integration.config.channels
            assert data["gain"] == self.integration.config.volume
            assert data["priority"] == 5
            assert data["pattern"] == "welcome_message"
    
    def test_get_status(self):
        """Тест получения статуса интеграции"""
        status = self.integration.get_status()
        
        assert "initialized" in status
        assert "running" in status
        assert "config" in status
        assert "player_state" in status
        
        # Проверяем конфигурацию
        config = status["config"]
        assert "enabled" in config
        assert "text" in config
        assert "audio_file" in config
        assert "fallback_to_tts" in config
        assert "delay_sec" in config
