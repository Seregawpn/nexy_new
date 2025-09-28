#!/usr/bin/env python3
"""
Пример правильной инициализации StreamingWorkflowIntegration с модулями
"""

import asyncio
import logging
from typing import Dict, Any

# Импорты модулей
from modules.text_filtering import TextFilterManager
from modules.text_filtering.config import TextFilteringConfig
from modules.text_processing.core.text_processor import TextProcessor
from modules.audio_generation.core.audio_processor import AudioProcessor
from integrations.workflow_integrations.memory_workflow_integration import MemoryWorkflowIntegration

# Импорт интеграции
from integrations.workflow_integrations.streaming_workflow_integration import StreamingWorkflowIntegration

logger = logging.getLogger(__name__)

async def create_streaming_workflow() -> StreamingWorkflowIntegration:
    """
    Создание правильно настроенной StreamingWorkflowIntegration с модулями
    
    Returns:
        Инициализированная интеграция
    """
    try:
        # 1. Создаём и инициализируем модули
        logger.info("🔧 Инициализация модулей...")
        
        # Модуль фильтрации текста
        text_filter_config = TextFilteringConfig()
        text_filter_manager = TextFilterManager(text_filter_config)
        await text_filter_manager.initialize()
        
        # Модуль обработки текста
        text_processor = TextProcessor()
        await text_processor.initialize()
        
        # Модуль генерации аудио
        audio_processor = AudioProcessor()
        await audio_processor.initialize()
        
        # Модуль работы с памятью
        memory_workflow = MemoryWorkflowIntegration()
        await memory_workflow.initialize()
        
        # 2. Создаём интеграцию с модулями
        logger.info("🔗 Создание StreamingWorkflowIntegration...")
        streaming_integration = StreamingWorkflowIntegration(
            text_processor=text_processor,
            audio_processor=audio_processor,
            memory_workflow=memory_workflow,
            text_filter_manager=text_filter_manager  # Ключевое добавление!
        )
        
        # 3. Инициализируем интеграцию
        await streaming_integration.initialize()
        
        logger.info("✅ StreamingWorkflowIntegration создана и инициализирована")
        return streaming_integration
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания StreamingWorkflowIntegration: {e}")
        raise

async def example_usage():
    """
    Пример использования правильно настроенной интеграции
    """
    try:
        # Создаём интеграцию
        streaming_integration = await create_streaming_workflow()
        
        # Пример запроса
        request_data = {
            'session_id': 'test_session',
            'hardware_id': 'test_hardware',
            'text': 'The file main.py contains version 12.10. Check config.json.',
            'screenshot': None
        }
        
        logger.info("🚀 Обработка запроса...")
        
        # Обрабатываем запрос
        async for result in streaming_integration.process_request_streaming(request_data):
            if result.get('success'):
                if 'text_response' in result:
                    logger.info(f"📝 Text: {result['text_response']}")
                if 'audio_chunk' in result:
                    logger.info(f"🔊 Audio chunk: {len(result['audio_chunk'])} bytes")
            else:
                logger.error(f"❌ Error: {result.get('error')}")
        
        logger.info("✅ Обработка завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в примере: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
