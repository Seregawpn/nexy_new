#!/usr/bin/env python3
"""
StreamingWorkflowIntegration - управляет потоком: текст → аудио → клиент
"""

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
        """Потоковая обработка запроса: предложения и аудио стримятся параллельно."""
        if not self.is_initialized:
            logger.error("❌ StreamingWorkflowIntegration не инициализирован")
            yield {
                'success': False,
                'error': 'StreamingWorkflowIntegration not initialized',
                'text_response': '',
            }
            return

        session_id = request_data.get('session_id', 'unknown')
        try:
            logger.info(f"🔄 Начало обработки запроса: {session_id}")
            logger.info(f"→ Input text len={len(request_data.get('text','') or '')}, has_screenshot={bool(request_data.get('screenshot'))}")
            logger.info(f"→ Input text content: '{request_data.get('text', '')[:100]}...'")

            logger.info("🔍 ДИАГНОСТИКА МОДУЛЕЙ:")
            logger.info(f"   → text_processor: {self.text_processor is not None}")
            logger.info(f"   → audio_processor: {self.audio_processor is not None}")
            if self.text_processor:
                logger.info(f"   → text_processor.is_initialized: {getattr(self.text_processor, 'is_initialized', 'NO_ATTR')}")
            if self.audio_processor:
                logger.info(f"   → audio_processor.is_initialized: {getattr(self.audio_processor, 'is_initialized', 'NO_ATTR')}")

            hardware_id = request_data.get('hardware_id', 'unknown')
            memory_context = await self._get_memory_context_parallel(hardware_id)

            captured_sentences: list[str] = []
            sentence_counter = 0
            total_audio_chunks = 0
            total_audio_bytes = 0
            sentence_audio_map: dict[int, int] = {}

            async for sentence in self._iter_processed_sentences(
                request_data.get('text', ''),
                request_data.get('screenshot'),
                memory_context
            ):
                sentence_counter += 1
                sentence_audio_chunks = 0
                captured_sentences.append(sentence)

                logger.info(f"📝 Sentence #{sentence_counter}: '{sentence[:120]}{'...' if len(sentence) > 120 else ''}'")
                yield {
                    'success': True,
                    'text_response': sentence,
                    'sentence_index': sentence_counter
                }

                async for audio_chunk in self._stream_audio_for_sentence(sentence, sentence_counter):
                    if not audio_chunk:
                        continue
                    sentence_audio_chunks += 1
                    total_audio_chunks += 1
                    total_audio_bytes += len(audio_chunk)
                    yield {
                        'success': True,
                        'audio_chunk': audio_chunk,
                        'sentence_index': sentence_counter,
                        'audio_chunk_index': sentence_audio_chunks
                    }

                sentence_audio_map[sentence_counter] = sentence_audio_chunks
                logger.info(
                    f"🎧 Sentence #{sentence_counter} → audio_chunks={sentence_audio_chunks}, total_audio_chunks={total_audio_chunks}, total_bytes={total_audio_bytes}"
                )

            full_text = " ".join(captured_sentences).strip()
            logger.info(
                f"✅ Запрос обработан успешно: sentences={sentence_counter}, audio_chunks={total_audio_chunks}, total_bytes={total_audio_bytes}"
            )
            yield {
                'success': True,
                'text_full_response': full_text,
                'sentences_processed': sentence_counter,
                'audio_chunks_processed': total_audio_chunks,
                'audio_bytes_processed': total_audio_bytes,
                'sentence_audio_map': sentence_audio_map,
                'is_final': True
            }

        except Exception as e:
            logger.error(f"❌ Ошибка обработки запроса {session_id}: {e}")
            yield {
                'success': False,
                'error': str(e),
                'text_response': '',
            }

    async def _get_memory_context_parallel(self, hardware_id: str) -> Optional[Dict[str, Any]]:
        """
        Неблокирующее получение контекста памяти
        
        Args:
            hardware_id: Идентификатор оборудования
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

    async def _iter_processed_sentences(
        self,
        text: str,
        screenshot: Optional[str],
        memory_context: Optional[Dict[str, Any]]
    ) -> AsyncGenerator[str, None]:
        """Стримингово возвращает предложения с учётом памяти и скриншота."""
        enriched_text = self._enrich_with_memory(text, memory_context)

        screenshot_data: Optional[bytes] = None
        if screenshot:
            import base64
            try:
                screenshot_data = base64.b64decode(screenshot)
                logger.info(f"📸 Скриншот декодирован: {len(screenshot_data)} bytes")
            except Exception as decode_error:
                logger.warning(f"⚠️ Не удалось декодировать скриншот: {decode_error}")
                screenshot_data = None

        yielded_any = False
        if self.text_processor and hasattr(self.text_processor, 'process_text_streaming'):
            logger.info(f"🔄 Стриминг текста через TextProcessor: '{enriched_text[:80]}...'")
            try:
                async for processed_sentence in self.text_processor.process_text_streaming(enriched_text, screenshot_data):
                    sentence = (processed_sentence or '').strip()
                    if sentence:
                        yielded_any = True
                        logger.debug(f"📨 TextProcessor sentence: '{sentence[:120]}...'")
                        yield sentence
            except Exception as processing_error:
                logger.warning(f"⚠️ Ошибка TextProcessor: {processing_error}. Используем fallback")

        if not yielded_any:
            logger.debug("⚠️ TextProcessor не вернул предложений, используем fallback разбивку")
            for fallback_sentence in self._split_into_sentences(enriched_text):
                if fallback_sentence:
                    yield fallback_sentence

    def _enrich_with_memory(self, text: str, memory_context: Optional[Dict[str, Any]]) -> str:
        """
        Объединение текста с контекстом памяти
        
        Args:
            text: Исходный текст
            memory_context: Контекст памяти
        """
        if not memory_context:
            return text
        
        try:
            memory_info = memory_context.get('recent_context', '') if memory_context else ''
            if memory_info:
                enriched_text = f"Контекст: {memory_info}\n\n{text}"
                logger.debug("Текст обогащен контекстом памяти")
                return enriched_text
            return text
        except Exception as e:
            logger.warning(f"⚠️ Ошибка обогащения текста памятью: {e}")
            return text

    async def _stream_audio_for_sentence(self, sentence: str, sentence_index: int) -> AsyncGenerator[bytes, None]:
        """Стримит аудио чанки для одного предложения."""
        if not sentence.strip():
            return
        if not self.audio_processor:
            logger.warning("⚠️ AudioProcessor недоступен, пропускаем генерацию аудио")
            return
        if not hasattr(self.audio_processor, 'generate_speech_streaming'):
            logger.warning("⚠️ AudioProcessor не поддерживает generate_speech_streaming")
            return
        if hasattr(self.audio_processor, 'is_initialized') and not self.audio_processor.is_initialized:
            logger.warning("⚠️ AudioProcessor не инициализирован")
            return

        try:
            logger.debug(f"🔊 Генерация аудио для предложения #{sentence_index}: '{sentence[:80]}...'")
            async for audio_chunk in self.audio_processor.generate_speech_streaming(sentence):
                if audio_chunk:
                    yield audio_chunk
        except Exception as audio_error:
            logger.warning(f"⚠️ Ошибка генерации аудио для предложения #{sentence_index}: {audio_error}")
    
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
