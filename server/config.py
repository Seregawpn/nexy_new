import os
from typing import Optional
from pathlib import Path

# Загружаем переменные окружения из config.env
config_path = Path(__file__).parent / "config.env"  # config.env в той же папке
if config_path.exists():
    with open(config_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                # Используем rsplit для правильного разбора строк с = в значениях
                key, value = line.rsplit('=', 1)
                os.environ[key.strip()] = value.strip()

class Config:
    """Конфигурация приложения"""
    
    # =====================================================
    # GEMINI API
    # =====================================================
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # =====================================================
    # GOOGLE SEARCH API
    # =====================================================
    GSEARCH_API_KEY = os.getenv('GSEARCH_API_KEY')
    GSEARCH_CSE_ID = os.getenv('GSEARCH_CSE_ID')
    
    # =====================================================
    # EDGE TTS
    # =====================================================
    EDGE_TTS_VOICE = os.getenv('EDGE_TTS_VOICE', 'en-US-JennyNeural')
    EDGE_TTS_RATE = os.getenv('EDGE_TTS_RATE', '+0%')
    EDGE_TTS_VOLUME = os.getenv('EDGE_TTS_VOLUME', '+0%')
    
    # =====================================================
    # AZURE SPEECH TTS
    # =====================================================
    SPEECH_KEY = os.getenv('SPEECH_KEY')
    SPEECH_REGION = os.getenv('SPEECH_REGION')
    
    # =====================================================
    # gRPC СЕРВЕР
    # =====================================================
    GRPC_HOST = os.getenv('GRPC_HOST', '0.0.0.0')
    GRPC_PORT = int(os.getenv('GRPC_PORT', '50051'))
    
    # =====================================================
    # POSTGRESQL БАЗА ДАННЫХ
    # =====================================================
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', '5432'))
    DB_NAME = os.getenv('DB_NAME', 'voice_assistant_db')
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # =====================================================
    # АУДИО
    # =====================================================
    SAMPLE_RATE = int(os.getenv('SAMPLE_RATE', '48000'))
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', '1024'))
    
    # =====================================================
    # ЛОГИРОВАНИЕ
    # =====================================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    # =====================================================
    # ПРОИЗВОДИТЕЛЬНОСТЬ
    # =====================================================
    MAX_SENTENCE_LENGTH = int(os.getenv('MAX_SENTENCE_LENGTH', '200'))
    MAX_WORKERS = int(os.getenv('MAX_WORKERS', '10'))
    
    @classmethod
    def get_database_url(cls) -> str:
        """Получение строки подключения к базе данных"""
        if cls.DB_PASSWORD:
            return f"postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
        else:
            return f"postgresql://{cls.DB_USER}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}"
    
    @classmethod
    def validate(cls) -> bool:
        """Проверка конфигурации"""
        errors = []
        
        # Проверяем обязательные параметры
        if not cls.GEMINI_API_KEY:
            errors.append("GEMINI_API_KEY не установлен")
        
        # Проверяем параметры базы данных
        if not cls.DB_NAME:
            errors.append("DB_NAME не установлен")
        
        if not cls.DB_USER:
            errors.append("DB_USER не установлен")
        
        if errors:
            print("❌ Ошибки конфигурации:")
            for error in errors:
                print(f"  - {error}")
            return False
        
        print("✅ Конфигурация корректна")
        return True
