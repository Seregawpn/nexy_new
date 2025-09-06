import asyncio
import logging
import grpc.aio              
from concurrent.futures import ThreadPoolExecutor
import sys                     
import os
import numpy as np
from datetime import datetime

# Добавляем корневую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Protobuf файлы генерируются автоматически из streaming.proto
import streaming_pb2
import streaming_pb2_grpc
from config import Config
from text_processor import TextProcessor
from audio_generator import AudioGenerator
from database.database_manager import DatabaseManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_dtype_string(dtype) -> str:
    """Правильно преобразует numpy dtype в строку для protobuf"""
    if hasattr(dtype, 'name'):
        return dtype.name  # np.int16 -> 'int16'
    dtype_str = str(dtype)
    if dtype_str == '<i2':
        return 'int16'
    elif dtype_str == '<f4':
        return 'float32'
    elif dtype_str == '<f8':
        return 'float64'
    return dtype_str

class StreamingServicer(streaming_pb2_grpc.StreamingServiceServicer):
    """gRPC сервис для стриминга аудио и текста (АСИНХРОННАЯ ВЕРСИЯ)"""
    
    def __init__(self):
        self.text_processor = TextProcessor()
        self.audio_generator = AudioGenerator()
        
        # КРИТИЧНО: добавляем отслеживание активных сессий для прерывания
        self.active_sessions = {}  # {session_id: {'task': task, 'cancelled': False}}
        self.session_counter = 0
        
        # КРИТИЧНО: ГЛОБАЛЬНЫЙ флаг прерывания для МГНОВЕННОЙ отмены
        self.global_interrupt_flag = False
        self.interrupt_hardware_id = None
        
        # Инициализируем менеджер базы данных
        try:
            db_url = Config.get_database_url()
            self.db_manager = DatabaseManager(db_url)
            if self.db_manager.connect():
                logger.info("✅ База данных подключена успешно")
                # Устанавливаем DatabaseManager в TextProcessor для работы с памятью
                self.text_processor.set_database_manager(self.db_manager)
                logger.info("✅ DatabaseManager установлен в TextProcessor")
            else:
                logger.warning("⚠️ Не удалось подключиться к базе данных")
                self.db_manager = None
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации базы данных: {e}")
            self.db_manager = None

    async def StreamAudio(self, request, context):
        """
        АСИНХРОННЫЙ стриминг аудио и текста в ответ на промпт.
        Использует async for для обработки потоков текста и аудио.
        """
        stream_start_time = asyncio.get_event_loop().time()
        logger.info(f"🚨 StreamAudio() начат в {stream_start_time:.3f}")
        
        prompt = request.prompt
        screenshot_base64 = request.screenshot if request.HasField('screenshot') else None
        screen_width = request.screen_width if request.HasField('screen_width') else 0
        screen_height = request.screen_height if request.HasField('screen_height') else 0
        hardware_id = request.hardware_id
        
        logger.info(f"   📝 Промпт: {prompt[:100]}...")
        logger.info(f"   🆔 Hardware ID: {hardware_id[:20] if hardware_id else 'None'}...")
        logger.info(f"   📸 Скриншот: {'Да' if screenshot_base64 else 'Нет'}")
        
        # 🔹 Спец-режим: приветствие при запуске (минуем LLM/БД, сразу TTS)
        if isinstance(prompt, str) and prompt.startswith("__GREETING__:"):
            greeting_text = prompt.split(":", 1)[1].strip()
            logger.info(f"🎬 Режим приветствия. Текст: {greeting_text[:100]}...")
            try:
                audio_chunk_complete = await self.audio_generator.generate_audio(greeting_text)
                if audio_chunk_complete is not None and len(audio_chunk_complete) > 0:
                    yield streaming_pb2.StreamResponse(
                        audio_chunk=streaming_pb2.AudioChunk(
                            audio_data=audio_chunk_complete.tobytes(),
                            dtype=_get_dtype_string(audio_chunk_complete.dtype),
                            shape=list(audio_chunk_complete.shape)
                        )
                    )
                yield streaming_pb2.StreamResponse(end_message="greeting_done")
            except Exception as e:
                logger.error(f"❌ Ошибка генерации приветствия: {e}")
                yield streaming_pb2.StreamResponse(error_message=f"Ошибка приветствия: {e}")
            return
        
        # КРИТИЧНО: создаем уникальный ID сессии для отслеживания
        session_id = f"session_{self.session_counter}_{hardware_id[:8] if hardware_id else 'unknown'}"
        self.session_counter += 1
        
        # КРИТИЧНО: сбрасываем глобальный флаг прерывания для новой сессии
        if self.interrupt_hardware_id == hardware_id:
            self.global_interrupt_flag = False
            self.interrupt_hardware_id = None
            logger.info(f"🔄 Глобальный флаг прерывания сброшен для новой сессии {hardware_id}")
        
        logger.info(f"🚀 НОВАЯ СЕССИЯ {session_id}: {prompt}")
        logger.info(f"Hardware ID: {hardware_id}")
        
        if screenshot_base64:
            logger.info(f"Получен скриншот: {screen_width}x{screen_height} пикселей, {len(screenshot_base64)} символов Base64")
        else:
            logger.info("Скриншот не предоставлен")
        
        try:
            # КРИТИЧНО: регистрируем сессию как активную
            self.active_sessions[session_id] = {'cancelled': False, 'start_time': asyncio.get_event_loop().time()}
            logger.info(f"✅ Сессия {session_id} зарегистрирована как активная")
            
            # Асинхронная обработка БД (запускаем как фоновую задачу)
            if hardware_id and self.db_manager:
                screen_info_for_db = {'width': screen_width, 'height': screen_height} if screen_width > 0 else {}
                asyncio.create_task(self._process_hardware_id(hardware_id, prompt, screenshot_base64, screen_info_for_db))
            
            logger.info(f"🚀 Запускаю Gemini Live API streaming для сессии {session_id}...")
            
            screen_info = {'width': screen_width, 'height': screen_height} if screen_width > 0 else {}
            
            # Получаем асинхронный генератор текста с передачей hardware_id для памяти
            text_generator = self.text_processor.generate_response_stream(
                prompt=prompt, 
                hardware_id=hardware_id,
                screenshot_base64=screenshot_base64,
                # КРИТИЧНО: передаем доступ к глобальному флагу прерывания
                interrupt_checker=lambda: (self.global_interrupt_flag and self.interrupt_hardware_id == hardware_id)
            )
            
            # Стримим текст и для каждого куска стримим аудио
            iteration_count = 0
            logger.info(f"   🔄 Начинаю цикл обработки текста для сессии {session_id}")
            
            async for text_chunk in text_generator:
                iteration_count += 1
                chunk_time = asyncio.get_event_loop().time()
                logger.info(f"   📦 Обрабатываю текстовый чанк {iteration_count} в {chunk_time:.3f}")
                
                # КРИТИЧНО: ПЕРВЫЙ ПРИОРИТЕТ - проверка глобального флага прерывания
                if self.global_interrupt_flag and self.interrupt_hardware_id == hardware_id:
                    logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН для {hardware_id} - МГНОВЕННО ПРЕРЫВАЮ ГЕНЕРАЦИЮ ТЕКСТА!")
                    logger.info(f"   🚫 Прерывание на чанке {iteration_count} - выход из цикла текста")
                    break
                
                # КРИТИЧНО: проверяем прерывание ПЕРЕД генерацией текста
                if session_id in self.active_sessions and self.active_sessions[session_id]['cancelled']:
                    logger.warning(f"🚨 Сессия {session_id} ОТМЕНЕНА - прерываю генерацию текста!")
                    break
                
                # КРИТИЧНО: проверяем gRPC контекст на отмену
                try:
                    if hasattr(context, 'cancelled') and context.cancelled():
                        logger.warning(f"🚨 gRPC задача ОТМЕНЕНА в цикле генерации текста для сессии {session_id}!")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки gRPC отмены в цикле текста: {e}")
                    pass
                
                # КРИТИЧНО: ПЕРВЫЙ ПРИОРИТЕТ - проверка глобального флага прерывания
                if self.global_interrupt_flag and self.interrupt_hardware_id == hardware_id:
                    logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН для {hardware_id} - МГНОВЕННО ПРЕРЫВАЮ ВСЕ!")
                    break
                
                # КРИТИЧНО: ДОПОЛНИТЕЛЬНАЯ проверка прерывания в КАЖДОЙ итерации
                if iteration_count % 1 == 0:  # Проверяем КАЖДУЮ итерацию!
                    if self.global_interrupt_flag and self.interrupt_hardware_id == hardware_id:
                        logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН для {hardware_id} - МГНОВЕННО ПРЕРЫВАЮ ВСЕ!")
                        break
                
                # КРИТИЧНО: проверяем, не была ли сессия отменена
                if session_id in self.active_sessions and self.active_sessions[session_id]['cancelled']:
                    logger.warning(f"🚨 Сессия {session_id} ОТМЕНЕНА - прерываю стриминг!")
                    break
                
                # КРИТИЧНО: проверяем состояние gRPC соединения
                try:
                    # Проверяем cancel (задача отменена) - правильная проверка
                    if hasattr(context, 'cancelled') and context.cancelled():
                        logger.warning(f"🚨 gRPC задача ОТМЕНЕНА для сессии {session_id}!")
                        break
                        
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки состояния gRPC: {e}")
                    pass
                
                # КРИТИЧНО: ПЕРИОДИЧЕСКАЯ проверка прерывания каждые 3 итерации
                if iteration_count % 3 == 0:
                    logger.info(f"🔍 Периодическая проверка прерывания: итерация {iteration_count}")
                    if session_id in self.active_sessions and self.active_sessions[session_id]['cancelled']:
                        logger.warning(f"🚨 Сессия {session_id} ОТМЕНЕНА на периодической проверке!")
                        break
                
                # КРИТИЧНО: проверяем время жизни сессии (защита от зависания)
                current_time = asyncio.get_event_loop().time()
                session_start_time = self.active_sessions[session_id]['start_time']
                if current_time - session_start_time > 30.0:  # 30 секунд максимум
                    logger.warning(f"🚨 Сессия {session_id} превысила лимит времени (30s) - принудительно завершаю!")
                    break
                
                if text_chunk and text_chunk.strip():
                    # КРИТИЧНО: ПЕРВЫЙ ПРИОРИТЕТ - проверка глобального флага прерывания
                    if self.global_interrupt_flag and self.interrupt_hardware_id == hardware_id:
                        logger.warning(f"🚨 ГЛОБАЛЬНЫЙ ФЛАГ ПРЕРЫВАНИЯ АКТИВЕН для {hardware_id} - МГНОВЕННО ПРЕРЫВАЮ ГЕНЕРАЦИЮ АУДИО!")
                        break
                    
                    # КРИТИЧНО: проверяем прерывание ПЕРЕД генерацией аудио
                    if session_id in self.active_sessions and self.active_sessions[session_id]['cancelled']:
                        logger.warning(f"🚨 Сессия {session_id} ОТМЕНЕНА - прерываю генерацию аудио!")
                        break
                    
                    # 1. Отправляем текстовый чанк клиенту (очищаем маркер LangChain)
                    clean_text_chunk = text_chunk
                    if text_chunk.startswith("__LANGCHAIN_TEXT_ONLY__:"):
                        clean_text_chunk = text_chunk.replace("__LANGCHAIN_TEXT_ONLY__:", "", 1)
                    
                    yield streaming_pb2.StreamResponse(text_chunk=clean_text_chunk)
                    
                    # 2. 🚀 ПОТОКОВАЯ генерация аудио для этого предложения
                    # 🔄 ПРОВЕРЯЕМ: если это LangChain fallback (TEXT_ONLY), пропускаем генерацию аудио
                    if text_chunk.startswith("__LANGCHAIN_TEXT_ONLY__:"):
                        logger.info(f"   🔄 [GRPC_SERVER] LangChain fallback detected - пропускаю генерацию аудио для чанка {iteration_count}")
                        # Отправляем пустой аудио чанк для завершения
                        yield streaming_pb2.StreamResponse(audio_chunk=streaming_pb2.AudioChunk(
                            audio_data=b"",
                            dtype="int16",
                            shape=[0]
                        ))
                        continue
                    
                    try:
                        logger.info(f"   🎵 Начинаю ПОТОКОВУЮ генерацию аудио для чанка {iteration_count}...")
                        audio_start_time = asyncio.get_event_loop().time()
                        
                        # Используем новый потоковый метод
                        audio_chunk_count = 0
                        async for audio_chunk in self.audio_generator.generate_streaming_audio(text_chunk):
                            audio_chunk_count += 1
                            logger.info(f"   🎵 [GRPC_SERVER] Получен аудио чанк {audio_chunk_count} от генератора: {len(audio_chunk) if audio_chunk is not None else 'None'} сэмплов")
                            
                            # Проверяем прерывание перед отправкой каждого аудио чанка
                            if self.global_interrupt_flag and self.interrupt_hardware_id == hardware_id:
                                logger.warning(f"🚨 [GRPC_SERVER] ПРЕРЫВАНИЕ АКТИВНО для {hardware_id} - прерываю потоковую генерацию аудио!")
                                break
                            
                            if session_id in self.active_sessions and self.active_sessions[session_id]['cancelled']:
                                logger.warning(f"🚨 [GRPC_SERVER] Сессия {session_id} ОТМЕНЕНА - прерываю потоковую генерацию аудио!")
                                break
                            
                            # КРИТИЧНО: Проверяем, что аудио чанк не пустой перед отправкой
                            if audio_chunk is not None and len(audio_chunk) > 0:
                                logger.info(f"   🎵 [GRPC_SERVER] Отправляю аудио чанк {audio_chunk_count} клиенту: {len(audio_chunk)} сэмплов")
                                # Отправляем аудио чанк клиенту
                                yield streaming_pb2.StreamResponse(
                                    audio_chunk=streaming_pb2.AudioChunk(
                                        audio_data=audio_chunk.tobytes(),
                                        dtype=_get_dtype_string(audio_chunk.dtype),
                                        shape=list(audio_chunk.shape)
                                    )
                                )
                                logger.info(f"   ✅ [GRPC_SERVER] Аудио чанк {audio_chunk_count} отправлен успешно")
                            else:
                                logger.debug(f"   🔇 [GRPC_SERVER] Пропускаю пустой аудио чанк {audio_chunk_count}")
                        
                        logger.info(f"   🎵 [GRPC_SERVER] Потоковая генерация завершена: {audio_chunk_count} чанков обработано")
                        
                        audio_gen_time = (asyncio.get_event_loop().time() - audio_start_time) * 1000
                        logger.info(f"   ⏱️ Потоковая генерация аудио завершена: {audio_gen_time:.1f}ms")
                        
                    except Exception as audio_error:
                        logger.error(f"Ошибка потоковой генерации аудио для '{text_chunk[:30]}...': {audio_error}")

            stream_end_time = asyncio.get_event_loop().time()
            total_stream_time = stream_end_time - stream_start_time
            logger.info(f"✅ Gemini Live API streaming завершен для сессии {session_id}")
            logger.info(f"   ⏱️ Общее время стрима: {total_stream_time:.1f}s")
            logger.info(f"   📊 Обработано чанков: {iteration_count}")
                
        except Exception as e:
            logger.error(f"❌ Произошла ошибка в StreamAudio для сессии {session_id}: {e}", exc_info=True)
            yield streaming_pb2.StreamResponse(
                error_message=f"Произошла внутренняя ошибка: {e}"
            )
        finally:
            # КРИТИЧНО: НЕ очищаем сессию сразу - даем время для InterruptSession RPC
            # Вместо этого запускаем отложенную очистку
            try:
                if session_id in self.active_sessions:
                    # КРИТИЧНО: НЕ планируем автоматическую очистку!
                    # Сессия будет очищена ТОЛЬКО после получения команды прерывания
                    # или по таймауту (30 секунд) для предотвращения утечек памяти
                    logger.info(f"⏰ Сессия {session_id} оставлена активной для команд прерывания")
                    
                    # КРИТИЧНО: запускаем задачу автоматической очистки старых сессий
                    asyncio.create_task(self._auto_cleanup_old_sessions())
                    
                    # КРИТИЧНО: сбрасываем глобальный флаг прерывания для данной сессии
                    if self.interrupt_hardware_id == hardware_id:
                        self.global_interrupt_flag = False
                        self.interrupt_hardware_id = None
                        logger.info(f"🔄 Глобальный флаг прерывания сброшен для {hardware_id}")
                        
            except Exception as cleanup_error:
                logger.error(f"❌ Ошибка планирования очистки сессии {session_id}: {cleanup_error}")
                # В случае ошибки очищаем немедленно
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                    logger.info(f"🧹 Сессия {session_id} очищена немедленно (fallback)")
    
    def InterruptSession(self, request, context):
        """
        ПРИНУДИТЕЛЬНОЕ прерывание активной сессии на сервере!
        МГНОВЕННАЯ отмена всех процессов генерации!
        """
        import time
        interrupt_start_time = time.time()
        hardware_id = request.hardware_id
        
        logger.warning(f"🚨 InterruptSession() вызван в {interrupt_start_time:.3f}")
        logger.warning(f"🚨 ЗАПРОС НА ПРИНУДИТЕЛЬНОЕ ПРЕРЫВАНИЕ для Hardware ID: {hardware_id}")
        
        # Логируем состояние ДО прерывания
        active_sessions_count = len(self.active_sessions)
        global_flag_before = self.global_interrupt_flag
        interrupt_hw_before = self.interrupt_hardware_id
        logger.info(f"   📊 Состояние ДО: active_sessions={active_sessions_count}, global_flag={global_flag_before}, interrupt_hw={interrupt_hw_before}")
        
        # КРИТИЧНО: Устанавливаем ГЛОБАЛЬНЫЙ флаг прерывания
        flag_start_time = time.time()
        self.global_interrupt_flag = True
        self.interrupt_hardware_id = hardware_id
        flag_time = (time.time() - flag_start_time) * 1000
        logger.warning(f"🚨 ГЛОБАЛЬНЫЙ флаг прерывания УСТАНОВЛЕН для {hardware_id} за {flag_time:.1f}ms")
        
        # КРИТИЧНО: МГНОВЕННО отменяем все процессы генерации
        try:
            # 1️⃣ Отменяем генерацию LLM ВСЕГДА
            if hasattr(self.text_processor, 'cancel_generation'):
                self.text_processor.cancel_generation()
                logger.warning(f"🚨 Генерация LLM МГНОВЕННО ОТМЕНЕНА для {hardware_id}!")
            
            # 2️⃣ Отменяем генерацию аудио ВСЕГДА
            if hasattr(self.audio_generator, 'stop_generation'):
                self.audio_generator.stop_generation()
                logger.warning(f"🚨 Генерация аудио МГНОВЕННО ОТМЕНЕНА для {hardware_id}!")
            
            if hasattr(self.text_processor, 'clear_buffers'):
                self.text_processor.clear_buffers()
                logger.warning(f"🚨 Буферы LLM МГНОВЕННО ОЧИЩЕНЫ для {hardware_id}!")
                
        except Exception as e:
            logger.error(f"❌ Ошибка отмены процессов генерации: {e}")
        
        # ПРОСТОЙ СБРОС ВСЕГО - не важно найдены сессии или нет!
        logger.warning(f"🚨 ПРОСТОЙ СБРОС ВСЕГО для {hardware_id} - не важно есть ли активные сессии!")
        
        # КРИТИЧНО: ВСЕГДА очищаем все буферы и процессы
        try:
            # Очищаем буферы аудио генератора ВСЕГДА
            if hasattr(self.audio_generator, 'stop_generation'):
                self.audio_generator.stop_generation()
                logger.warning(f"🚨 Генерация аудио ОСТАНОВЛЕНА для {hardware_id}!")
            
            # Очищаем буферы текстового процессора ВСЕГДА
            if hasattr(self.text_processor, 'clear_buffers'):
                self.text_processor.clear_buffers()
                logger.warning(f"🚨 Буферы LLM МГНОВЕННО ОЧИЩЕНЫ для {hardware_id}!")
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки буферов: {e}")
        
        # КРИТИЧНО: ВСЕГДА возвращаем успех - сброс выполнен!
        interrupt_end_time = time.time()
        total_interrupt_time = (interrupt_end_time - interrupt_start_time) * 1000
        
        # Логируем состояние ПОСЛЕ прерывания
        active_sessions_after = len(self.active_sessions)
        global_flag_after = self.global_interrupt_flag
        interrupt_hw_after = self.interrupt_hardware_id
        logger.info(f"   📊 Состояние ПОСЛЕ: active_sessions={active_sessions_after}, global_flag={global_flag_after}, interrupt_hw={interrupt_hw_after}")
        logger.warning(f"   ⏱️ Общее время прерывания: {total_interrupt_time:.1f}ms")
        
        logger.warning(f"✅ ПРОСТОЙ СБРОС ВСЕГО завершен для {hardware_id}!")
        return streaming_pb2.InterruptResponse(
            success=True,
            interrupted_sessions=[],  # Пустой список - это нормально!
            message="ПРОСТОЙ СБРОС ВСЕГО выполнен - все процессы остановлены"
        )
    
    async def _delayed_cleanup_session(self, session_id, delay=1.0):
        """
        Отложенная очистка сессии - дает время для InterruptSession RPC
        МГНОВЕННАЯ отмена всех процессов и очистка чанков
        """
        try:
            await asyncio.sleep(delay)
            if session_id in self.active_sessions:
                # КРИТИЧНО: МГНОВЕННО отменяем все процессы для данной сессии
                session_info = self.active_sessions[session_id]
                if 'task' in session_info and session_info['task']:
                    try:
                        session_info['task'].cancel()
                        logger.warning(f"🚨 Задача {session_id} МГНОВЕННО ОТМЕНЕНА!")
                    except:
                        pass
                
                # КРИТИЧНО: очищаем все чанки и буферы
                try:
                    # Очищаем буферы аудио генератора ТОЛЬКО если аудио уже генерировалось
                    if hasattr(self.audio_generator, 'is_busy'):
                        if self.audio_generator.is_busy():
                            self.audio_generator.stop_generation()
                            logger.warning(f"🚨 Генерация аудио ОСТАНОВЛЕНА для {session_id}!")
                        else:
                            logger.info(f"ℹ️ Аудио не генерировалось для {session_id} - пропускаем очистку буферов")
                except:
                    pass
                
                # Удаляем сессию
                del self.active_sessions[session_id]
                logger.info(f"🧹 Сессия {session_id} очищена после отложенной очистки")
            else:
                logger.info(f"ℹ️ Сессия {session_id} уже очищена")
        except Exception as e:
            logger.error(f"❌ Ошибка отложенной очистки сессии {session_id}: {e}")
            # В случае ошибки пробуем очистить немедленно
            try:
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]
                    logger.info(f"🧹 Сессия {session_id} очищена немедленно (fallback)")
            except:
                pass
    
    async def _auto_cleanup_old_sessions(self):
        """
        Автоматически очищает старые сессии по таймауту для предотвращения утечек памяти.
        Запускается в фоне для каждой новой сессии.
        """
        try:
            # Ждем 30 секунд для проверки старых сессий
            await asyncio.sleep(30.0)
            
            current_time = asyncio.get_event_loop().time()
            sessions_to_cleanup = []
            
            # Проверяем все активные сессии
            for session_id, session_info in list(self.active_sessions.items()):
                if 'start_time' in session_info:
                    session_age = current_time - session_info['start_time']
                    if session_age > 30.0:  # 30 секунд максимум
                        sessions_to_cleanup.append(session_id)
                        logger.warning(f"🚨 Сессия {session_id} превысила лимит времени ({session_age:.1f}s) - планирую очистку")
            
            # Очищаем старые сессии
            for session_id in sessions_to_cleanup:
                try:
                    if session_id in self.active_sessions:
                        del self.active_sessions[session_id]
                        logger.info(f"🧹 Старая сессия {session_id} автоматически очищена")
                except Exception as e:
                    logger.error(f"❌ Ошибка автоматической очистки сессии {session_id}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Ошибка автоматической очистки старых сессий: {e}")
    
    async def _process_hardware_id(self, hardware_id: str, prompt: str, screenshot_base64: str = None, screen_info: dict = None):
        """Асинхронная обработка информации в базе данных."""
        if not self.db_manager:
            logger.warning("⚠️ База данных недоступна для обработки Hardware ID")
            return
        
        try:
            # Запускаем синхронную операцию в executor'е
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._process_hardware_id_sync, hardware_id, prompt, screenshot_base64, screen_info)
        except Exception as e:
            logger.error(f"❌ Ошибка обработки hardware_id: {e}")
    
    def _process_hardware_id_sync(self, hardware_id: str, prompt: str, screenshot_base64: str = None, screen_info: dict = None):
        """Синхронный код для работы с БД, который будет выполняться в ThreadPoolExecutor."""
        try:
            logger.info(f"🆔 Обработка Hardware ID в потоке: {hardware_id[:16]}...")
            
            # 1. Создаем или получаем пользователя
            user = self.db_manager.get_user_by_hardware_id(hardware_id)
            if not user:
                logger.info(f"🆔 Пользователь не найден, создаю нового...")
                user_id = self.db_manager.create_user(hardware_id, {"created_via": "gRPC"})
                if not user_id:
                    logger.error(f"❌ Не удалось создать пользователя для {hardware_id}")
                    return
                logger.info(f"✅ Создан новый пользователь: {user_id}")
            else:
                user_id = user['id']
                logger.info(f"✅ Найден существующий пользователь: {user_id}")

            # 2. Создаем сессию
            if not user_id:
                logger.error(f"❌ user_id = None! Пропускаю создание сессии")
                return
                
            logger.info(f"🆔 Создаю сессию для пользователя: {user_id}")
            session_id = self.db_manager.create_session(user_id, {"prompt": prompt})
            if not session_id:
                logger.error(f"❌ Не удалось создать сессию для пользователя: {user_id}")
                return
            logger.info(f"✅ Создана сессия: {session_id}")

            # 3. Создаем команду
            if not session_id:
                logger.error(f"❌ session_id = None! Пропускаю создание команды")
                return
                
            logger.info(f"🆔 Создаю команду для сессии: {session_id}")
            command_metadata = {"has_screenshot": bool(screenshot_base64)}
            if screen_info:
                command_metadata['screen_info'] = screen_info
                
            command_id = self.db_manager.create_command(session_id, prompt, command_metadata)
            if not command_id:
                logger.error(f"❌ Не удалось создать команду для сессии: {session_id}")
                return
            logger.info(f"✅ Команда создана: {command_id}")

            # 4. Создаем скриншот (если есть)
            if screenshot_base64 and session_id:
                logger.info(f"🆔 Создаю скриншот для сессии: {session_id}")
                import json
                screenshot_metadata = {
                    "base64_length": len(screenshot_base64),
                    "format": "webp_base64"
                }
                if screen_info:
                    screenshot_metadata["screen_resolution"] = f"{screen_info.get('width', 0)}x{screen_info.get('height', 0)}"
                
                screenshot_id = self.db_manager.create_screenshot(
                    session_id, 
                    f"/tmp/screenshot_{session_id}.webp", 
                    None,  # file_url = None
                    screenshot_metadata  # metadata как dict
                )
                if screenshot_id:
                    logger.info(f"✅ Скриншот создан: {screenshot_id}")
                else:
                    logger.error(f"❌ Не удалось создать скриншот для сессии: {session_id}")

        except Exception as e:
            logger.error(f"❌ Ошибка в потоке обработки Hardware ID: {e}", exc_info=True)


async def serve():
    """Запуск асинхронного gRPC сервера"""
    
    # Настройки для больших сообщений (аудио + скриншоты)
    options = [
        ('grpc.max_send_message_length', 50 * 1024 * 1024),  # 50MB
        ('grpc.max_receive_message_length', 50 * 1024 * 1024),  # 50MB
        ('grpc.max_metadata_size', 1024 * 1024),  # 1MB для метаданных
    ]
    
    server = grpc.aio.server(options=options)
    streaming_pb2_grpc.add_StreamingServiceServicer_to_server(StreamingServicer(), server)
    
    server_address = f"{Config.GRPC_HOST}:{Config.GRPC_PORT}"
    server.add_insecure_port(server_address)
    
    logger.info(f"Асинхронный gRPC сервер запускается на {server_address}")
    logger.info(f"📏 Максимальный размер сообщения: 50MB")
    await server.start()
    logger.info("Сервер запущен. Нажмите Ctrl+C для остановки.")
    
    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки, останавливаю сервер...")
        await server.stop(0)
    finally:
        logger.info("Сервер остановлен.")

if __name__ == "__main__":
    # Проверяем конфигурацию перед запуском
    if not Config.validate():
        logger.error("❌ Конфигурация некорректна. Сервер не будет запущен.")
        sys.exit(1)
    
    asyncio.run(serve())
