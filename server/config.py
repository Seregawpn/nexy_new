import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Config:
    """Конфигурация приложения"""
    
    # Google Gemini API
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    GEMINI_MODEL = "gemini-2.5-flash-lite"
    
    # Edge-TTS настройки
    DEFAULT_VOICE = "ru-RU-SvetlanaNeural"  # Русский голос по умолчанию
    FALLBACK_VOICE = "en-US-JennyNeural"    # Английский голос как fallback
    
    # Доступные голоса
    VOICES = {
        "ru": "ru-RU-SvetlanaNeural",
        "en": "en-US-JennyNeural",
        "ru-male": "ru-RU-DmitryNeural",
        "en-male": "en-US-GuyNeural"
    }
    
    # Настройки аудио
    AUDIO_RATE = "+0%"      # Скорость речи
    AUDIO_VOLUME = "+0%"    # Громкость
    AUDIO_PITCH = "+0Hz"    # Тон
    
    # Настройки обработки
    MAX_SENTENCE_LENGTH = 200  # Максимальная длина предложения
    BUFFER_SIZE = 1024         # Размер буфера для аудио
    TEMP_DIR = "temp_audio"    # Временная директория для аудио
    
    # Настройки воспроизведения - улучшены для стабильности
    PLAYBACK_CHUNK_SIZE = 8192  # Увеличен с 4096 до 8192
    SAMPLE_RATE = 44100         # Увеличен с 24000 до 44100 для лучшего качества
    
    @classmethod
    def validate(cls):
        """Проверяет корректность конфигурации"""
        if not cls.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY не установлен в переменных окружения")
        
        # Создаем временную директорию если её нет
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        return True
