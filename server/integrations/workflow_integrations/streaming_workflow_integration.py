#!/usr/bin/env python3
"""
StreamingWorkflowIntegration - управляет потоком: текст → аудио → клиент
"""

import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamingWorkflowIntegration:
    """
    Управляет потоком обработки: получение текста → обработка → генерация аудио → стриминг клиенту
    """
    
    def __init__(self, text_processor=None, audio_processor=None, memory_workflow=None):
        """
        Инициализация StreamingWorkflowIntegration
        
        Args:
            text_processor: Модуль обработки текста
            audio_processor: Модуль генерации аудио
            memory_workflow: Workflow интеграция для работы с памятью
        """
        self.text_processor = text_processor
        self.audio_processor = audio_processor
        self.memory_workflow = memory_workflow
        self.is_initialized = False
        
        logger.info("StreamingWorkflowIntegration создан")
    
    async def initialize(self) -> bool:
        """
        Инициализация интеграции
        
        Returns:
            True если инициализация успешна, False иначе
        """
        try:
            logger.info("Инициализация StreamingWorkflowIntegration...")
            
            # Проверяем доступность модулей
            if not self.text_processor:
                logger.warning("⚠️ TextProcessor не предоставлен")
            
            if not self.audio_processor:
                logger.warning("⚠️ AudioProcessor не предоставлен")
            
            if not self.memory_workflow:
                logger.warning("⚠️ MemoryWorkflow не предоставлен")
            
            self.is_initialized = True
            logger.info("✅ StreamingWorkflowIntegration инициализирован успешно")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации StreamingWorkflowIntegration: {e}")
            return False
    
    async def process_request_streaming(self, request_data: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Основной метод обработки запроса с стримингом
        
        Args:
            request_data: Данные запроса (текст, скриншот, hardware_id, session_id)
            
        Yields:
            Результаты обработки (текстовые чанки, аудио чанки, статус)
        """
        if not self.is_initialized:
            logger.error("❌ StreamingWorkflowIntegration не инициализирован")
            yield {
                'success': False,
                'error': 'StreamingWorkflowIntegration not initialized',
                'text_response': '',
                'audio_chunks': []
            }
            return
        
        try:
            logger.info(f"🔄 Начало обработки запроса: {request_data.get('session_id', 'unknown')}")
            
            # 1. Получение контекста памяти (параллельно)
            memory_context = await self._get_memory_context_parallel(
                request_data.get('hardware_id', 'unknown')
            )
            
            # 2. Обработка текста + скриншота
            processed_text = await self._process_text_with_context(
                request_data.get('text', ''),
                request_data.get('screenshot'),
                memory_context
            )
            
            # 3. Генерация аудио по предложениям
            audio_chunks = []
            audio_generated = False
            
            async for audio_chunk in self._generate_audio_streaming(processed_text):
                audio_chunks.append(audio_chunk)
                audio_generated = True
                yield {
                    'success': True,
                    'text_response': processed_text,
                    'audio_chunk': audio_chunk,
                    'audio_chunks': audio_chunks
                }
            
            # Если аудио не было сгенерировано, возвращаем текстовый ответ
            if not audio_generated:
                yield {
                    'success': True,
                    'text_response': processed_text,
                    'audio_chunks': []
                }
            
            logger.info(f"✅ Запрос обработан успешно: {len(audio_chunks)} аудио чанков")
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса: {e}")
            yield {
                'success': False,
                'error': str(e),
                'text_response': '',
                'audio_chunks': []
            }
    
    async def _get_memory_context_parallel(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Неблокирующее получение контекста памяти
        
        Args:
            hardware_id: Идентификатор оборудования
            
        Returns:
            Контекст памяти или None при ошибке
        """
        try:
            if not self.memory_workflow:
                logger.debug("MemoryWorkflow не доступен, пропускаем получение памяти")
                return None
            
            logger.debug(f"Получение контекста памяти для {hardware_id}")
            memory_context = await self.memory_workflow.get_memory_context_parallel(hardware_id)
            
            if memory_context:
                logger.debug(f"✅ Получен контекст памяти: {len(memory_context)} элементов")
            else:
                logger.debug("⚠️ Контекст памяти пуст")
            
            return memory_context
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения контекста памяти: {e}")
            return None
    
    async def _process_text_with_context(self, text: str, screenshot: Optional[str], memory_context: Optional[Dict[str, Any]]) -> str:
        """
        Обработка текста с учетом скриншота и контекста памяти
        
        Args:
            text: Исходный текст
            screenshot: Скриншот в base64 (опционально)
            memory_context: Контекст памяти (опционально)
            
        Returns:
            Обработанный текст
        """
        try:
            # Объединяем текст с контекстом памяти
            enriched_text = self._enrich_with_memory(text, memory_context)
            
            # Обрабатываем через TextProcessor если доступен
            if self.text_processor and hasattr(self.text_processor, 'process_text'):
                logger.debug("Обработка текста через TextProcessor")
                try:
                    # Получаем первый результат из async generator
                    async for processed_sentence in self.text_processor.process_text(enriched_text):
                        return processed_sentence  # Возвращаем первое предложение
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обработки через TextProcessor: {e}")
                    return enriched_text
            else:
                logger.debug("TextProcessor не доступен, возвращаем обогащенный текст")
                return enriched_text
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки текста: {e}")
            return text  # Возвращаем исходный текст при ошибке
    
    def _enrich_with_memory(self, text: str, memory_context: Optional[Dict[str, Any]]) -> str:
        """
        Объединение текста с контекстом памяти
        
        Args:
            text: Исходный текст
            memory_context: Контекст памяти
            
        Returns:
            Обогащенный текст
        """
        if not memory_context:
            return text
        
        try:
            # Простое объединение - в реальной реализации здесь может быть более сложная логика
            memory_info = memory_context.get('recent_context', '')
            if memory_info:
                enriched_text = f"Контекст: {memory_info}\n\n{text}"
                logger.debug("Текст обогащен контекстом памяти")
                return enriched_text
            
            return text
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка обогащения текста памятью: {e}")
            return text
    
    async def _generate_audio_streaming(self, text: str) -> AsyncGenerator[bytes, None]:
        """
        Генерация аудио по предложениям
        
        Args:
            text: Текст для генерации аудио
            
        Yields:
            Аудио чанки
        """
        try:
            if not self.audio_processor:
                logger.warning("⚠️ AudioProcessor не доступен, пропускаем генерацию аудио")
                return
            
            if not hasattr(self.audio_processor, 'generate_speech_streaming'):
                logger.warning("⚠️ AudioProcessor не имеет метода generate_speech_streaming")
                return
            
            logger.debug(f"Генерация аудио для текста: {text[:50]}...")
            
            # Разбиваем текст на предложения
            sentences = self._split_into_sentences(text)
            
            for sentence in sentences:
                if sentence.strip():
                    logger.debug(f"Генерация аудио для предложения: {sentence[:30]}...")
                    
                    # Генерируем аудио для каждого предложения
                    try:
                        async for audio_chunk in self.audio_processor.generate_speech_streaming(sentence):
                            yield audio_chunk
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка генерации аудио для предложения: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации аудио: {e}")
    
    def _split_into_sentences(self, text: str) -> list[str]:
        """
        Разбивка текста на предложения
        
        Args:
            text: Исходный текст
            
        Returns:
            Список предложений
        """
        try:
            # Простая разбивка по точкам, восклицательным и вопросительным знакам
            import re
            sentences = re.split(r'[.!?]+', text)
            
            # Очищаем от пустых строк и лишних пробелов
            clean_sentences = [s.strip() for s in sentences if s.strip()]
            
            logger.debug(f"Текст разбит на {len(clean_sentences)} предложений")
            return clean_sentences
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка разбивки текста: {e}")
            return [text]  # Возвращаем весь текст как одно предложение
    
    async def cleanup(self):
        """Очистка ресурсов"""
        try:
            logger.info("Очистка StreamingWorkflowIntegration...")
            self.is_initialized = False
            logger.info("✅ StreamingWorkflowIntegration очищен")
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки StreamingWorkflowIntegration: {e}")
