#!/usr/bin/env python3
"""
Generate Welcome Audio Script

Скрипт для генерации предзаписанного аудио файла приветствия.
Использует Azure TTS (если доступен) или macOS say command.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent))

from modules.welcome_message.core.audio_generator import WelcomeAudioGenerator
from modules.welcome_message.core.types import WelcomeConfig

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_welcome_audio():
    """Генерирует аудио файл приветствия"""
    try:
        # Конфигурация
        config = WelcomeConfig(
            enabled=True,
            text="Hi! Nexy is here. How can I help you?",
            audio_file="assets/audio/welcome_en.mp3",
            fallback_to_tts=True,
            delay_sec=1.0,
            volume=0.8,
            voice="en-US-JennyNeural",
            sample_rate=48000,
            channels=1,
            bit_depth=16
        )
        
        logger.info("🎵 [GENERATE_AUDIO] Начинаю генерацию аудио приветствия")
        logger.info(f"📝 [GENERATE_AUDIO] Текст: '{config.text}'")
        logger.info(f"🎯 [GENERATE_AUDIO] Выходной файл: {config.audio_file}")
        
        # Создаем генератор
        generator = WelcomeAudioGenerator(config)
        
        # Генерируем аудио
        audio_data = await generator.generate_audio(config.text)
        
        if audio_data is None:
            logger.error("❌ [GENERATE_AUDIO] Не удалось сгенерировать аудио")
            return False
        
        # Сохраняем в файл
        output_path = Path(__file__).parent.parent / config.audio_file
        success = await generator.save_audio_to_file(audio_data, output_path)
        
        if success:
            duration_sec = len(audio_data) / config.sample_rate
            file_size = output_path.stat().st_size
            logger.info(f"✅ [GENERATE_AUDIO] Аудио успешно сгенерировано!")
            logger.info(f"📊 [GENERATE_AUDIO] Статистика:")
            logger.info(f"   - Длительность: {duration_sec:.1f} секунд")
            logger.info(f"   - Сэмплов: {len(audio_data)}")
            logger.info(f"   - Sample Rate: {config.sample_rate} Hz")
            logger.info(f"   - Каналы: {config.channels}")
            logger.info(f"   - Размер файла: {file_size} байт")
            logger.info(f"   - Путь: {output_path}")
            return True
        else:
            logger.error("❌ [GENERATE_AUDIO] Не удалось сохранить аудио файл")
            return False
            
    except Exception as e:
        logger.error(f"❌ [GENERATE_AUDIO] Критическая ошибка: {e}")
        return False


async def main():
    """Главная функция"""
    print("🎵 Генератор аудио приветствия для Nexy AI Assistant")
    print("=" * 60)
    
    success = await generate_welcome_audio()
    
    if success:
        print("\n✅ Аудио приветствия успешно сгенерировано!")
        print("🎯 Файл готов для использования в приложении")
    else:
        print("\n❌ Ошибка генерации аудио приветствия")
        print("🔧 Проверьте настройки и попробуйте снова")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
