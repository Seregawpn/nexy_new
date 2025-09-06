#!/usr/bin/env python3
"""
Тесты для AudioGenerator
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к серверу для импорта
sys.path.append(str(Path(__file__).parent.parent))

from audio_generator import AudioGenerator


async def test_audio_generator():
    """
    Тестирует AudioGenerator
    """
    print("🧪 Тестируем AudioGenerator...")
    
    try:
        generator = AudioGenerator()
        
        # Тест 1: Простая генерация
        print("📝 Тест 1: Простая генерация")
        audio = await generator.generate_audio("Hello, this is a test.")
        if audio is not None:
            print(f"✅ Тест 1 пройден: {len(audio)} сэмплов")
        else:
            print("❌ Тест 1 провален")
        
        # Тест 2: Потоковая генерация
        print("📝 Тест 2: Потоковая генерация")
        text = "This is the first sentence. This is the second sentence. This is the third sentence."
        
        chunk_count = 0
        async for audio_chunk in generator.generate_streaming_audio(text):
            chunk_count += 1
            print(f"✅ Чанк {chunk_count}: {len(audio_chunk)} сэмплов")
        
        print(f"✅ Тест 2 пройден: {chunk_count} чанков")
        print("🎉 Все тесты завершены!")
        
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")


if __name__ == "__main__":
    asyncio.run(test_audio_generator())
