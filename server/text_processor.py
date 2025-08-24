import asyncio
import logging
import os
import re
from typing import AsyncGenerator, List

# 🚨 ЗАМЕНА: Gemini Live API → LangChain + Google Gemini
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    LANGCHAIN_AVAILABLE = False

# --- Загрузка конфигурации ---
# Проверка наличия необходимых ключей API
if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY not found. Check config.env")

logger = logging.getLogger(__name__)

# Логируем статус импорта LangChain
if LANGCHAIN_AVAILABLE:
    logger.info("✅ LangChain + Google Gemini imported successfully")
else:
    logger.warning(f"⚠️ LangChain unavailable: {e}")

class TextProcessor:
    """
    Обрабатывает текстовые запросы с использованием Google Gemini через LangChain,
    который может использовать инструменты (например, Google Search)
    и поддерживает стриминг финального ответа.
    
    🚨 ВАЖНО: System Prompt теперь правильно передается в конфигурации сессии,
    а не как обычное сообщение. Это обеспечивает корректное поведение ассистента.
    """
    
    def __init__(self):
        # Инициализируем компоненты памяти
        self.memory_analyzer = None
        self.db_manager = None
        
        # ✅ МАКСИМАЛЬНО ПРОСТОЙ System Prompt (только то, что работает)
        self.base_system_instruction = (
            "You are a helpful assistant for blind and visually impaired users. "
            "Answer on question, exactly what user wants to know or get. Don't mix  answers of conversations or describe screenshot.\n"
   
            
            "🎯 YOUR CAPABILITIES:\n\n"
            
            "💬 BASIC CONVERSATION - for:\n"
            "- General questions and explanations\n"
            "- How things work\n"
            "- Definitions and concepts\n"
            "- Historical facts\n"
            "- Scientific explanations\n"
            "- Simple advice and help\n\n"
            
            "📱 SCREEN ANALYSIS - if screenshot available:\n"
            "- Use screenshot ONLY as visual context for your response\n"
            "- DO NOT return JSON coordinates or technical image analysis\n"
            "- Simply describe what you see on screen in natural language\n"
            "- Focus on helping the user with their question\n"
            "- If you see any dangerous content, warn about it\n\n"
            
            "📋 RESPONSE RULES:\n"
            "- Answer briefly and clearly\n"
            "- Be friendly and helpful\n"
            "- Don't over-explain\n"
            "- Focus on what the user needs\n"
            
            
            
            
            "REMEMBER: Keep it simple, helpful, Use memory just in case if you need to use, it's really helpful but otherwise don't use it, also Screenshot if user don't ask you to describe or talk about you don't need to talk about this if user ask you about a screenshot then in this case, you need to talk about screenshot and describe it!"
        )
        
        logger.info(f"✅ base_system_instruction created: {len(self.base_system_instruction)} characters")
        
        try:
            # ✅ УПРОЩЕННАЯ ИНИЦИАЛИЗАЦИЯ (как в langchain_test)
            if LANGCHAIN_AVAILABLE:
                logger.info("✅ Using LangChain + Google Gemini (simplified version)")
                
                # ✅ Устанавливаем флаг использования LangChain
                self.use_langchain = True
                
                # ✅ ПРОСТАЯ ИНИЦИАЛИЗАЦИЯ LangChain БЕЗ инструментов в конструкторе
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash-lite",
                    google_api_key=os.environ.get("GEMINI_API_KEY"),
                    temperature=0.7,
                    max_output_tokens=2048,
                    streaming=True,  # 🔧 ВКЛЮЧАЕМ СТРИМИНГ!
                    cache=False,
                    # 🔧 ОТКЛЮЧАЕМ КЭШИРОВАНИЕ для получения свежих результатов
                    force_refresh=True
                )
                
                # ✅ МАКСИМАЛЬНО ПРОСТАЯ СИСТЕМА (только то, что работает)
                logger.info("✅ System simplified - no tools, only basic conversation")
                
                logger.info(f"✅ TextProcessor with LangChain initialized successfully")
                
            else:
                # ❌ LangChain недоступен - критическая ошибка
                logger.error("❌ CRITICAL ERROR: LangChain unavailable!")
                raise ImportError("LangChain unavailable. Install required dependencies.")
            
            # Инициализируем MemoryAnalyzer (если доступен)
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if gemini_api_key:
                try:
                    from memory_analyzer import MemoryAnalyzer
                    self.memory_analyzer = MemoryAnalyzer(gemini_api_key)
                    logger.info(f"✅ MemoryAnalyzer initialized")
                except ImportError as e:
                    logger.warning(f"⚠️ MemoryAnalyzer cannot be imported: {e}")
                    self.memory_analyzer = None
                except Exception as e:
                    logger.warning(f"⚠️ MemoryAnalyzer not initialized: {e}")
                    self.memory_analyzer = None
            
        except Exception as e:
            logger.error(f"❌ Error initializing TextProcessor: {e}", exc_info=True)
            self.llm = None
    

    
    def cancel_generation(self):
        """
        МГНОВЕННО отменяет текущую генерацию LLM и очищает все процессы.
        Используется для принудительного прерывания.
        """
        try:
            logger.warning("🚨 IMMEDIATELY canceling LLM generation!")
            
            # КРИТИЧНО: отменяем текущую генерацию Gemini
            if hasattr(self, '_current_generation'):
                try:
                    if hasattr(self._current_generation, 'cancel'):
                        self._current_generation.cancel()
                        logger.warning("🚨 Gemini generation IMMEDIATELY CANCELLED!")
                except:
                    pass
                self._current_generation = None
            
            # КРИТИЧНО: очищаем все внутренние буферы
            if hasattr(self, '_text_buffer'):
                self._text_buffer.clear()
                logger.warning("🚨 Text buffers IMMEDIATELY CLEARED!")
            
            # КРИТИЧНО: очищаем все временные переменные
            if hasattr(self, '_current_prompt'):
                self._current_prompt = None
                logger.warning("�� Current prompt IMMEDIATELY CLEARED!")
            
            logger.warning("✅ All LLM processes IMMEDIATELY cancelled!")
            
        except Exception as e:
            logger.error(f"❌ Error canceling LLM generation: {e}")
    
    def clear_buffers(self):
        """
        МГНОВЕННО очищает все буферы и отменяет генерацию.
        """
        self.cancel_generation()

    def set_database_manager(self, db_manager):
        """
        Устанавливает DatabaseManager для работы с памятью.
        
        Args:
            db_manager: Экземпляр DatabaseManager
        """
        self.db_manager = db_manager
        logger.info("✅ DatabaseManager set in TextProcessor")
    
    async def generate_response_stream(self, prompt: str, hardware_id: str = None, screenshot_base64: str = None, interrupt_checker=None, **kwargs) -> AsyncGenerator[str, None]:
        """
        🎯 УПРОЩЕННЫЙ МЕТОД: Генерация ответа через LangChain (как в langchain_test)
        """
        try:
            logger.info(f"🚀 Starting request processing: '{prompt[:100]}...'")
            
            # КРИТИЧНО: сохраняем функцию проверки прерывания
            self._interrupt_checker = interrupt_checker
            self._current_prompt = prompt
            
            # Получаем контекст памяти (если доступен)
            memory_context = ""
            if hardware_id and self.db_manager:
                try:
                    # Таймаут 2 секунды на получение памяти
                    async with asyncio.timeout(2.0):
                        memory_data = await asyncio.to_thread(
                            self.db_manager.get_user_memory, 
                            hardware_id
                        )
                        if memory_data.get('short') or memory_data.get('long'):
                            memory_context = f"""
🧠 MEMORY CONTEXT (for response context):

📋 SHORT-TERM MEMORY (current session):
{memory_data.get('short', 'No short-term memory')}

📚 LONG-TERM MEMORY (user information):
{memory_data.get('long', 'No long-term memory')}

💡 MEMORY USAGE INSTRUCTIONS:
- Use short-term memory to understand current conversation context
- Use long-term memory for response personalization (name, preferences, important details)
- If memory is not relevant to current request - ignore it
- Memory should complement the answer, not replace it
- Priority: current request > short-term memory > long-term memory
                            """
                            logger.info(f"🧠 Memory obtained for {hardware_id}: short-term ({len(memory_data.get('short', ''))} chars), long-term ({len(memory_data.get('long', ''))} chars)")
                        else:
                            logger.info(f"🧠 Memory for {hardware_id} is empty")
                except asyncio.TimeoutError:
                    logger.warning(f"⏰ Timeout getting memory for {hardware_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Error getting memory: {e}")
            
            # 🚨 УПРОЩЕННЫЙ ПОДХОД: используем только прямой вызов LLM
            logger.info("🚀 Using direct LLM call (no chain)")
                
            # 🔧 Формируем контент для запроса
            user_content = prompt
            if memory_context:
                user_content = f"{memory_context}\n\n{prompt}"
            
            # 🚨 УБРАНО: дублирующая логика языка - теперь используется только base_system_instruction
                
            # 🔧 ПРЯМОЙ ВЫЗОВ LLM без цепочки
            try:
                # 🔧 Убираем служебный текст - сразу обрабатываем запрос
                async with asyncio.timeout(15.0):  # 15 секунд на простую обработку
                    
                    # 🔧 ПОДДЕРЖКА ИЗОБРАЖЕНИЙ: создаем мультимодальные сообщения
                    if screenshot_base64:
                        logger.info("🖼️ Screenshot detected - creating multimodal request")
                        
                        # Создаем мультимодальное сообщение с изображением
                        # 🔧 System Prompt передается в конфигурации, а не как сообщение
                        messages = [
                            SystemMessage(content=self.base_system_instruction),
                            HumanMessage(content=[
                                {
                                    "type": "text",
                                    "text": user_content
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/webp;base64,{screenshot_base64}"
                                    }
                                }
                            ])
                        ]
                        logger.info("✅ Multimodal message created with WebP image")
                    else:
                        # Только текст
                        # ✅ System Prompt передается как SystemMessage в списке сообщений
                        messages = [
                            SystemMessage(content=self.base_system_instruction),
                            HumanMessage(content=user_content)
                        ]
                        logger.info("✅ Text-only message created")
                    
                    # 🔧 Прямой вызов LLM со стримингом
                    buffer = ""  # Буфер для накопления текста
                    full_response = ""  # 🔧 Полный ответ для анализа памяти
                    
                    async for chunk in self.llm.astream(messages, config={
                        "cache": False,
                        "force_refresh": True
                    }):
                        # 🔧 Извлекаем контент из чанка
                        if hasattr(chunk, 'content'):
                            content = chunk.content
                        elif hasattr(chunk, 'text'):
                            content = chunk.text
                        else:
                            content = str(chunk)
                        
                        # 🔧 Накопление в буфере и полном ответе
                        if content:
                            buffer += content
                            full_response += content  # 🔧 Собираем полный ответ для памяти
                            
                            # 🔧 Проверяем, есть ли полные предложения
                            sentences = self._split_into_sentences(buffer)
                            
                            # Если есть полные предложения, отправляем их
                            if len(sentences) > 1:
                                # Отправляем все предложения кроме последнего (оно может быть неполным)
                                for sentence in sentences[:-1]:
                                    if sentence.strip():
                                        yield sentence.strip()
                                
                                # Оставляем последнее предложение в буфере
                                buffer = sentences[-1]
                    
                    # 🔧 Отправляем оставшийся текст в буфере
                    if buffer.strip():
                        yield buffer.strip()
                        full_response += buffer.strip()  # 🔧 Добавляем последний фрагмент
                    
                    logger.info("✅ Direct LLM streaming completed successfully")
                    
                    # 🔧 ФОНОВОЕ обновление памяти с РЕАЛЬНЫМ ответом
                    if hardware_id and self.db_manager and self.memory_analyzer:
                        # Создаем задачу в фоне с РЕАЛЬНЫМ ответом
                        asyncio.create_task(
                            self._update_memory_background(hardware_id, prompt, full_response)
                        )
                        logger.info(f"🔄 Memory update task started in background for {hardware_id} with real response ({len(full_response)} chars)")
                    elif hardware_id and self.db_manager:
                        logger.warning(f"⚠️ MemoryAnalyzer unavailable for {hardware_id}, memory will not be updated")
                    elif hardware_id:
                        logger.warning(f"⚠️ DatabaseManager unavailable for {hardware_id}, memory will not be updated")
                    
            except asyncio.TimeoutError:
                logger.warning("⏰ Timeout - using fallback")
                # Fallback: синхронный вызов со стримингом
                
                # 🔧 ПОДДЕРЖКА ИЗОБРАЖЕНИЙ В FALLBACK
                if screenshot_base64:
                    logger.info("🖼️ Screenshot detected in fallback - creating multimodal request")
                    # ✅ System Prompt передается как SystemMessage в списке сообщений
                    messages = [
                        SystemMessage(content=self.base_system_instruction),
                        HumanMessage(content=[
                            {
                                "type": "text",
                                "text": user_content
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/webp;base64,{screenshot_base64}"
                                }
                            }
                        ])
                    ]
                else:
                    # ✅ System Prompt передается как SystemMessage в списке сообщений
                    messages = [
                        SystemMessage(content=self.base_system_instruction),
                        HumanMessage(content=user_content)
                    ]
                
                # 🔧 Fallback стриминг с разбивкой на предложения
                buffer = ""  # Буфер для накопления текста
                
                for chunk in self.llm.stream(messages, config={
                    "cache": False,
                    "force_refresh": True
                }):
                    # 🔧 Извлекаем контент из чанка
                    if hasattr(chunk, 'content'):
                        content = chunk.content
                    elif hasattr(chunk, 'text'):
                        content = chunk.text
                    else:
                        content = str(chunk)
                    
                    # 🔧 Накопление в буфере
                    if content:
                        buffer += content
                        
                        # 🔧 Проверяем, есть ли полные предложения
                        sentences = self._split_into_sentences(buffer)
                        
                        # Если есть полные предложения, отправляем их
                        if len(sentences) > 1:
                            # Отправляем все предложения кроме последнего (оно может быть неполным)
                            for sentence in sentences[:-1]:
                                if sentence.strip():
                                    yield sentence.strip()
                            
                            # Оставляем последнее предложение в буфере
                            buffer = sentences[-1]
                
                # 🔧 Отправляем оставшийся текст в буфере
                if buffer.strip():
                    yield buffer.strip()
                
                logger.info("✅ Fallback LLM streaming completed successfully")
                    
            except Exception as e:
                logger.error(f"❌ Error in direct LLM call: {e}")
                yield f"Sorry, an error occurred while processing your request: {e}"
            
            # 🔧 ПАМЯТЬ ОБНОВЛЯЕТСЯ В ОСНОВНОМ СТРИМЕ с реальным ответом

        except Exception as e:
            logger.error(f"Error in request processing: {e}", exc_info=True)
            yield "Sorry, an internal error occurred while processing your request."
    
    def clean_text(self, text: str) -> str:
        """Очищает текст от лишних символов и форматирования"""
        if not text:
            return ""
        
        # Убираем лишние пробелы и переносы строк
        text = ' '.join(text.split())
        
        # Убираем специальные символы, которые могут мешать
        text = re.sub(r'[^\w\s\.\,\!\?\-\:\;\(\)\[\]\{\}\"\']', '', text)
        
        return text.strip()

    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения для стриминга"""
        if not text:
            return []
        
        # Очищаем текст
        text = self.clean_text(text)
        
        # Используем более точное разбиение на предложения
        
        # 🎯 УЛУЧШЕННЫЙ ПАТТЕРН для разбиения на предложения
        # Учитываем:
        # - Точки (.)
        # - Восклицательные знаки (!)
        # - Вопросительные знаки (?)
        # - Многоточие (...)
        # - Комбинации (!?, ?!)
        # Исключаем точки в сокращениях (т.д., и т.п., Dr., Mr., etc.)
        
        # Паттерн для разбиения на предложения
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-ZА-Я])'
        
        # Разбиваем по паттерну
        sentences = re.split(sentence_pattern, text)
        
        # Фильтруем и обрабатываем предложения
        result = []
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                # Если это не последнее предложение, проверяем знак препинания
                if i < len(sentences) - 1:
                    # Ищем знак препинания в конце
                    if not any(sentence.endswith(ending) for ending in ['.', '!', '?', '...', '?!', '!?']):
                        sentence += '.'
                result.append(sentence)
        
        return result
    
    async def _smart_stream_content(self, content: str) -> AsyncGenerator[str, None]:
        """Умный стриминг контента с разбивкой на предложения"""
        if not content or not content.strip():
            return
        
        # Разбиваем на предложения
        sentences = self._split_into_sentences(content)
        
        for sentence in sentences:
            if sentence.strip():
                yield sentence.strip()
    
    def _is_complete_sentence(self, text: str) -> bool:
        """Проверяет, является ли предложение полным"""
        if not text:
            return False
        
        # Очищаем текст
        text = self.clean_text(text)
        
        # Проверяем, заканчивается ли текст знаком окончания предложения
        sentence_endings = ['.', '!', '?', '...', '?!', '!?']
        return any(text.endswith(ending) for ending in sentence_endings)
    
    async def _update_memory_background(self, hardware_id: str, prompt: str, response: str):
        """
        Фоновое обновление памяти пользователя.
        
        Args:
            hardware_id: Аппаратный ID пользователя
            prompt: Запрос пользователя
            response: Ответ ассистента
        """
        try:
            logger.debug(f"🔄 Starting background memory update for {hardware_id}")
            
            # Анализируем разговор для извлечения памяти
            short_memory, long_memory = await self.memory_analyzer.analyze_conversation(
                prompt, 
                response
            )
            
            # Если есть что сохранять
            if short_memory or long_memory:
                # Обновляем память в базе данных
                success = await asyncio.to_thread(
                    self.db_manager.update_user_memory,
                    hardware_id,
                    short_memory,
                    long_memory
                )
                
                if success:
                    logger.info(f"✅ Memory for {hardware_id} updated: short-term ({len(short_memory)} chars), long-term ({len(long_memory)} chars)")
                else:
                    logger.warning(f"⚠️ Could not update memory for {hardware_id}")
            else:
                logger.debug(f"🧠 No information found for {hardware_id} to remember")
                
        except Exception as e:
            logger.error(f"❌ Error in background memory update for {hardware_id}: {e}")
            # НЕ поднимаем исключение - это фоновая задача