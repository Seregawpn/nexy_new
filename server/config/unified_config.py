#!/usr/bin/env python3
"""
Централизованная конфигурация для всего сервера Nexy
Объединяет все настройки из разных модулей в единую точку управления
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Конфигурация базы данных"""
    host: str = "localhost"
    port: int = 5432
    name: str = "voice_assistant_db"
    user: str = "postgres"
    password: str = ""
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', '5432')),
            name=os.getenv('DB_NAME', 'voice_assistant_db'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )

@dataclass
class GrpcConfig:
    """Конфигурация gRPC сервера"""
    host: str = "0.0.0.0"
    port: int = 50051
    max_workers: int = 10
    
    @classmethod
    def from_env(cls) -> 'GrpcConfig':
        return cls(
            host=os.getenv('GRPC_HOST', '0.0.0.0'),
            port=int(os.getenv('GRPC_PORT', '50051')),
            max_workers=int(os.getenv('MAX_WORKERS', '10'))
        )

@dataclass
class AudioConfig:
    """Конфигурация аудио (синхронизирована с клиентом)"""
    sample_rate: int = 48000
    chunk_size: int = 1024
    format: str = "int16"
    channels: int = 1
    bits_per_sample: int = 16
    
    # Azure TTS настройки
    azure_speech_key: str = ""
    azure_speech_region: str = ""
    azure_voice_name: str = "en-US-AriaNeural"
    azure_voice_style: str = "friendly"
    azure_speech_rate: float = 1.0
    azure_speech_pitch: float = 1.0
    azure_speech_volume: float = 1.0
    azure_audio_format: str = "riff-48khz-16bit-mono-pcm"
    
    # Streaming настройки
    streaming_chunk_size: int = 4096
    streaming_enabled: bool = True
    
    @classmethod
    def from_env(cls) -> 'AudioConfig':
        return cls(
            sample_rate=int(os.getenv('SAMPLE_RATE', '48000')),
            chunk_size=int(os.getenv('CHUNK_SIZE', '1024')),
            format=os.getenv('AUDIO_FORMAT', 'int16'),
            channels=int(os.getenv('AUDIO_CHANNELS', '1')),
            bits_per_sample=int(os.getenv('AUDIO_BITS_PER_SAMPLE', '16')),
            azure_speech_key=os.getenv('AZURE_SPEECH_KEY', ''),
            azure_speech_region=os.getenv('AZURE_SPEECH_REGION', ''),
            azure_voice_name=os.getenv('AZURE_VOICE_NAME', 'en-US-AriaNeural'),
            azure_voice_style=os.getenv('AZURE_VOICE_STYLE', 'friendly'),
            azure_speech_rate=float(os.getenv('AZURE_SPEECH_RATE', '1.0')),
            azure_speech_pitch=float(os.getenv('AZURE_SPEECH_PITCH', '1.0')),
            azure_speech_volume=float(os.getenv('AZURE_SPEECH_VOLUME', '1.0')),
            azure_audio_format=os.getenv('AZURE_AUDIO_FORMAT', 'riff-48khz-16bit-mono-pcm'),
            streaming_chunk_size=int(os.getenv('STREAMING_CHUNK_SIZE', '4096')),
            streaming_enabled=os.getenv('STREAMING_ENABLED', 'true').lower() == 'true'
        )

@dataclass
class TextProcessingConfig:
    """Конфигурация обработки текста"""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-exp"
    gemini_temperature: float = 0.7
    gemini_max_tokens: int = 2048
    
    # LangChain настройки
    langchain_model: str = "gemini-pro"
    langchain_temperature: float = 0.7
    
    # Fallback настройки
    fallback_timeout: int = 30
    circuit_breaker_threshold: int = 3
    circuit_breaker_timeout: int = 300
    
    # Производительность
    max_concurrent_requests: int = 10
    request_timeout: int = 60
    
    @classmethod
    def from_env(cls) -> 'TextProcessingConfig':
        return cls(
            gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
            gemini_model=os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp'),
            gemini_temperature=float(os.getenv('GEMINI_TEMPERATURE', '0.7')),
            gemini_max_tokens=int(os.getenv('GEMINI_MAX_TOKENS', '2048')),
            langchain_model=os.getenv('LANGCHAIN_MODEL', 'gemini-pro'),
            langchain_temperature=float(os.getenv('LANGCHAIN_TEMPERATURE', '0.7')),
            fallback_timeout=int(os.getenv('FALLBACK_TIMEOUT', '30')),
            circuit_breaker_threshold=int(os.getenv('CIRCUIT_BREAKER_THRESHOLD', '3')),
            circuit_breaker_timeout=int(os.getenv('CIRCUIT_BREAKER_TIMEOUT', '300')),
            max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '10')),
            request_timeout=int(os.getenv('REQUEST_TIMEOUT', '60'))
        )

@dataclass
class MemoryConfig:
    """Конфигурация управления памятью"""
    gemini_api_key: str = ""
    max_short_term_memory_size: int = 10240  # 10KB
    max_long_term_memory_size: int = 10240   # 10KB
    memory_timeout: float = 2.0
    analysis_timeout: float = 5.0
    memory_analysis_model: str = "gemini-1.5-flash"
    memory_analysis_temperature: float = 0.3
    
    @classmethod
    def from_env(cls) -> 'MemoryConfig':
        return cls(
            gemini_api_key=os.getenv('GEMINI_API_KEY', ''),
            max_short_term_memory_size=int(os.getenv('MAX_SHORT_TERM_MEMORY_SIZE', '10240')),
            max_long_term_memory_size=int(os.getenv('MAX_LONG_TERM_MEMORY_SIZE', '10240')),
            memory_timeout=float(os.getenv('MEMORY_TIMEOUT', '2.0')),
            analysis_timeout=float(os.getenv('ANALYSIS_TIMEOUT', '5.0')),
            memory_analysis_model=os.getenv('MEMORY_ANALYSIS_MODEL', 'gemini-1.5-flash'),
            memory_analysis_temperature=float(os.getenv('MEMORY_ANALYSIS_TEMPERATURE', '0.3'))
        )

@dataclass
class SessionConfig:
    """Конфигурация управления сессиями"""
    max_sessions: int = 100
    session_timeout: int = 3600  # 1 час
    hardware_id_length: int = 32
    
    @classmethod
    def from_env(cls) -> 'SessionConfig':
        return cls(
            max_sessions=int(os.getenv('MAX_SESSIONS', '100')),
            session_timeout=int(os.getenv('SESSION_TIMEOUT', '3600')),
            hardware_id_length=int(os.getenv('HARDWARE_ID_LENGTH', '32'))
        )

@dataclass
class InterruptConfig:
    """Конфигурация управления прерываниями"""
    global_interrupt_timeout: int = 300  # 5 минут
    session_interrupt_timeout: int = 60  # 1 минута
    max_active_sessions: int = 50
    
    @classmethod
    def from_env(cls) -> 'InterruptConfig':
        return cls(
            global_interrupt_timeout=int(os.getenv('GLOBAL_INTERRUPT_TIMEOUT', '300')),
            session_interrupt_timeout=int(os.getenv('SESSION_INTERRUPT_TIMEOUT', '60')),
            max_active_sessions=int(os.getenv('MAX_ACTIVE_SESSIONS', '50'))
        )

@dataclass
class LoggingConfig:
    """Конфигурация логирования"""
    level: str = "INFO"
    log_requests: bool = True
    log_responses: bool = False
    log_file: str = "server.log"
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        return cls(
            level=os.getenv('LOG_LEVEL', 'INFO'),
            log_requests=os.getenv('LOG_REQUESTS', 'true').lower() == 'true',
            log_responses=os.getenv('LOG_RESPONSES', 'false').lower() == 'true',
            log_file=os.getenv('LOG_FILE', 'server.log'),
            max_file_size=int(os.getenv('LOG_MAX_FILE_SIZE', '10485760')),
            backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5'))
        )

@dataclass
class UnifiedServerConfig:
    """Централизованная конфигурация всего сервера"""
    database: DatabaseConfig = field(default_factory=DatabaseConfig.from_env)
    grpc: GrpcConfig = field(default_factory=GrpcConfig.from_env)
    audio: AudioConfig = field(default_factory=AudioConfig.from_env)
    text_processing: TextProcessingConfig = field(default_factory=TextProcessingConfig.from_env)
    memory: MemoryConfig = field(default_factory=MemoryConfig.from_env)
    session: SessionConfig = field(default_factory=SessionConfig.from_env)
    interrupt: InterruptConfig = field(default_factory=InterruptConfig.from_env)
    logging: LoggingConfig = field(default_factory=LoggingConfig.from_env)
    
    def __post_init__(self):
        """Пост-инициализация для валидации"""
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Валидация всей конфигурации"""
        errors = []
        
        # Проверяем критические настройки
        if not self.text_processing.gemini_api_key:
            errors.append("GEMINI_API_KEY не установлен")
        
        if not self.audio.azure_speech_key:
            errors.append("AZURE_SPEECH_KEY не установлен")
            
        if not self.audio.azure_speech_region:
            errors.append("AZURE_SPEECH_REGION не установлен")
        
        # Проверяем диапазоны значений
        if not (0 <= self.text_processing.gemini_temperature <= 2):
            errors.append("gemini_temperature должен быть между 0 и 2")
            
        if not (0.5 <= self.audio.azure_speech_rate <= 2.0):
            errors.append("azure_speech_rate должен быть между 0.5 и 2.0")
            
        if self.audio.sample_rate not in [8000, 16000, 22050, 44100, 48000]:
            errors.append("sample_rate должен быть одним из: 8000, 16000, 22050, 44100, 48000")
        
        # Выводим предупреждения
        for error in errors:
            logger.warning(f"⚠️ {error}")
        
        if errors:
            logger.warning("⚠️ Конфигурация имеет предупреждения, но система может работать")
    
    def get_module_config(self, module_name: str) -> Dict[str, Any]:
        """
        Получение конфигурации для конкретного модуля
        
        Args:
            module_name: Имя модуля
            
        Returns:
            Словарь с конфигурацией модуля
        """
        config_mapping = {
            'database': self.database.__dict__,
            'grpc': self.grpc.__dict__,
            'audio': self.audio.__dict__,
            'text_processing': self.text_processing.__dict__,
            'memory': self.memory.__dict__,
            'session': self.session.__dict__,
            'interrupt': self.interrupt.__dict__,
            'logging': self.logging.__dict__
        }
        
        return config_mapping.get(module_name, {})
    
    def get_provider_config(self, provider_name: str) -> Dict[str, Any]:
        """
        Получение конфигурации для конкретного провайдера
        
        Args:
            provider_name: Имя провайдера
            
        Returns:
            Словарь с конфигурацией провайдера
        """
        provider_configs = {
            'gemini_live': {
                'api_key': self.text_processing.gemini_api_key,
                'model': self.text_processing.gemini_model,
                'temperature': self.text_processing.gemini_temperature,
                'max_tokens': self.text_processing.gemini_max_tokens,
                'timeout': self.text_processing.request_timeout
            },
            'langchain': {
                'model': self.text_processing.langchain_model,
                'temperature': self.text_processing.langchain_temperature,
                'api_key': self.text_processing.gemini_api_key,
                'timeout': self.text_processing.request_timeout
            },
            'azure_tts': {
                'speech_key': self.audio.azure_speech_key,
                'speech_region': self.audio.azure_speech_region,
                'voice_name': self.audio.azure_voice_name,
                'voice_style': self.audio.azure_voice_style,
                'speech_rate': self.audio.azure_speech_rate,
                'speech_pitch': self.audio.azure_speech_pitch,
                'speech_volume': self.audio.azure_speech_volume,
                'audio_format': self.audio.azure_audio_format,
                'sample_rate': self.audio.sample_rate,
                'channels': self.audio.channels,
                'bits_per_sample': self.audio.bits_per_sample,
                'timeout': self.text_processing.request_timeout
            },
            'postgresql': {
                'host': self.database.host,
                'port': self.database.port,
                'database': self.database.name,
                'user': self.database.user,
                'password': self.database.password
            }
        }
        
        return provider_configs.get(provider_name, {})
    
    def get_fallback_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации fallback менеджера
        
        Returns:
            Словарь с конфигурацией fallback
        """
        return {
            'timeout': self.text_processing.fallback_timeout,
            'circuit_breaker_threshold': self.text_processing.circuit_breaker_threshold,
            'circuit_breaker_timeout': self.text_processing.circuit_breaker_timeout,
            'max_concurrent_requests': self.text_processing.max_concurrent_requests
        }
    
    def get_streaming_config(self) -> Dict[str, Any]:
        """
        Получение конфигурации streaming
        
        Returns:
            Словарь с конфигурацией streaming
        """
        return {
            'chunk_size': self.audio.streaming_chunk_size,
            'enabled': self.audio.streaming_enabled,
            'sample_rate': self.audio.sample_rate,
            'channels': self.audio.channels,
            'bits_per_sample': self.audio.bits_per_sample
        }
    
    def save_to_yaml(self, file_path: Union[str, Path]) -> None:
        """
        Сохранение конфигурации в YAML файл
        
        Args:
            file_path: Путь к файлу
        """
        config_dict = {
            'database': self.database.__dict__,
            'grpc': self.grpc.__dict__,
            'audio': self.audio.__dict__,
            'text_processing': self.text_processing.__dict__,
            'memory': self.memory.__dict__,
            'session': self.session.__dict__,
            'interrupt': self.interrupt.__dict__,
            'logging': self.logging.__dict__
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
        
        logger.info(f"✅ Конфигурация сохранена в {file_path}")
    
    @classmethod
    def load_from_yaml(cls, file_path: Union[str, Path]) -> 'UnifiedServerConfig':
        """
        Загрузка конфигурации из YAML файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Экземпляр UnifiedServerConfig
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f)
        
        # Создаем экземпляры конфигураций из словаря
        database = DatabaseConfig(**config_dict.get('database', {}))
        grpc = GrpcConfig(**config_dict.get('grpc', {}))
        audio = AudioConfig(**config_dict.get('audio', {}))
        text_processing = TextProcessingConfig(**config_dict.get('text_processing', {}))
        memory = MemoryConfig(**config_dict.get('memory', {}))
        session = SessionConfig(**config_dict.get('session', {}))
        interrupt = InterruptConfig(**config_dict.get('interrupt', {}))
        logging_config = LoggingConfig(**config_dict.get('logging', {}))
        
        return cls(
            database=database,
            grpc=grpc,
            audio=audio,
            text_processing=text_processing,
            memory=memory,
            session=session,
            interrupt=interrupt,
            logging=logging_config
        )
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получение статуса всей конфигурации
        
        Returns:
            Словарь со статусом конфигурации
        """
        return {
            'database': {
                'host': self.database.host,
                'port': self.database.port,
                'name': self.database.name,
                'user': self.database.user,
                'password_set': bool(self.database.password)
            },
            'grpc': self.grpc.__dict__,
            'audio': {
                'sample_rate': self.audio.sample_rate,
                'chunk_size': self.audio.chunk_size,
                'format': self.audio.format,
                'azure_speech_key_set': bool(self.audio.azure_speech_key),
                'azure_speech_region_set': bool(self.audio.azure_speech_region),
                'azure_voice_name': self.audio.azure_voice_name,
                'streaming_enabled': self.audio.streaming_enabled
            },
            'text_processing': {
                'gemini_api_key_set': bool(self.text_processing.gemini_api_key),
                'gemini_model': self.text_processing.gemini_model,
                'gemini_temperature': self.text_processing.gemini_temperature,
                'max_concurrent_requests': self.text_processing.max_concurrent_requests
            },
            'memory': {
                'gemini_api_key_set': bool(self.memory.gemini_api_key),
                'max_short_term_memory_size': self.memory.max_short_term_memory_size,
                'max_long_term_memory_size': self.memory.max_long_term_memory_size,
                'memory_timeout': self.memory.memory_timeout
            },
            'session': self.session.__dict__,
            'interrupt': self.interrupt.__dict__,
            'logging': self.logging.__dict__
        }

# Глобальный экземпляр конфигурации
_config_instance: Optional[UnifiedServerConfig] = None

def get_config() -> UnifiedServerConfig:
    """
    Получение глобального экземпляра конфигурации
    
    Returns:
        Экземпляр UnifiedServerConfig
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = UnifiedServerConfig()
        logger.info("✅ Централизованная конфигурация инициализирована")
    return _config_instance

def reload_config() -> UnifiedServerConfig:
    """
    Перезагрузка конфигурации из переменных окружения
    
    Returns:
        Новый экземпляр UnifiedServerConfig
    """
    global _config_instance
    _config_instance = UnifiedServerConfig()
    logger.info("✅ Конфигурация перезагружена")
    return _config_instance

if __name__ == "__main__":
    # Тестирование конфигурации
    config = get_config()
    print("📊 Статус конфигурации:")
    status = config.get_status()
    
    for section, values in status.items():
        print(f"\n🔧 {section.upper()}:")
        for key, value in values.items():
            print(f"  {key}: {value}")
    
    # Сохраняем пример конфигурации
    config.save_to_yaml("server/config/unified_config_example.yaml")
    print("\n✅ Пример конфигурации сохранен в server/config/unified_config_example.yaml")
