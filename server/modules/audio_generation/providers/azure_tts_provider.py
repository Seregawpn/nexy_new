"""
Azure TTS Provider для генерации речи
"""

import logging
from typing import AsyncGenerator, Dict, Any, Optional
from integration.core.universal_provider_interface import UniversalProviderInterface

logger = logging.getLogger(__name__)

# Импорты Azure Speech SDK (с обработкой отсутствия)
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    speechsdk = None
    AZURE_SPEECH_AVAILABLE = False
    logger.warning("⚠️ Azure Speech SDK не найден - провайдер будет недоступен")

class AzureTTSProvider(UniversalProviderInterface):
    """
    Провайдер генерации речи с использованием Azure Cognitive Services Speech
    
    Основной провайдер для преобразования текста в речь с поддержкой
    streaming и различных форматов аудио.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Инициализация Azure TTS провайдера
        
        Args:
            config: Конфигурация провайдера
        """
        super().__init__(
            name="azure_tts",
            priority=1,  # Основной провайдер
            config=config
        )
        
        # Azure настройки
        self.speech_key = config.get('speech_key', '')
        self.speech_region = config.get('speech_region', '')
        self.voice_name = config.get('voice_name', 'en-US-AriaNeural')
        self.voice_style = config.get('voice_style', 'friendly')
        self.speech_rate = config.get('speech_rate', 1.0)
        self.speech_pitch = config.get('speech_pitch', 1.0)
        self.speech_volume = config.get('speech_volume', 1.0)
        
        # Аудио настройки
        self.audio_format = config.get('audio_format', 'riff-16khz-16bit-mono-pcm')
        self.sample_rate = config.get('sample_rate', 16000)
        self.channels = config.get('channels', 1)
        self.bits_per_sample = config.get('bits_per_sample', 16)
        
        # Таймауты
        self.timeout = config.get('timeout', 60)
        self.connection_timeout = config.get('connection_timeout', 30)
        
        # Speech config и synthesizer
        self.speech_config = None
        self.synthesizer = None
        
        self.is_available = AZURE_SPEECH_AVAILABLE and bool(self.speech_key and self.speech_region)
        
        logger.info(f"Azure TTS Provider initialized: available={self.is_available}")
    
    async def initialize(self) -> bool:
        """
        Инициализация Azure TTS провайдера
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            if not self.is_available:
                logger.error("Azure TTS Provider not available - missing dependencies or credentials")
                return False
            
            # Создаем speech config
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            
            # Настраиваем голос
            self.speech_config.speech_synthesis_voice_name = self.voice_name
            
            # Настраиваем аудио формат
            self.speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
            )
            
            # Создаем synthesizer
            self.synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # Используем встроенный аудио конфиг
            )
            
            # Тестируем подключение
            test_result = await self._test_connection()
            
            if test_result:
                self.is_initialized = True
                logger.info(f"Azure TTS Provider initialized successfully with voice: {self.voice_name}")
                return True
            else:
                logger.error("Azure TTS Provider test synthesis failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize Azure TTS Provider: {e}")
            return False
    
    async def process(self, input_data: str) -> AsyncGenerator[bytes, None]:
        """
        Обработка текста в речь с использованием Azure TTS
        
        Args:
            input_data: Текст для преобразования в речь
            
        Yields:
            Chunks аудио данных
        """
        try:
            if not self.is_initialized or not self.synthesizer:
                raise Exception("Azure TTS Provider not initialized")
            
            # Создаем SSML для лучшего контроля голоса
            ssml = self._create_ssml(input_data)
            
            # Выполняем синтез речи
            result = self.synthesizer.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                # Получаем аудио данные
                audio_data = result.audio_data
                
                if audio_data:
                    # Разбиваем на chunks для streaming
                    chunk_size = 4096  # 4KB chunks
                    for i in range(0, len(audio_data), chunk_size):
                        chunk = audio_data[i:i + chunk_size]
                        if chunk:
                            yield chunk
                    
                    logger.debug(f"Azure TTS Provider generated {len(audio_data)} bytes of audio")
                else:
                    raise Exception("No audio data generated")
                    
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                raise Exception(f"Synthesis canceled: {cancellation_details.reason} - {cancellation_details.error_details}")
            else:
                raise Exception(f"Synthesis failed with reason: {result.reason}")
                
        except Exception as e:
            logger.error(f"Azure TTS Provider processing error: {e}")
            raise e
    
    async def cleanup(self) -> bool:
        """
        Очистка ресурсов Azure TTS провайдера
        
        Returns:
            True если очистка успешна, False иначе
        """
        try:
            if self.synthesizer:
                self.synthesizer = None
            if self.speech_config:
                self.speech_config = None
                
            self.is_initialized = False
            logger.info("Azure TTS Provider cleaned up")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up Azure TTS Provider: {e}")
            return False
    
    def _create_ssml(self, text: str) -> str:
        """
        Создание SSML для синтеза речи
        
        Args:
            text: Текст для преобразования
            
        Returns:
            SSML строка
        """
        # Экранируем специальные символы
        escaped_text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        ssml = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
            <voice name="{self.voice_name}">
                <mstts:express-as style="{self.voice_style}" styledegree="1.0">
                    <prosody rate="{self.speech_rate}" pitch="{self.speech_pitch}" volume="{self.speech_volume}">
                        {escaped_text}
                    </prosody>
                </mstts:express-as>
            </voice>
        </speak>
        """
        
        return ssml.strip()
    
    async def _test_connection(self) -> bool:
        """
        Тестирование подключения к Azure TTS
        
        Returns:
            True если подключение работает, False иначе
        """
        try:
            if not self.synthesizer:
                return False
            
            # Простой тестовый синтез
            test_text = "Hello, this is a test."
            result = self.synthesizer.speak_text_async(test_text).get()
            
            return result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted
            
        except Exception as e:
            logger.warning(f"Azure TTS Provider connection test failed: {e}")
            return False
    
    async def _custom_health_check(self) -> bool:
        """
        Кастомная проверка здоровья Azure TTS провайдера
        
        Returns:
            True если провайдер здоров, False иначе
        """
        try:
            if not self.is_available or not self.synthesizer:
                return False
            
            # Простая проверка - тестовый синтез
            test_result = await self._test_connection()
            return test_result
            
        except Exception as e:
            logger.warning(f"Azure TTS Provider health check failed: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение расширенного статуса Azure TTS провайдера
        
        Returns:
            Словарь со статусом провайдера
        """
        base_status = super().get_status()
        
        # Добавляем специфичную информацию
        base_status.update({
            "provider_type": "azure_tts",
            "voice_name": self.voice_name,
            "voice_style": self.voice_style,
            "speech_rate": self.speech_rate,
            "speech_pitch": self.speech_pitch,
            "speech_volume": self.speech_volume,
            "audio_format": self.audio_format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bits_per_sample": self.bits_per_sample,
            "is_available": self.is_available,
            "speech_key_set": bool(self.speech_key),
            "speech_region_set": bool(self.speech_region),
            "azure_speech_available": AZURE_SPEECH_AVAILABLE
        })
        
        return base_status
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Получение расширенных метрик Azure TTS провайдера
        
        Returns:
            Словарь с метриками провайдера
        """
        base_metrics = super().get_metrics()
        
        # Добавляем специфичные метрики
        base_metrics.update({
            "provider_type": "azure_tts",
            "voice_name": self.voice_name,
            "audio_format": self.audio_format,
            "is_available": self.is_available,
            "speech_key_set": bool(self.speech_key),
            "speech_region_set": bool(self.speech_region)
        })
        
        return base_metrics
    
    def get_audio_info(self) -> Dict[str, Any]:
        """
        Получение информации об аудио формате
        
        Returns:
            Словарь с информацией об аудио
        """
        return {
            "format": self.audio_format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "bits_per_sample": self.bits_per_sample,
            "voice_name": self.voice_name,
            "voice_style": self.voice_style,
            "speech_rate": self.speech_rate,
            "speech_pitch": self.speech_pitch,
            "speech_volume": self.speech_volume
        }
