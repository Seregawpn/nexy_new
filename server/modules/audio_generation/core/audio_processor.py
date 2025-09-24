"""
Основной AudioProcessor - координатор модуля генерации аудио
"""

import logging
from typing import Dict, Any, Optional, AsyncGenerator
from modules.audio_generation.config import AudioGenerationConfig
from modules.audio_generation.providers.azure_tts_provider import AzureTTSProvider

logger = logging.getLogger(__name__)

class AudioProcessor:
    """
    Основной процессор аудио
    
    Координирует работу Azure TTS провайдера и обеспечивает
    единый интерфейс для генерации речи из текста.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация процессора аудио
        
        Args:
            config: Конфигурация модуля
        """
        self.config = AudioGenerationConfig(config)
        self.provider = None
        self.is_initialized = False
        
        logger.info("AudioProcessor initialized")
    
    async def initialize(self) -> bool:
        """
        Инициализация процессора аудио
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Initializing AudioProcessor...")
            
            # Валидируем конфигурацию
            if not self.config.validate():
                logger.error("Audio generation configuration validation failed")
                return False
            
            # Создаем провайдер
            await self._create_provider()
            
            # Инициализируем провайдер
            if not await self.provider.initialize():
                logger.error("Failed to initialize Azure TTS provider")
                return False
            
            self.is_initialized = True
            logger.info("AudioProcessor initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize AudioProcessor: {e}")
            return False
    
    async def _create_provider(self):
        """Создание провайдера аудио"""
        try:
            # Azure TTS Provider (единственный провайдер)
            azure_config = self.config.get_azure_config()
            self.provider = AzureTTSProvider(azure_config)
            
            logger.info("Created Azure TTS provider")
            
        except Exception as e:
            logger.error(f"Error creating provider: {e}")
            raise e
    
    async def generate_speech(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Генерация речи из текста
        
        Args:
            text: Текст для преобразования в речь
            
        Yields:
            Chunks аудио данных
        """
        try:
            if not self.is_initialized:
                raise Exception("AudioProcessor not initialized")
            
            logger.debug(f"Generating speech for text: {text[:100]}...")
            
            async for audio_chunk in self.provider.process(text):
                yield audio_chunk
                
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise e
    
    async def generate_speech_streaming(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Потоковая генерация речи из текста
        
        Args:
            text: Текст для преобразования в речь
            
        Yields:
            Chunks аудио данных в реальном времени
        """
        try:
            if not self.is_initialized:
                raise Exception("AudioProcessor not initialized")
            
            logger.debug(f"Streaming speech generation for text: {text[:100]}...")
            
            # Получаем streaming конфигурацию
            streaming_config = self.config.get_streaming_config()
            
            if not streaming_config['enabled']:
                logger.warning("Streaming is disabled, falling back to regular generation")
                async for chunk in self.generate_speech(text):
                    yield chunk
                return
            
            # Потоковая генерация через провайдер
            chunk_size = streaming_config['chunk_size']
            async for audio_chunk in self.provider.process(text):
                # Разбиваем на меньшие chunks для streaming
                for i in range(0, len(audio_chunk), chunk_size):
                    chunk = audio_chunk[i:i + chunk_size]
                    if chunk:
                        yield chunk
                
        except Exception as e:
            logger.error(f"Error in streaming speech generation: {e}")
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов процессора
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            logger.info("Cleaning up AudioProcessor...")
            
            # Очищаем провайдер
            if self.provider:
                await self.provider.cleanup()
            
            self.is_initialized = False
            logger.info("AudioProcessor cleaned up successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up AudioProcessor: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса процессора
        
        Returns:
            Словарь со статусом процессора
        """
        status = {
            "is_initialized": self.is_initialized,
            "config_status": self.config.get_status(),
            "provider": None
        }
        
        # Добавляем статус провайдера
        if self.provider:
            status["provider"] = self.provider.get_status()
        
        return status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение метрик процессора
        
        Returns:
            Словарь с метриками процессора
        """
        metrics = {
            "is_initialized": self.is_initialized,
            "provider": None
        }
        
        # Добавляем метрики провайдера
        if self.provider:
            metrics["provider"] = self.provider.get_metrics()
        
        return metrics
    
    def get_audio_info(self) -> Dict[str, Any]:
        """
        Получение информации об аудио формате
        
        Returns:
            Словарь с информацией об аудио
        """
        if self.provider:
            return self.provider.get_audio_info()
        else:
            return {
                "format": self.config.audio_format,
                "sample_rate": self.config.sample_rate,
                "channels": self.config.channels,
                "bits_per_sample": self.config.bits_per_sample,
                "voice_name": self.config.azure_voice_name,
                "voice_style": self.config.azure_voice_style,
                "speech_rate": self.config.azure_speech_rate,
                "speech_pitch": self.config.azure_speech_pitch,
                "speech_volume": self.config.azure_speech_volume
            }
    
    def get_voice_options(self) -> Dict[str, list]:
        """
        Получение доступных опций голоса
        
        Returns:
            Словарь с доступными опциями
        """
        return self.config.get_voice_options()
    
    def update_voice_settings(self, voice_settings: Dict[str, Any]) -> bool:
        """
        Обновление настроек голоса
        
        Args:
            voice_settings: Новые настройки голоса
            
        Returns:
            True если настройки обновлены, False иначе
        """
        try:
            if not self.is_initialized or not self.provider:
                logger.warning("Cannot update voice settings - processor not initialized")
                return False
            
            # Обновляем настройки в конфигурации
            if 'voice_name' in voice_settings:
                self.config.azure_voice_name = voice_settings['voice_name']
            if 'voice_style' in voice_settings:
                self.config.azure_voice_style = voice_settings['voice_style']
            if 'speech_rate' in voice_settings:
                self.config.azure_speech_rate = voice_settings['speech_rate']
            if 'speech_pitch' in voice_settings:
                self.config.azure_speech_pitch = voice_settings['speech_pitch']
            if 'speech_volume' in voice_settings:
                self.config.azure_speech_volume = voice_settings['speech_volume']
            
            # Обновляем настройки в провайдере
            if hasattr(self.provider, 'voice_name'):
                self.provider.voice_name = self.config.azure_voice_name
            if hasattr(self.provider, 'voice_style'):
                self.provider.voice_style = self.config.azure_voice_style
            if hasattr(self.provider, 'speech_rate'):
                self.provider.speech_rate = self.config.azure_speech_rate
            if hasattr(self.provider, 'speech_pitch'):
                self.provider.speech_pitch = self.config.azure_speech_pitch
            if hasattr(self.provider, 'speech_volume'):
                self.provider.speech_volume = self.config.azure_speech_volume
            
            logger.info(f"Voice settings updated: {voice_settings}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating voice settings: {e}")
            return False
    
    def reset_metrics(self):
        """Сброс метрик процессора"""
        if self.provider:
            self.provider.reset_metrics()
        logger.info("AudioProcessor metrics reset")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Получение краткой сводки по процессору
        
        Returns:
            Словарь со сводкой
        """
        summary = {
            "is_initialized": self.is_initialized,
            "provider_name": "azure_tts",
            "provider_available": self.provider.is_available if self.provider else False,
            "config_valid": self.config.validate(),
            "audio_info": self.get_audio_info()
        }
        
        return summary
    
    def __str__(self) -> str:
        """Строковое представление процессора"""
        return f"AudioProcessor(initialized={self.is_initialized}, provider={'azure_tts' if self.provider else 'none'})"
    
    def __repr__(self) -> str:
        """Представление процессора для отладки"""
        return (
            f"AudioProcessor("
            f"initialized={self.is_initialized}, "
            f"provider={'azure_tts' if self.provider else 'none'}, "
            f"available={self.provider.is_available if self.provider else False}"
            f")"
        )
