#!/usr/bin/env python3
"""
StreamingWorkflowIntegration - управляет потоком: текст → аудио → клиент
"""

import logging
import os
from typing import Dict, Any, AsyncGenerator, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class StreamingWorkflowIntegration:
    """
    Управляет потоком обработки: получение текста → обработка → генерация аудио → стриминг клиенту
    """
    
    def __init__(self, text_processor=None, audio_processor=None, memory_workflow=None, text_filter_manager=None):
        """
        Инициализация StreamingWorkflowIntegration
        
        Args:
            text_processor: Модуль обработки текста
            audio_processor: Модуль генерации аудио
            memory_workflow: Workflow интеграция для работы с памятью
            text_filter_manager: Менеджер фильтрации текста
        """
        self.text_processor = text_processor
        self.audio_processor = audio_processor
        self.memory_workflow = memory_workflow
        self.text_filter_manager = text_filter_manager
        self.is_initialized = False
        
        # Единая неблокирующая буферизация и критерии флашинга (для текста и TTS одновременно)
        self._stream_buffer: str = ""
        self._has_emitted: bool = False
        self._pending_segment: str = ""
        self._processed_sentences: set = set()  # Для дедупликации
        # Централизованные пороги (STREAM_*), с бэквард-фоллбеком на TTS_* (уменьшены для естественного воспроизведения)
        self.stream_min_chars: int = int(os.getenv("STREAM_MIN_CHARS", os.getenv("TTS_MIN_CHARS", "15")))
        self.stream_min_words: int = int(os.getenv("STREAM_MIN_WORDS", os.getenv("TTS_MIN_WORDS", "3")))
        self.stream_first_sentence_min_words: int = int(os.getenv("STREAM_FIRST_SENTENCE_MIN_WORDS", os.getenv("TTS_FIRST_SENTENCE_MIN_WORDS", "2")))
        self.stream_punct_flush_strict: bool = os.getenv("STREAM_PUNCT_FLUSH_STRICT", os.getenv("TTS_PUNCT_FLUSH_STRICT", "true")).lower() == "true"
        self.sentence_joiner: str = " "
        self.end_punctuations = ('.', '!', '?')
        
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
            
            if not self.text_filter_manager:
                logger.warning("⚠️ TextFilterManager не предоставлен")
            
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

            # Сбрасываем состояние перед новой сессией,
            # иначе остатки из предыдущей обработки вызывают дублирование чанков
            self._stream_buffer = ""
            self._pending_segment = ""
            self._has_emitted = False
            self._processed_sentences.clear()

            captured_segments: list[str] = []
            input_sentence_counter = 0
            emitted_segment_counter = 0
            total_audio_chunks = 0
            total_audio_bytes = 0
            sentence_audio_map: dict[int, int] = {}

            async for sentence in self._iter_processed_sentences(
                request_data.get('text', ''),
                request_data.get('screenshot'),
                memory_context
            ):
                input_sentence_counter += 1
                logger.info(f"📝 In sentence #{input_sentence_counter}: '{sentence[:120]}{'...' if len(sentence) > 120 else ''}' (len={len(sentence)})")

                # Единая буферизация: накапливаем, извлекаем завершенные предложения, агрегируем короткие
                sanitized = await self._sanitize_for_tts(sentence)
                if sanitized:
                    # Дедупликация только на уровне очищенного текста (более мягкая)
                    sanitized_hash = hash(sanitized.strip())
                    if sanitized_hash in self._processed_sentences:
                        logger.debug(f"🔄 Пропускаем дублированный очищенный текст: '{sanitized[:50]}...'")
                        continue
                    self._processed_sentences.add(sanitized_hash)
                    
                    self._stream_buffer = (f"{self._stream_buffer}{self.sentence_joiner}{sanitized}" if self._stream_buffer else sanitized)

                complete_sentences, remainder = await self._split_complete_sentences(self._stream_buffer)
                self._stream_buffer = remainder

                for complete in complete_sentences:
                    # Агрегируем короткие завершенные предложения до порогов
                    candidate = complete if not self._pending_segment else f"{self._pending_segment}{self.sentence_joiner}{complete}"
                    words_count = await self._count_meaningful_words(candidate)
                    if (not self._has_emitted and (words_count >= self.stream_first_sentence_min_words or len(candidate) >= self.stream_min_chars)) or \
                       (self._has_emitted and (words_count >= self.stream_min_words or len(candidate) >= self.stream_min_chars)):
                        # Дедупликация финальных сегментов (только для очень коротких повторений)
                        to_emit = candidate.strip()
                        if len(to_emit) > 10:  # Только для длинных текстов применяем дедупликацию
                            complete_hash = hash(to_emit)
                            if complete_hash in self._processed_sentences:
                                logger.debug(f"🔄 Пропускаем дублированный финальный сегмент: '{to_emit[:50]}...'")
                                continue
                            self._processed_sentences.add(complete_hash)
                        
                        # Готов к эмиссии
                        emitted_segment_counter += 1
                        self._pending_segment = ""
                        self._has_emitted = True

                        # Текст
                        captured_segments.append(to_emit)
                        yield {
                            'success': True,
                            'text_response': to_emit,
                            'sentence_index': emitted_segment_counter
                        }

                        # Аудио (гарантируем завершающую пунктуацию для TTS)
                        tts_text = to_emit if to_emit.endswith(self.end_punctuations) else f"{to_emit}."
                        sentence_audio_chunks = 0
                        async for audio_chunk in self._stream_audio_for_sentence(tts_text, emitted_segment_counter):
                            if not audio_chunk:
                                continue
                            sentence_audio_chunks += 1
                            total_audio_chunks += 1
                            total_audio_bytes += len(audio_chunk)
                            yield {
                                'success': True,
                                'audio_chunk': audio_chunk,
                                'sentence_index': emitted_segment_counter,
                                'audio_chunk_index': sentence_audio_chunks
                            }

                        sentence_audio_map[emitted_segment_counter] = sentence_audio_chunks
                        logger.info(
                            f"🎧 Segment #{emitted_segment_counter} → audio_chunks={sentence_audio_chunks}, total_audio_chunks={total_audio_chunks}, total_bytes={total_audio_bytes}"
                        )
                    else:
                        # Продолжаем копить
                        self._pending_segment = candidate

            # Финальный флаш: сначала обработаем завершенные предложения из буфера
            if self._stream_buffer:
                complete_sentences, remainder = await self._split_complete_sentences(self._stream_buffer)
                self._stream_buffer = remainder
                for complete in complete_sentences:
                    candidate = complete if not self._pending_segment else f"{self._pending_segment}{self.sentence_joiner}{complete}"
                    words_count = await self._count_meaningful_words(candidate)
                    if (not self._has_emitted and (words_count >= self.stream_first_sentence_min_words or len(candidate) >= self.stream_min_chars)) or \
                       (self._has_emitted and (words_count >= self.stream_min_words or len(candidate) >= self.stream_min_chars)):
                        emitted_segment_counter += 1
                        to_emit = candidate.strip()
                        self._pending_segment = ""
                        self._has_emitted = True
                        captured_segments.append(to_emit)
                        yield {'success': True, 'text_response': to_emit, 'sentence_index': emitted_segment_counter}
                        tts_text = to_emit if to_emit.endswith(self.end_punctuations) else f"{to_emit}."
                        sentence_audio_chunks = 0
                        async for audio_chunk in self._stream_audio_for_sentence(tts_text, emitted_segment_counter):
                            if not audio_chunk:
                                continue
                            sentence_audio_chunks += 1
                            total_audio_chunks += 1
                            total_audio_bytes += len(audio_chunk)
                            yield {'success': True, 'audio_chunk': audio_chunk, 'sentence_index': emitted_segment_counter, 'audio_chunk_index': sentence_audio_chunks}
                        sentence_audio_map[emitted_segment_counter] = sentence_audio_chunks
                        logger.info(f"🎧 Final segment #{emitted_segment_counter} → audio_chunks={sentence_audio_chunks}, total_audio_chunks={total_audio_chunks}, total_bytes={total_audio_bytes}")
                    else:
                        self._pending_segment = candidate

            # Если остался незавершенный агрегат, можно форс-флаш, если очень длинный
            force_max = int(os.getenv("STREAM_FORCE_FLUSH_MAX_CHARS", "0") or 0)
            if self._pending_segment and force_max > 0 and len(self._pending_segment) >= force_max:
                emitted_segment_counter += 1
                to_emit = self._pending_segment
                self._pending_segment = ""
                self._has_emitted = True
                captured_segments.append(to_emit)
                yield {'success': True, 'text_response': to_emit, 'sentence_index': emitted_segment_counter}
                tts_text = to_emit if to_emit.endswith(self.end_punctuations) else f"{to_emit}."
                sentence_audio_chunks = 0
                async for audio_chunk in self._stream_audio_for_sentence(tts_text, emitted_segment_counter):
                    if not audio_chunk:
                        continue
                    sentence_audio_chunks += 1
                    total_audio_chunks += 1
                    total_audio_bytes += len(audio_chunk)
                    yield {'success': True, 'audio_chunk': audio_chunk, 'sentence_index': emitted_segment_counter, 'audio_chunk_index': sentence_audio_chunks}
                sentence_audio_map[emitted_segment_counter] = sentence_audio_chunks
                logger.info(f"🎧 Forced final segment #{emitted_segment_counter} → audio_chunks={sentence_audio_chunks}, total_audio_chunks={total_audio_chunks}, total_bytes={total_audio_bytes}")

            full_text = " ".join(captured_segments).strip()

            logger.info(
                f"✅ Запрос обработан успешно: segments={emitted_segment_counter}, audio_chunks={total_audio_chunks}, total_bytes={total_audio_bytes}"
            )
            yield {
                'success': True,
                'text_full_response': full_text,
                'sentences_processed': emitted_segment_counter,
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

    async def _sanitize_for_tts(self, text: str) -> str:
        """
        Очистка текста для синтеза речи через модуль фильтрации
        """
        if not text:
            return ""

        if self.text_filter_manager:
            try:
                result = await self.text_filter_manager.clean_text(text, {
                    "remove_special_chars": True,
                    "remove_extra_whitespace": True,
                    "normalize_unicode": True,
                    "remove_control_chars": True
                })
                if result.get("success") and result.get("cleaned_text") is not None:
                    return result.get("cleaned_text", "").strip()
            except Exception as err:
                logger.warning("⚠️ Ошибка очистки текста через TextFilterManager: %s", err)

        return text.strip()

    async def _split_complete_sentences(self, text: str) -> tuple[list[str], str]:
        """
        Разбиение текста на предложения через модуль фильтрации
        """
        if not text:
            return [], ""

        if self.text_filter_manager:
            try:
                result = await self.text_filter_manager.split_sentences(text)
                if result.get("success"):
                    return result.get("sentences", []), result.get("remainder", "")
            except Exception as err:
                logger.warning("⚠️ Ошибка разбиения текста через TextFilterManager: %s", err)

        stripped = text.strip()
        return ([stripped] if stripped else [], "")

    async def _count_meaningful_words(self, text: str) -> int:
        """
        Подсчёт значимых слов через модуль фильтрации
        """
        if not text:
            return 0

        if self.text_filter_manager:
            try:
                return self.text_filter_manager.count_meaningful_words(text)
            except Exception as err:
                logger.warning("⚠️ Ошибка подсчёта слов через TextFilterManager: %s", err)

        return len([w for w in text.split() if w.strip()])

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
            logger.info(f"🔊 Генерация аудио для предложения #{sentence_index}: '{sentence[:80]}...'")
            chunk_count = 0
            async for audio_chunk in self.audio_processor.generate_speech_streaming(sentence):
                if audio_chunk:
                    chunk_count += 1
                    logger.info(f"🔊 Audio chunk #{chunk_count} для предложения #{sentence_index}: {len(audio_chunk)} bytes")
                    yield audio_chunk
            logger.info(f"✅ Аудио генерация завершена для предложения #{sentence_index}: {chunk_count} чанков")
        except Exception as audio_error:
            logger.error(f"❌ Ошибка генерации аудио для предложения #{sentence_index}: {audio_error}")
    
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
