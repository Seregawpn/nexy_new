"""
Конфигурация модуля Audio Generation
Использует централизованную конфигурацию
"""

from typing import Dict, Any, Optional

from config.unified_config import get_config

class AudioGenerationConfig:
    """Конфигурация модуля генерации аудио"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация конфигурации из централизованной системы
        
        Args:
            config: Словарь с конфигурацией (опционально, переопределяет централизованную)
        """
        # Получаем централизованную конфигурацию
        unified_config = get_config()
        self.config = config or {}
        
        # Используем централизованные настройки с возможностью переопределения
        self.azure_speech_key = self.config.get('azure_speech_key', unified_config.audio.azure_speech_key)
        self.azure_speech_region = self.config.get('azure_speech_region', unified_config.audio.azure_speech_region)
        self.azure_voice_name = self.config.get('azure_voice_name', unified_config.audio.azure_voice_name)
        self.azure_voice_style = self.config.get('azure_voice_style', unified_config.audio.azure_voice_style)
        self.azure_speech_rate = self.config.get('azure_speech_rate', unified_config.audio.azure_speech_rate)
        self.azure_speech_pitch = self.config.get('azure_speech_pitch', unified_config.audio.azure_speech_pitch)
        self.azure_speech_volume = self.config.get('azure_speech_volume', unified_config.audio.azure_speech_volume)
        
        # Настройки аудио формата
        self.audio_format = self.config.get('audio_format', unified_config.audio.azure_audio_format)
        self.sample_rate = self.config.get('sample_rate', unified_config.audio.sample_rate)
        self.channels = self.config.get('channels', unified_config.audio.channels)
        self.bits_per_sample = self.config.get('bits_per_sample', unified_config.audio.bits_per_sample)
        
        # Настройки производительности
        self.max_concurrent_requests = self.config.get('max_concurrent_requests', unified_config.text_processing.max_concurrent_requests)
        self.request_timeout = self.config.get('request_timeout', unified_config.text_processing.request_timeout)
        self.connection_timeout = self.config.get('connection_timeout', 30)
        
        # Настройки streaming
        self.streaming_chunk_size = self.config.get('streaming_chunk_size', unified_config.audio.streaming_chunk_size)
        self.streaming_enabled = self.config.get('streaming_enabled', unified_config.audio.streaming_enabled)
        
        # Настройки логирования
        self.log_level = self.config.get('log_level', unified_config.logging.level)
        self.log_requests = self.config.get('log_requests', unified_config.logging.log_requests)
        self.log_responses = self.config.get('log_responses', unified_config.logging.log_responses)
        
    def get_azure_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации Azure TTS
        
        Returns:
            Словарь с конфигурацией Azure
        """
        return {
            'speech_key': self.azure_speech_key,
            'speech_region': self.azure_speech_region,
            'voice_name': self.azure_voice_name,
            'voice_style': self.azure_voice_style,
            'speech_rate': self.azure_speech_rate,
            'speech_pitch': self.azure_speech_pitch,
            'speech_volume': self.azure_speech_volume,
            'audio_format': self.audio_format,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bits_per_sample': self.bits_per_sample,
            'timeout': self.request_timeout,
            'connection_timeout': self.connection_timeout
        }
    
    def get_streaming_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации streaming
        
        Returns:
            Словарь с конфигурацией streaming
        """
        return {
            'chunk_size': self.streaming_chunk_size,
            'enabled': self.streaming_enabled,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bits_per_sample': self.bits_per_sample
        }
    
    def validate(self) -> bool:
        """
        Валидация конфигурации
        
        Returns:
            True если конфигурация валидна, False иначе
        """
        # Проверяем наличие Azure ключей
        if not self.azure_speech_key:
            print("⚠️ AZURE_SPEECH_KEY не установлен")
            return False
            
        if not self.azure_speech_region:
            print("⚠️ AZURE_SPEECH_REGION не установлен")
            return False
            
        # Проверяем корректность параметров речи
        if not (0.5 <= self.azure_speech_rate <= 2.0):
            print("❌ azure_speech_rate должен быть между 0.5 и 2.0")
            return False
            
        if not (0.5 <= self.azure_speech_pitch <= 2.0):
            print("❌ azure_speech_pitch должен быть между 0.5 и 2.0")
            return False
            
        if not (0.0 <= self.azure_speech_volume <= 1.0):
            print("❌ azure_speech_volume должен быть между 0.0 и 1.0")
            return False
            
        # Проверяем корректность аудио параметров
        if self.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            print("❌ sample_rate должен быть одним из: 8000, 16000, 22050, 44100, 48000")
            return False
            
        if self.channels not in [1, 2]:
            print("❌ channels должен быть 1 (моно) или 2 (стерео)")
            return False
            
        if self.bits_per_sample not in [8, 16, 24, 32]:
            print("❌ bits_per_sample должен быть одним из: 8, 16, 24, 32")
            return False
            
        if self.request_timeout <= 0:
            print("❌ request_timeout должен быть положительным")
            return False
            
        if self.streaming_chunk_size <= 0:
            print("❌ streaming_chunk_size должен быть положительным")
            return False
            
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса конфигурации
        
        Returns:
            Словарь со статусом конфигурации
        """
        return {
            'azure_speech_key_set': bool(self.azure_speech_key),
            'azure_speech_region_set': bool(self.azure_speech_region),
            'azure_voice_name': self.azure_voice_name,
            'azure_voice_style': self.azure_voice_style,
            'azure_speech_rate': self.azure_speech_rate,
            'azure_speech_pitch': self.azure_speech_pitch,
            'azure_speech_volume': self.azure_speech_volume,
            'audio_format': self.audio_format,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'bits_per_sample': self.bits_per_sample,
            'max_concurrent_requests': self.max_concurrent_requests,
            'request_timeout': self.request_timeout,
            'connection_timeout': self.connection_timeout,
            'streaming_chunk_size': self.streaming_chunk_size,
            'streaming_enabled': self.streaming_enabled,
            'log_level': self.log_level,
            'log_requests': self.log_requests,
            'log_responses': self.log_responses
        }
    
    def get_voice_options(self) -> Dict[str, list]:
        """
        Получение доступных опций голоса
        
        Returns:
            Словарь с доступными опциями
        """
        return {
            'voice_names': [
                'en-US-AriaNeural',
                'en-US-DavisNeural',
                'en-US-JennyNeural',
                'en-US-GuyNeural',
                'en-US-JaneNeural',
                'en-US-JasonNeural',
                'en-US-NancyNeural',
                'en-US-TonyNeural',
                'en-US-MichelleNeural',
                'en-US-ChristopherNeural'
            ],
            'voice_styles': [
                'friendly',
                'cheerful',
                'sad',
                'angry',
                'fearful',
                'disgruntled',
                'serious',
                'affectionate',
                'gentle',
                'calm'
            ],
            'audio_formats': [
                'riff-16khz-16bit-mono-pcm',
                'riff-24khz-16bit-mono-pcm',
                'riff-48khz-16bit-mono-pcm',
                'riff-22050hz-16bit-mono-pcm',
                'riff-44100hz-16bit-mono-pcm',
                'audio-16khz-32kbitrate-mono-mp3',
                'audio-16khz-64kbitrate-mono-mp3',
                'audio-16khz-128kbitrate-mono-mp3',
                'audio-24khz-48kbitrate-mono-mp3',
                'audio-24khz-96kbitrate-mono-mp3',
                'audio-24khz-160kbitrate-mono-mp3',
                'audio-48khz-96kbitrate-mono-mp3',
                'audio-48khz-192kbitrate-mono-mp3'
            ]
        }
