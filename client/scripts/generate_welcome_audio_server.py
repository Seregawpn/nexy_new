#!/usr/bin/env python3
"""
Generate Welcome Audio Script - Server AudioGenerator Version

Скрипт для генерации предзаписанного аудио файла приветствия
используя серверный AudioGenerator с Azure TTS.
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Добавляем путь к серверу
server_path = Path(__file__).parent.parent.parent / "server"
sys.path.append(str(server_path))

# Добавляем путь к модулям клиента
client_path = Path(__file__).parent.parent
sys.path.append(str(client_path))

from audio_generator import AudioGenerator
from config import Config

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def generate_welcome_audio():
    """Генерирует аудио файл приветствия используя серверный AudioGenerator"""
    try:
        # Проверяем конфигурацию Azure TTS
        if not Config.SPEECH_KEY or not Config.SPEECH_REGION:
            logger.warning("⚠️ Azure TTS не настроен, используем fallback методы")
            logger.info("💡 Для получения высококачественного аудио настройте SPEECH_KEY и SPEECH_REGION в server/config.env")
        else:
            logger.info(f"✅ Azure TTS настроен: Region={Config.SPEECH_REGION}")
        
        # Конфигурация приветствия
        welcome_text = "Hi! Nexy is here. How can I help you?"
        output_file = "assets/audio/welcome_en.mp3"
        
        logger.info("🎵 [SERVER_AUDIO_GEN] Начинаю генерацию аудио приветствия")
        logger.info(f"📝 [SERVER_AUDIO_GEN] Текст: '{welcome_text}'")
        logger.info(f"🎯 [SERVER_AUDIO_GEN] Выходной файл: {output_file}")
        
        # Создаем генератор с голосом по умолчанию
        generator = AudioGenerator(voice="en-US-JennyNeural")
        
        # Генерируем аудио
        logger.info("🎵 [SERVER_AUDIO_GEN] Генерирую аудио через серверный AudioGenerator...")
        audio_data = await generator.generate_audio(welcome_text)
        
        if audio_data is None:
            logger.error("❌ [SERVER_AUDIO_GEN] Не удалось сгенерировать аудио")
            return False
        
        # Сохраняем в файл
        output_path = Path(__file__).parent.parent / output_file
        
        # Создаем директорию если не существует
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Конвертируем numpy массив в AudioSegment
        from pydub import AudioSegment
        audio_segment = AudioSegment(
            audio_data.tobytes(),
            frame_rate=48000,  # Серверный генератор всегда использует 48000Hz
            sample_width=2,    # 16-bit
            channels=1         # mono
        )
        
        # Сохраняем в MP3
        audio_segment.export(output_path, format="mp3")
        
        # Статистика
        duration_sec = len(audio_data) / 48000
        file_size = output_path.stat().st_size
        
        logger.info(f"✅ [SERVER_AUDIO_GEN] Аудио успешно сгенерировано!")
        logger.info(f"📊 [SERVER_AUDIO_GEN] Статистика:")
        logger.info(f"   - Длительность: {duration_sec:.1f} секунд")
        logger.info(f"   - Сэмплов: {len(audio_data)}")
        logger.info(f"   - Sample Rate: 48000 Hz")
        logger.info(f"   - Каналы: 1 (mono)")
        logger.info(f"   - Размер файла: {file_size} байт")
        logger.info(f"   - Путь: {output_path}")
        
        # Проверяем качество аудио
        if duration_sec < 1.0:
            logger.warning("⚠️ Аудио слишком короткое, возможно проблема с генерацией")
        elif duration_sec > 10.0:
            logger.warning("⚠️ Аудио слишком длинное, возможно проблема с генерацией")
        else:
            logger.info("✅ Длительность аудио в нормальном диапазоне")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ [SERVER_AUDIO_GEN] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Главная функция"""
    print("🎵 Генератор аудио приветствия (Server AudioGenerator)")
    print("=" * 60)
    
    # Проверяем конфигурацию
    logger.info("🔍 Проверка конфигурации...")
    
    if Config.SPEECH_KEY and Config.SPEECH_REGION:
        logger.info("✅ Azure TTS настроен - будет использован высококачественный голос")
    else:
        logger.warning("⚠️ Azure TTS не настроен - будет использован fallback")
        logger.info("💡 Для настройки Azure TTS добавьте в server/config.env:")
        logger.info("   SPEECH_KEY=your_azure_speech_key")
        logger.info("   SPEECH_REGION=your_azure_region")
    
    success = await generate_welcome_audio()
    
    if success:
        print("\n✅ Аудио приветствия успешно сгенерировано!")
        print("🎯 Файл готов для использования в приложении")
        print("🎵 Качество: Azure TTS (если настроен) или macOS say fallback")
    else:
        print("\n❌ Ошибка генерации аудио приветствия")
        print("🔧 Проверьте настройки и попробуйте снова")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
